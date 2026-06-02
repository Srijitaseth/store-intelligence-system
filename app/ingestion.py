import json
from sqlalchemy.orm import Session
from app.database import EventDB
from app.models import StoreEvent


def save_event(db: Session, event: StoreEvent) -> str:
    existing_event = db.query(EventDB).filter(EventDB.event_id == event.event_id).first()

    if existing_event:
        return "duplicate"

    db_event = EventDB(
        event_id=event.event_id,
        store_id=event.store_id,
        camera_id=event.camera_id,
        visitor_id=event.visitor_id,
        event_type=event.event_type.upper(),
        timestamp=event.timestamp,
        zone_id=event.zone_id,
        dwell_ms=event.dwell_ms,
        is_staff=event.is_staff,
        confidence=event.confidence,
        metadata_json=json.dumps(event.metadata.model_dump())
    )

    db.add(db_event)
    db.commit()

    return "inserted"