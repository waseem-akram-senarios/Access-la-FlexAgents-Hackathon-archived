"""In-memory store with seed data for Spectac Track B APIs."""

from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.phoneutil import phones_match

_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_SEED_PATH = Path(__file__).parent / "seed" / "departments.json"


def _now() -> datetime:
    return datetime.now(settings.tz)


def _today() -> date:
    return _now().date()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _case_number(seq: int) -> str:
    # Custom Access-style case numbers: ACC-YYYYMMDD-####
    return f"ACC-{_today().strftime('%Y%m%d')}-{seq:04d}"


class Store:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.departments: list[dict[str, Any]] = []
        self.cases: dict[str, dict[str, Any]] = {}
        self.cases_by_number: dict[str, str] = {}
        self.case_idempotency: dict[str, str] = {}
        self.case_seq = 1000
        self.slots: dict[str, dict[str, Any]] = {}
        self.callbacks: dict[str, dict[str, Any]] = {}
        self.callback_idempotency: dict[str, str] = {}
        self.messages: dict[str, dict[str, Any]] = {}
        self.reset()

    def reset(self) -> None:
        with self._lock:
            raw = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
            today_iso = _today().isoformat()
            depts: list[dict[str, Any]] = []
            for row in raw:
                dept = deepcopy(row)
                overrides = []
                for ov in dept.get("holiday_overrides", []):
                    o = dict(ov)
                    if o.get("date") == "__TODAY__":
                        o["date"] = today_iso
                    overrides.append(o)
                dept["holiday_overrides"] = overrides
                depts.append(dept)
            self.departments = depts
            self.cases.clear()
            self.cases_by_number.clear()
            self.case_idempotency.clear()
            self.case_seq = 1000
            self.slots.clear()
            self.callbacks.clear()
            self.callback_idempotency.clear()
            self.messages.clear()
            self._seed_slots()
            self._seed_demo_cases_and_messages()

    def _seed_slots(self) -> None:
        """Generate ~20+ slots per department over the next 7 days."""
        starts = [
            time(9, 0),
            time(10, 0),
            time(11, 0),
            time(13, 0),
            time(14, 0),
            time(15, 0),
        ]
        today = _today()
        for dept in self.departments:
            for day_offset in range(0, 7):
                d = today + timedelta(days=day_offset)
                for i, start in enumerate(starts):
                    end_h = start.hour + 1
                    end = time(end_h, 0)
                    # First slot of today for billing is pre-filled (capacity 1, booked 1)
                    # so judges can see fill-up / 409 behavior.
                    capacity = 1 if i == 0 else 2
                    booked = 0
                    if day_offset == 0 and i == 0 and dept["id"] == "dept_billing":
                        booked = 1
                    sid = f"slot_{dept['id']}_{d.isoformat()}_{start.strftime('%H%M')}"
                    self.slots[sid] = {
                        "id": sid,
                        "department_id": dept["id"],
                        "date": d,
                        "start": start,
                        "end": end,
                        "capacity": capacity,
                        "booked": booked,
                    }

    def _seed_demo_cases_and_messages(self) -> None:
        """Seed 20+ cases and messages so list endpoints are non-empty."""
        topics = [
            ("lost item", "Left backpack on vehicle after trip."),
            ("complaint", "Driver was late by 25 minutes."),
            ("compliment", "Driver was very helpful with mobility device."),
            ("eligibility", "Question about recertification timeline."),
            ("fare", "Need help understanding TAP fare options."),
            ("wmr", "Cannot log into Where's My Ride."),
            ("standing order", "Need to pause subscription trips."),
            ("appeal", "Received denial notice and need next steps."),
            ("access id", "Lost Access ID card."),
            ("beyond the curb", "Ask about Beyond the Curb assistance."),
        ]
        for i in range(22):
            topic, summary = topics[i % len(topics)]
            phone = f"213555{1000 + i:04d}"
            case = self.create_case(
                {
                    "phone": phone,
                    "topic": topic,
                    "summary": f"{summary} (seed #{i + 1})",
                    "department_id": self.departments[i % len(self.departments)]["id"],
                    "rider_name": f"Rider {i + 1}",
                    "priority": "normal",
                    "metadata": {"seed": True},
                },
                idempotency_key=None,
            )
            self.create_message(
                {
                    "to": phone,
                    "body": f"Access LA update for case {case['case_number']}: we received your request.",
                    "from": "ACCESS-LA",
                    "case_id": case["id"],
                    "metadata": {"seed": True},
                }
            )

    # ── Departments ──────────────────────────────────────────────

    def list_departments(self, need: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = [self._enrich_department(d) for d in self.departments]
            if need:
                q = need.strip().lower()
                rows = [
                    d
                    for d in rows
                    if q in d["name"].lower()
                    or q in d["description"].lower()
                    or any(q in n.lower() for n in d["needs"])
                ]
            return rows

    def get_department(self, dept_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            for d in self.departments:
                if d["id"] == dept_id:
                    return self._enrich_department(d)
            return None

    def _enrich_department(self, dept: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        today = now.date()
        day_key = _DAY_KEYS[today.weekday()]
        closed_today = False
        open_now = False

        override = next(
            (o for o in dept.get("holiday_overrides", []) if o.get("date") == today.isoformat()),
            None,
        )
        if override:
            if override.get("closed", True):
                closed_today = True
                open_now = False
            else:
                open_now = self._within_hours(
                    now.time(), override.get("open"), override.get("close")
                )
                closed_today = not open_now and not override.get("open")
        else:
            hours_row = next((h for h in dept["hours"] if h["day"] == day_key), None)
            if not hours_row or hours_row.get("closed"):
                closed_today = True
                open_now = False
            else:
                open_now = self._within_hours(
                    now.time(), hours_row.get("open"), hours_row.get("close")
                )
                closed_today = False

        out = deepcopy(dept)
        out["open_now"] = open_now
        out["closed_today"] = closed_today
        out["timezone"] = settings.timezone
        return out

    @staticmethod
    def _within_hours(now_t: time, open_s: Optional[str], close_s: Optional[str]) -> bool:
        if not open_s or not close_s:
            return False
        oh, om = map(int, open_s.split(":"))
        ch, cm = map(int, close_s.split(":"))
        start = time(oh, om)
        end = time(ch, cm)
        if end == time(23, 59):
            return now_t >= start
        return start <= now_t <= end

    # ── Cases ────────────────────────────────────────────────────

    def create_case(
        self, payload: dict[str, Any], idempotency_key: Optional[str]
    ) -> dict[str, Any]:
        with self._lock:
            if idempotency_key and idempotency_key in self.case_idempotency:
                existing_id = self.case_idempotency[idempotency_key]
                return deepcopy(self.cases[existing_id])

            self.case_seq += 1
            now = _now()
            cid = _new_id("case")
            case_number = _case_number(self.case_seq)
            topic = payload["topic"]
            category = payload.get("category")
            if not category:
                t = topic.strip().lower().replace(" ", "_").replace("-", "_")
                if t in {"complaint", "commendation", "lost_item", "compliment"}:
                    category = "commendation" if t == "compliment" else t
                elif "lost" in t:
                    category = "lost_item"
                elif "complain" in t:
                    category = "complaint"
                elif "commend" in t or "compliment" in t:
                    category = "commendation"
                else:
                    category = "other"
            row = {
                "id": cid,
                "case_number": case_number,
                "phone": payload["phone"],
                "topic": topic,
                "summary": payload["summary"],
                "category": category,
                "incident_at": payload.get("incident_at"),
                "route": payload.get("route"),
                "vehicle": payload.get("vehicle"),
                "department_id": payload.get("department_id"),
                "rider_name": payload.get("rider_name"),
                "priority": payload.get("priority", "normal"),
                "status": "open",
                "metadata": payload.get("metadata") or {},
                "created_at": now,
                "updated_at": now,
            }
            self.cases[cid] = row
            self.cases_by_number[case_number] = cid
            if idempotency_key:
                self.case_idempotency[idempotency_key] = cid
            return deepcopy(row)

    def get_case(self, case_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self.cases.get(case_id)
            if row:
                return deepcopy(row)
            # Also allow lookup by case_number
            mapped = self.cases_by_number.get(case_id)
            if mapped:
                return deepcopy(self.cases[mapped])
            return None

    def list_cases(self, phone: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self.cases.values())
            if phone:
                rows = [c for c in rows if phones_match(c["phone"], phone)]
            rows.sort(key=lambda c: c["created_at"], reverse=True)
            return [deepcopy(r) for r in rows]

    # ── Slots / Callbacks ────────────────────────────────────────

    def list_slots(self, department_id: str, on_date: date) -> list[dict[str, Any]]:
        with self._lock:
            out = []
            for s in self.slots.values():
                if s["department_id"] == department_id and s["date"] == on_date:
                    row = deepcopy(s)
                    row["available"] = row["booked"] < row["capacity"]
                    out.append(row)
            out.sort(key=lambda s: s["start"])
            return out

    def get_slot(self, slot_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            s = self.slots.get(slot_id)
            if not s:
                return None
            row = deepcopy(s)
            row["available"] = row["booked"] < row["capacity"]
            return row

    def create_callback(
        self, payload: dict[str, Any], idempotency_key: Optional[str]
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """Returns (callback, error_code). error_code in {not_found, conflict}."""
        with self._lock:
            key = idempotency_key or payload.get("idempotency_key")
            if key and key in self.callback_idempotency:
                existing = self.callbacks.get(self.callback_idempotency[key])
                # Cancelled bookings must not block a new book with the same key.
                if existing and existing.get("status") != "cancelled":
                    return deepcopy(existing), None
                self.callback_idempotency.pop(key, None)

            slot = self.slots.get(payload["slot_id"])
            if not slot:
                return None, "not_found"
            if slot["department_id"] != payload["department_id"]:
                return None, "not_found"
            if slot["booked"] >= slot["capacity"]:
                return None, "conflict"

            slot["booked"] += 1
            cb_id = _new_id("cb")
            row = {
                "id": cb_id,
                "department_id": payload["department_id"],
                "slot_id": payload["slot_id"],
                "phone": payload["phone"],
                "name": payload.get("name"),
                "reason": payload.get("reason"),
                "status": "booked",
                "created_at": _now(),
            }
            self.callbacks[cb_id] = row
            if key:
                self.callback_idempotency[key] = cb_id
            return deepcopy(row), None

    def delete_callback(self, callback_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self.callbacks.get(callback_id)
            if not row:
                return None
            if row["status"] == "cancelled":
                return deepcopy(row)
            row["status"] = "cancelled"
            # Free idempotency key so the same key can book again after cancel.
            stale_keys = [k for k, v in self.callback_idempotency.items() if v == callback_id]
            for k in stale_keys:
                del self.callback_idempotency[k]
            slot = self.slots.get(row["slot_id"])
            if slot and slot["booked"] > 0:
                slot["booked"] -= 1
            return deepcopy(row)

    def get_callback(self, callback_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self.callbacks.get(callback_id)
            return deepcopy(row) if row else None

    # ── Messages ─────────────────────────────────────────────────

    def create_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            mid = _new_id("msg")
            row = {
                "id": mid,
                "to": payload["to"],
                "from": payload.get("from") or payload.get("from_") or "ACCESS-LA",
                "body": payload["body"],
                "case_id": payload.get("case_id"),
                "status": "queued",
                "created_at": _now(),
                "metadata": payload.get("metadata") or {},
            }
            self.messages[mid] = row
            return deepcopy(row)

    def list_messages(self, to: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self.messages.values())
            if to:
                rows = [m for m in rows if phones_match(m["to"], to)]
            rows.sort(key=lambda m: m["created_at"], reverse=True)
            return [deepcopy(r) for r in rows]


store = Store()
