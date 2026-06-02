import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.database import EventDB


def get_store_anomalies(db: Session, store_id: str):
    events = (
        db.query(EventDB)
        .filter(EventDB.store_id == store_id)
        .filter(EventDB.is_staff == False)
        .all()
    )

    anomalies = []
    latest_queue_depth = 0
    zone_latest_visit = {}

    for event in events:
        try:
            metadata = json.loads(event.metadata_json or "{}")
            if metadata.get("queue_depth") is not None:
                latest_queue_depth = max(latest_queue_depth, metadata["queue_depth"])
        except Exception:
            pass

        if event.zone_id:
            zone_latest_visit[event.zone_id] = event.timestamp

    if latest_queue_depth >= 5:
        anomalies.append({
            "type": "BILLING_QUEUE_SPIKE",
            "severity": "WARN",
            "message": "Billing queue depth is high.",
            "suggested_action": "Open another billing counter or assign staff to billing area."
        })

    if len(events) == 0:
        anomalies.append({
            "type": "NO_EVENTS",
            "severity": "INFO",
            "message": "No customer events received for this store.",
            "suggested_action": "Check if CCTV feed and detection pipeline are running."
        })

    return {
        "store_id": store_id,
        "active_anomalies": anomalies
    }