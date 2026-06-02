

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_funnel_response_shape():
    response = client.get("/stores/STORE_BLR_002/funnel")

    assert response.status_code == 200

    body = response.json()

    assert "store_id" in body
    assert "funnel" in body
    assert isinstance(body["funnel"], list)

    stages = [stage["stage"] for stage in body["funnel"]]

    assert stages == ["Entry", "Zone Visit", "Billing Queue", "Purchase"]


def test_funnel_dropoff_is_not_negative():
    response = client.get("/stores/STORE_BLR_002/funnel")

    assert response.status_code == 200

    body = response.json()

    for stage in body["funnel"]:
        assert stage["drop_off_percent"] >= 0