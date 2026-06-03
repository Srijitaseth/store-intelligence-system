from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.database import EventDB


def get_health(db: Session):
    events = db.query(EventDB).all()

    last_event_timestamp_per_store = {}
    warnings = []

    for event in events:
        current_timestamp = last_event_timestamp_per_store.get(event.store_id)

        if current_timestamp is None or event.timestamp > current_timestamp:
            last_event_timestamp_per_store[event.store_id] = event.timestamp

    now = datetime.now(timezone.utc)

    for store_id, timestamp in last_event_timestamp_per_store.items():
        event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        if now - event_time > timedelta(minutes=10):
            warnings.append({
                "type": "STALE_FEED",
                "severity": "WARN",
                "store_id": store_id,
                "message": "No recent events received for this store in the last 10 minutes.",
                "suggested_action": "Check camera feed, detection pipeline, or event ingestion worker."
            })

    return {
        "status": "ok",
        "database": "connected",
        "last_event_timestamp_per_store": last_event_timestamp_per_store,
        "warnings": warnings
    }