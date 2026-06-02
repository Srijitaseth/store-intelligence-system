from sqlalchemy.orm import Session
from app.database import EventDB


def get_store_funnel(db: Session, store_id: str):
    events = (
        db.query(EventDB)
        .filter(EventDB.store_id == store_id)
        .filter(EventDB.is_staff == False)
        .all()
    )

    all_visitors = set()
    zone_visitors = set()
    billing_visitors = set()
    purchase_visitors = set()

    for event in events:
        all_visitors.add(event.visitor_id)

        if event.event_type in ["ZONE_ENTER", "ZONE_DWELL"]:
            zone_visitors.add(event.visitor_id)

        if event.event_type == "BILLING_QUEUE_JOIN":
            billing_visitors.add(event.visitor_id)

        if event.event_type == "PURCHASE":
            purchase_visitors.add(event.visitor_id)

    entry_count = len(all_visitors)
    zone_count = len(zone_visitors)
    billing_count = len(billing_visitors)
    purchase_count = len(purchase_visitors)

    def safe_stage_count(current_count, previous_count):
        return min(current_count, previous_count)

    zone_count = safe_stage_count(zone_count, entry_count)
    billing_count = safe_stage_count(billing_count, zone_count)
    purchase_count = safe_stage_count(purchase_count, billing_count)

    def drop_percent(previous_count, current_count):
        if previous_count == 0:
            return 0.0
        return round(((previous_count - current_count) / previous_count) * 100, 2)

    return {
        "store_id": store_id,
        "funnel": [
            {
                "stage": "Entry",
                "count": entry_count,
                "drop_off_percent": 0.0
            },
            {
                "stage": "Zone Visit",
                "count": zone_count,
                "drop_off_percent": drop_percent(entry_count, zone_count)
            },
            {
                "stage": "Billing Queue",
                "count": billing_count,
                "drop_off_percent": drop_percent(zone_count, billing_count)
            },
            {
                "stage": "Purchase",
                "count": purchase_count,
                "drop_off_percent": drop_percent(billing_count, purchase_count)
            }
        ]
    }