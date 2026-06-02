from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import EventDB


def get_health(db: Session):
    latest_events = db.query(EventDB).all()

    last_event_per_store = {}

    for event in latest_events:
        store_id = event.store_id

        if store_id not in last_event_per_store:
            last_event_per_store[store_id] = event.timestamp
        else:
            if event.timestamp > last_event_per_store[store_id]:
                last_event_per_store[store_id] = event.timestamp

    return {
        "status": "ok",
        "database": "connected",
        "last_event_timestamp_per_store": last_event_per_store
    }