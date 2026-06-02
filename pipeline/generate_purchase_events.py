import csv
import json
import uuid
import argparse
from datetime import datetime, timedelta


def parse_event_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_events(path):
    events = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    return events


def load_pos_rows(path):
    rows = []

    with open(path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append(row)

    return rows


def create_purchase_event(store_id, camera_id, visitor_id, timestamp, order_id, amount, session_seq):
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": "PURCHASE",
        "timestamp": timestamp,
        "zone_id": "BILLING",
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.95,
        "metadata": {
            "queue_depth": None,
            "sku_zone": "BILLING",
            "session_seq": session_seq,
            "order_id": order_id,
            "amount": amount
        }
    }


def generate_purchase_events(events_path, pos_path, output_path, store_id):
    events = load_events(events_path)
    pos_rows = load_pos_rows(pos_path)

    billing_events = []

    for event in events:
        if event["event_type"] == "BILLING_QUEUE_JOIN" and event["store_id"] == store_id:
            billing_events.append(event)

    billing_events.sort(key=lambda event: event["timestamp"])

    used_visitors = set()
    purchase_events = []

    max_purchases = min(len(pos_rows), len(billing_events))

    for index in range(max_purchases):
        billing_event = billing_events[index]
        visitor_id = billing_event["visitor_id"]

        if visitor_id in used_visitors:
            continue

        billing_time = parse_event_time(billing_event["timestamp"])
        purchase_time = billing_time + timedelta(minutes=2)

        pos_row = pos_rows[index]

        purchase_event = create_purchase_event(
            store_id=store_id,
            camera_id=billing_event["camera_id"],
            visitor_id=visitor_id,
            timestamp=purchase_time.isoformat().replace("+00:00", "Z"),
            order_id=pos_row["order_id"],
            amount=float(pos_row["total_amount"]),
            session_seq=999
        )

        purchase_events.append(purchase_event)
        used_visitors.add(visitor_id)

    with open(output_path, "w", encoding="utf-8") as file:
        for event in purchase_events:
            file.write(json.dumps(event) + "\n")

    print(f"Billing visitors found: {len(billing_events)}")
    print(f"POS rows found: {len(pos_rows)}")
    print(f"Purchase events written: {len(purchase_events)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--events", default="data/all_events.jsonl")
    parser.add_argument("--pos", default="data/pos_transactions.csv")
    parser.add_argument("--output", default="data/purchase_events.jsonl")
    parser.add_argument("--store-id", default="STORE_BLR_002")

    args = parser.parse_args()

    generate_purchase_events(
        events_path=args.events,
        pos_path=args.pos,
        output_path=args.output,
        store_id=args.store_id
    )