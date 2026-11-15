def test_post_and_list_messages(client):
    r = client.post(
        "/messages",
        json={
            "to": "213-555-4242",
            "body": "Your Access LA case was logged. Case ACC-DEMO.",
            "from": "ACCESS-LA",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["to"] == "2135554242"
    assert body["status"] == "queued"

    listed = client.get("/messages", params={"to": "2135554242"})
    assert listed.status_code == 200
    assert any(m["id"] == body["id"] for m in listed.json())


def test_messages_require_to(client):
    assert client.get("/messages").status_code == 400
