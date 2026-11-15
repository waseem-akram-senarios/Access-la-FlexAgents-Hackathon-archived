from datetime import date


def test_slots_and_book_and_cancel(client):
    today = date.today().isoformat()
    slots = client.get("/slots", params={"dept": "dept_customer_service", "date": today})
    assert slots.status_code == 200
    available = [s for s in slots.json() if s["available"]]
    assert available
    slot = available[0]

    booked = client.post(
        "/callbacks",
        json={
            "department_id": "dept_customer_service",
            "slot_id": slot["id"],
            "phone": "2135557777",
            "name": "Alex",
            "reason": "Appeal help",
        },
        headers={"Idempotency-Key": "cb-1"},
    )
    assert booked.status_code == 201
    cb = booked.json()
    assert cb["status"] == "booked"

    # Fill remaining capacity then expect 409
    for i in range(slot["capacity"]):
        r = client.post(
            "/callbacks",
            json={
                "department_id": "dept_customer_service",
                "slot_id": slot["id"],
                "phone": f"21355577{i:02d}",
            },
        )
        if r.status_code == 409:
            break
    else:
        # one more should conflict
        r = client.post(
            "/callbacks",
            json={
                "department_id": "dept_customer_service",
                "slot_id": slot["id"],
                "phone": "2135557799",
            },
        )
    assert r.status_code == 409

    deleted = client.delete(f"/callbacks/{cb['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "cancelled"


def test_prefilled_billing_slot_409(client):
    today = date.today().isoformat()
    slots = client.get("/slots", params={"dept": "dept_billing", "date": today})
    full = next(s for s in slots.json() if not s["available"])
    r = client.post(
        "/callbacks",
        json={
            "department_id": "dept_billing",
            "slot_id": full["id"],
            "phone": "2135550000",
        },
    )
    assert r.status_code == 409


def test_idempotency_after_cancel_allows_rebook(client):
    """Cancelled callback must not be returned for the same Idempotency-Key."""
    today = date.today().isoformat()
    slots = client.get("/slots", params={"dept": "dept_omc", "date": today}).json()
    slot = next(s for s in slots if s["available"] and s["capacity"] == 1)
    first = client.post(
        "/callbacks",
        json={
            "department_id": "dept_omc",
            "slot_id": slot["id"],
            "phone": "2135557001",
        },
        headers={"Idempotency-Key": "rebook-after-cancel"},
    )
    assert first.status_code == 201
    cb_id = first.json()["id"]
    assert client.delete(f"/callbacks/{cb_id}").json()["status"] == "cancelled"

    second = client.post(
        "/callbacks",
        json={
            "department_id": "dept_omc",
            "slot_id": slot["id"],
            "phone": "2135557001",
        },
        headers={"Idempotency-Key": "rebook-after-cancel"},
    )
    assert second.status_code == 201
    body = second.json()
    assert body["status"] == "booked"
    assert body["id"] != cb_id
