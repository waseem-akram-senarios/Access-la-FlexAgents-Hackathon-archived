"""Horizontal — many need/phone/topic variants; verified Access LA contacts."""

from __future__ import annotations

import pytest

from app.seed.verified_contacts import (
    NEED_TO_DEPT,
    OMC_TEXT,
    REQUIRED_PHONES,
    REQUIRED_TDD,
)


def test_horizontal_seed_phones_match_access_la(client):
    """Every department phone/tdd matches Rider's Guide / accessla.org constants."""
    rows = {d["id"]: d for d in client.get("/departments").json()}
    assert len(rows) >= 8
    for dept_id, phone in REQUIRED_PHONES.items():
        assert dept_id in rows, f"missing department {dept_id}"
        assert rows[dept_id]["phone"] == phone, (
            f"{dept_id}: expected {phone}, got {rows[dept_id]['phone']}"
        )
    for dept_id, tdd in REQUIRED_TDD.items():
        assert rows[dept_id].get("tdd") == tdd, (
            f"{dept_id}: expected tdd {tdd}, got {rows[dept_id].get('tdd')}"
        )
    # OMC description must mention Option 2 and text-to-chat number
    omc = rows["dept_omc"]
    assert omc["menu_option"] == "2"
    assert OMC_TEXT in omc["description"] or "827.4588" in omc["description"]
    # At least one closed today (billing seed override)
    assert any(d["closed_today"] for d in rows.values())
    # Billing closed_today forced for judges even on weekdays
    assert rows["dept_billing"]["closed_today"] is True
    assert rows["dept_billing"]["open_now"] is False


@pytest.mark.parametrize("need,dept_id", sorted(NEED_TO_DEPT.items()))
def test_horizontal_need_routes_to_verified_dept(client, need, dept_id):
    r = client.get("/departments", params={"need": need})
    assert r.status_code == 200
    ids = {d["id"] for d in r.json()}
    assert dept_id in ids, f"need={need!r} should include {dept_id}, got {ids}"


@pytest.mark.parametrize(
    "phone_in,phone_digits",
    [
        ("2135550100", "2135550100"),
        ("213-555-0100", "2135550100"),
        ("(213) 555-0100", "2135550100"),
        ("1.213.555.0100", "2135550100"),  # drop US country code
        ("213 555 0100", "2135550100"),
    ],
)
def test_horizontal_case_phone_normalization(client, phone_in, phone_digits):
    r = client.post(
        "/cases",
        json={"phone": phone_in, "topic": "general", "summary": "normalize check"},
        headers={"Idempotency-Key": f"phone-{phone_in}-{phone_digits}"},
    )
    assert r.status_code == 201
    assert r.json()["phone"] == phone_digits
    listed = client.get("/cases", params={"phone": phone_digits}).json()
    assert any(c["phone"] == phone_digits for c in listed)
    # Leading-1 query must still find the 10-digit stored number
    listed11 = client.get("/cases", params={"phone": "1" + phone_digits}).json()
    assert any(c["phone"] == phone_digits for c in listed11)


@pytest.mark.parametrize(
    "topic,dept_id",
    [
        ("lost item", "dept_lost_found"),
        ("complaint", "dept_customer_service"),
        ("eligibility", "dept_eligibility"),
        ("fare", "dept_billing"),
        ("wmr login", "dept_wmr_support"),
        ("late vehicle", "dept_omc"),
        ("travel training", "dept_travel_training"),
        ("title vi", "dept_civil_rights"),
    ],
)
def test_horizontal_case_topics_with_dept(client, topic, dept_id):
    r = client.post(
        "/cases",
        json={
            "phone": "3105552000",
            "topic": topic,
            "summary": f"Horizontal case for {topic}",
            "department_id": dept_id,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["department_id"] == dept_id
    assert body["case_number"].startswith("ACC-")


@pytest.mark.parametrize(
    "dept_id",
    [
        "dept_customer_service",
        "dept_reservations",
        "dept_omc",
        "dept_eligibility",
        "dept_lost_found",
    ],
)
def test_horizontal_slots_exist_per_dept(client, dept_id):
    from datetime import date

    today = date.today().isoformat()
    r = client.get("/slots", params={"dept": dept_id, "date": today})
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_horizontal_message_to_variants(client):
    for raw, digits in [
        ("8185553001", "8185553001"),
        ("818-555-3002", "8185553002"),
        ("(818) 555-3003", "8185553003"),
    ]:
        r = client.post(
            "/messages",
            json={"to": raw, "body": "Access LA test SMS", "from": "ACCESS-LA"},
        )
        assert r.status_code == 201
        assert r.json()["to"] == digits
        listed = client.get("/messages", params={"to": digits}).json()
        assert len(listed) >= 1


def test_horizontal_lost_found_seven_day_hours(client):
    lost = client.get("/departments/dept_lost_found").json()
    by_day = {h["day"]: h for h in lost["hours"]}
    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
        assert by_day[day].get("closed") is not True
        assert by_day[day]["open"] == "08:00"
        assert by_day[day]["close"] == "17:00"


def test_horizontal_reservations_six_to_ten(client):
    res = client.get("/departments/dept_reservations").json()
    assert res["phone"] == "1.800.883.1295"
    for h in res["hours"]:
        assert h.get("closed") is not True
        assert h["open"] == "06:00" and h["close"] == "22:00"


def test_horizontal_cs_weekday_only(client):
    cs = client.get("/departments/dept_customer_service").json()
    assert cs["phone"] == "1.800.827.0829"
    assert cs["tdd"] == "1.800.827.1359"
    by_day = {h["day"]: h for h in cs["hours"]}
    assert by_day["sat"]["closed"] is True
    assert by_day["sun"]["closed"] is True
    assert by_day["mon"]["open"] == "08:00" and by_day["mon"]["close"] == "17:00"
