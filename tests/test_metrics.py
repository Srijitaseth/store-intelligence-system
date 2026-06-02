

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_metrics_response_shape():
    response = client.get("/stores/STORE_BLR_002/metrics")

    assert response.status_code == 200

    body = response.json()

    assert "store_id" in body
    assert "unique_visitors" in body
    assert "converted_visitors" in body
    assert "conversion_rate" in body
    assert "avg_dwell_per_zone_ms" in body
    assert "current_queue_depth" in body


def test_metrics_empty_store_does_not_crash():
    response = client.get("/stores/UNKNOWN_STORE/metrics")

    assert response.status_code == 200

    body = response.json()

    assert body["store_id"] == "UNKNOWN_STORE"
    assert body["unique_visitors"] == 0
    assert body["converted_visitors"] == 0
    assert body["conversion_rate"] == 0.0