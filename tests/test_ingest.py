
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def sample_event(event_id="test_evt_001"):
    return {
        "event_id": event_id,
        "store_id": "STORE_BLR_002",
        "camera_id": "CAM_TEST_01",
        "visitor_id": "VIS_TEST_01",
        "event_type": "ENTRY",
        "timestamp": "2026-03-03T14:00:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {
            "queue_depth": None,
            "sku_zone": None,
            "session_seq": 1
        }
    }


def test_ingest_event_success():
    payload = {
        "events": [
            sample_event("test_evt_success_001")
        ]
    }

    response = client.post("/events/ingest", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert body["received"] == 1
    assert body["failed"] == 0
    assert "inserted" in body
    assert "duplicates" in body
    assert "errors" in body


def test_ingest_duplicate_event_is_idempotent():
    payload = {
        "events": [
            sample_event("test_evt_duplicate_001")
        ]
    }

    first_response = client.post("/events/ingest", json=payload)
    second_response = client.post("/events/ingest", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    second_body = second_response.json()

    assert second_body["received"] == 1
    assert second_body["duplicates"] >= 1