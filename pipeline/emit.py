import json
import uuid


def create_event(
    store_id,
    camera_id,
    visitor_id,
    event_type,
    timestamp,
    zone_id=None,
    dwell_ms=0,
    is_staff=False,
    confidence=0.85,
    queue_depth=None,
    sku_zone=None,
    session_seq=1
):
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": is_staff,
        "confidence": float(confidence),
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone": sku_zone,
            "session_seq": session_seq
        }
    }


def write_event(output_path, event):
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")