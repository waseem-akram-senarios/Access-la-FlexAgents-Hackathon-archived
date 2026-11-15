"""Vertical — one deep Access LA inquiry slice through all 4 APIs.

Flow: find Lost & Found → log case → book callback → send SMS confirmation.
Mirrors FlexAgents: find_department → log_case → book_callback (+ outbox).
"""

from __future__ import annotations

from datetime import date

from app.seed.verified_contacts import RESERVATIONS, RESERVATIONS_TDD


def test_vertical_lost_item_full_slice(client):
    # 1) Directory — need=lost routes to Lost and Found on Reservations line
    depts = client.get("/departments", params={"need": "lost item"}).json()
    lost = next(d for d in depts if d["id"] == "dept_lost_found")
    assert lost["phone"] == RESERVATIONS
    assert lost["tdd"] == RESERVATIONS_TDD
    assert lost["menu_option"] == "2"
    # Rider's Guide: 7 days 8am–5pm (not weekday-only)
    open_days = [h for h in lost["hours"] if not h.get("closed")]
    assert len(open_days) == 7
    assert all(h["open"] == "08:00" and h["close"] == "17:00" for h in open_days)

    # 2) Cases — create with idempotency; custom ACC- case number
    case_r = client.post(
        "/cases",
        json={
            "phone": "(213) 555-0101",
            "topic": "lost item",
            "summary": "Left black cane on Eastern region vehicle after 2pm drop-off.",
            "department_id": lost["id"],
            "rider_name": "Jamie Rider",
            "priority": "normal",
        },
        headers={"Idempotency-Key": "vert-lost-1"},
    )
    assert case_r.status_code == 201
    case = case_r.json()
    assert case["case_number"].startswith("ACC-")
    assert case["phone"] == "2135550101"
    assert client.get(f"/cases/{case['id']}").json()["id"] == case["id"]
    assert client.get(f"/cases/{case['case_number']}").json()["case_number"] == case["case_number"]
    by_phone = client.get("/cases", params={"phone": "2135550101"}).json()
    assert any(c["id"] == case["id"] for c in by_phone)

    # Idempotent replay returns same case
    again = client.post(
        "/cases",
        json={
            "phone": "2135550101",
            "topic": "lost item",
            "summary": "different text should not create duplicate",
            "department_id": lost["id"],
        },
        headers={"Idempotency-Key": "vert-lost-1"},
    )
    assert again.json()["id"] == case["id"]

    # 3) Callbacks — book an available Lost & Found slot; cancel frees it
    today = date.today().isoformat()
    slots = client.get("/slots", params={"dept": lost["id"], "date": today}).json()
    slot = next(s for s in slots if s["available"])
    cb_r = client.post(
        "/callbacks",
        json={
            "department_id": lost["id"],
            "slot_id": slot["id"],
            "phone": "2135550101",
            "name": "Jamie Rider",
            "reason": f"Follow up on case {case['case_number']}",
        },
        headers={"Idempotency-Key": "vert-cb-1"},
    )
    assert cb_r.status_code == 201
    cb = cb_r.json()
    assert cb["status"] == "booked"

    # Fill remaining capacity → 409
    while True:
        r = client.post(
            "/callbacks",
            json={
                "department_id": lost["id"],
                "slot_id": slot["id"],
                "phone": "2135550199",
            },
        )
        if r.status_code == 409:
            break
        assert r.status_code == 201
    assert r.json()["detail"]["error"] == "slot_taken"

    cancelled = client.delete(f"/callbacks/{cb['id']}").json()
    assert cancelled["status"] == "cancelled"

    # 4) Message outbox — fake SMS for judges
    msg_r = client.post(
        "/messages",
        json={
            "to": "213-555-0101",
            "body": (
                f"Access LA: case {case['case_number']} logged for Lost and Found. "
                f"Call Reservations {RESERVATIONS} Option 2 (8am–5pm daily)."
            ),
            "from": "ACCESS-LA",
            "case_id": case["id"],
        },
    )
    assert msg_r.status_code == 201
    msgs = client.get("/messages", params={"to": "2135550101"}).json()
    assert any(m["id"] == msg_r.json()["id"] for m in msgs)
    assert any(case["case_number"] in m["body"] for m in msgs)
