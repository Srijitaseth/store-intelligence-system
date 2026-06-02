import json
from sqlalchemy.orm import Session
from app.database import EventDB


def get_store_metrics(db: Session, store_id: str):
    events = (
        db.query(EventDB)
        .filter(EventDB.store_id == store_id)
        .filter(EventDB.is_staff == False)
        .all()
    )

    unique_visitors = set()
    converted_visitors = set()
    zone_dwell = {}
    latest_queue_depth = 0

    for event in events:
        unique_visitors.add(event.visitor_id)

        if event.event_type == "PURCHASE":
          converted_visitors.add(event.visitor_id)

        if event.zone_id and event.dwell_ms > 0:
            if event.zone_id not in zone_dwell:
                zone_dwell[event.zone_id] = []
            zone_dwell[event.zone_id].append(event.dwell_ms)

        try:
            metadata = json.loads(event.metadata_json or "{}")
            if metadata.get("queue_depth") is not None:
                latest_queue_depth = metadata["queue_depth"]
        except Exception:
            pass

    avg_dwell_per_zone = {}

    for zone, dwell_values in zone_dwell.items():
        avg_dwell_per_zone[zone] = sum(dwell_values) / len(dwell_values)

    total_visitors = len(unique_visitors)

    if total_visitors == 0:
        conversion_rate = 0.0
    else:
        conversion_rate = len(converted_visitors) / total_visitors

    return {
        "store_id": store_id,
        "unique_visitors": total_visitors,
        "converted_visitors": len(converted_visitors),
        "conversion_rate": round(conversion_rate, 4),
        "avg_dwell_per_zone_ms": avg_dwell_per_zone,
        "current_queue_depth": latest_queue_depth
    }