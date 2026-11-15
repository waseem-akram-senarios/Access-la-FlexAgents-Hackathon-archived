def test_list_departments_has_eight_plus(client):
    r = client.get("/departments")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 8
    assert all("open_now" in d and "phone" in d and "hours" in d for d in rows)
    assert any(d["closed_today"] for d in rows), "expected at least one closed today"


def test_need_filter_lost(client):
    r = client.get("/departments", params={"need": "lost"})
    assert r.status_code == 200
    names = {d["name"] for d in r.json()}
    assert "Lost and Found" in names or "Reservations" in names


def test_get_department(client):
    r = client.get("/departments/dept_customer_service")
    assert r.status_code == 200
    body = r.json()
    assert body["phone"] == "1.800.827.0829"
    assert body["holiday_overrides"]


def test_department_404(client):
    assert client.get("/departments/nope").status_code == 404
