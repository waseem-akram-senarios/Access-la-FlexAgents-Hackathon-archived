def test_create_and_get_case(client):
    r = client.post(
        "/cases",
        json={
            "phone": "213-555-0100",
            "topic": "lost item",
            "summary": "Left phone on van",
            "department_id": "dept_lost_found",
        },
        headers={"Idempotency-Key": "case-demo-1"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["case_number"].startswith("ACC-")
    assert body["phone"] == "2135550100"

    g = client.get(f"/cases/{body['id']}")
    assert g.status_code == 200
    assert g.json()["case_number"] == body["case_number"]

    by_num = client.get(f"/cases/{body['case_number']}")
    assert by_num.status_code == 200


def test_idempotency_key(client):
    payload = {
        "phone": "3105559999",
        "topic": "complaint",
        "summary": "Late pickup",
    }
    a = client.post("/cases", json=payload, headers={"Idempotency-Key": "same-key"})
    b = client.post("/cases", json=payload, headers={"Idempotency-Key": "same-key"})
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["id"] == b.json()["id"]
    assert a.json()["case_number"] == b.json()["case_number"]


def test_list_by_phone(client):
    client.post(
        "/cases",
        json={"phone": "8185551212", "topic": "fare", "summary": "TAP question"},
    )
    r = client.get("/cases", params={"phone": "8185551212"})
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_log_case_brief_fields(client):
    """Team 1 log_case: category, datetime, route/vehicle, description, callback phone."""
    r = client.post(
        "/cases",
        json={
            "phone": "213-555-2222",
            "topic": "lost item",
            "category": "lost_item",
            "summary": "Left bag on the 7 bus; driver was rude (separate case).",
            "incident_at": "2026-11-14T15:30:00-08:00",
            "route": "7",
            "vehicle": "van-4412",
            "department_id": "dept_lost_found",
        },
        headers={"Idempotency-Key": "log-case-fields"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "lost_item"
    assert body["route"] == "7"
    assert body["vehicle"] == "van-4412"
    assert body["incident_at"] is not None
    assert body["phone"] == "2135552222"
    assert body["case_number"].startswith("ACC-")
