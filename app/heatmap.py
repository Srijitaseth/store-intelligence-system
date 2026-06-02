from sqlalchemy.orm import Session
from app.database import EventDB


def get_store_heatmap(db: Session, store_id: str):
    events = (
        db.query(EventDB)
        .filter(EventDB.store_id == store_id)
        .filter(EventDB.is_staff == False)
        .all()
    )

    zone_stats = {}

    session_ids = set()

    for event in events:
        session_ids.add(event.visitor_id)

        if not event.zone_id:
            continue

        if event.zone_id not in zone_stats:
            zone_stats[event.zone_id] = {
                "visits": 0,
                "total_dwell_ms": 0
            }

        if event.event_type == "ZONE_ENTER":
            zone_stats[event.zone_id]["visits"] += 1

        zone_stats[event.zone_id]["total_dwell_ms"] += event.dwell_ms

    max_visits = 0

    for zone in zone_stats:
        max_visits = max(max_visits, zone_stats[zone]["visits"])

    heatmap = []

    for zone, stats in zone_stats.items():
        if max_visits == 0:
            normalized_score = 0
        else:
            normalized_score = int((stats["visits"] / max_visits) * 100)

        if stats["visits"] == 0:
            avg_dwell = 0
        else:
            avg_dwell = stats["total_dwell_ms"] / stats["visits"]

        heatmap.append({
            "zone_id": zone,
            "visits": stats["visits"],
            "avg_dwell_ms": avg_dwell,
            "normalized_score": normalized_score
        })

    data_confidence = "LOW" if len(session_ids) < 20 else "HIGH"

    return {
        "store_id": store_id,
        "data_confidence": data_confidence,
        "heatmap": heatmap
    }