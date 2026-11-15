import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store


@pytest.fixture()
def client():
    store.reset()
    with TestClient(app) as c:
        c.headers.update({"X-Spectac-Chaos": "off"})
        yield c
    store.reset()
