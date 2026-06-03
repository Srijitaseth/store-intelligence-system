import argparse
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def to_iso(value):
    return value.isoformat().replace("+00:00", "Z")


def load_events(path):
    events = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    return events


def write_events(path, events):
    with open(path, "w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event) + "\n")


def get_metadata(event):
    metadata = event.get("metadata")

    if isinstance(metadata, dict):
        return metadata

    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except Exception:
            return {}

    return {}


def make_event(base_event, event_type, timestamp, zone_id=None, dwell_ms=0, confidence=0.8, extra_metadata=None):
    metadata = get_metadata(base_event)

    if extra_metadata:
        metadata.update(extra_metadata)

    return {
        "event_id": str(uuid.uuid4()),
        "store_id": base_event["store_id"],
        "camera_id": base_event["camera_id"],
        "visitor_id": base_event["visitor_id"],
        "event_type": event_type,
        "timestamp": to_iso(timestamp),
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": base_event.get("is_staff", False),
        "confidence": confidence,
        "metadata": metadata
    }


def mark_low_confidence(events, threshold):
    for event in events:
        metadata = get_metadata(event)
        confidence = float(event.get("confidence", 0.0))

        if confidence < threshold:
            metadata["confidence_quality"] = "LOW"
            metadata["review_recommended"] = True
        else:
            metadata["confidence_quality"] = "NORMAL"

        event["metadata"] = metadata

    return events


def detect_staff_visitors(events, min_events, min_span_seconds, min_zone_switches):
    events_by_visitor = defaultdict(list)

    for event in events:
        events_by_visitor[event["visitor_id"]].append(event)

    staff_visitors = set()

    for visitor_id, visitor_events in events_by_visitor.items():
        visitor_events.sort(key=lambda event: event["timestamp"])

        if len(visitor_events) < min_events:
            continue

        first_time = parse_time(visitor_events[0]["timestamp"])
        last_time = parse_time(visitor_events[-1]["timestamp"])
        span_seconds = (last_time - first_time).total_seconds()

        zones = []
        for event in visitor_events:
            if event.get("zone_id"):
                zones.append(event["zone_id"])

        zone_switches = 0
        previous_zone = None

        for zone in zones:
            if previous_zone is not None and zone != previous_zone:
                zone_switches += 1
            previous_zone = zone

        if span_seconds >= min_span_seconds and zone_switches >= min_zone_switches:
            staff_visitors.add(visitor_id)

    for event in events:
        if event["visitor_id"] in staff_visitors:
            event["is_staff"] = True
            metadata = get_metadata(event)
            metadata["staff_detection_method"] = "movement_heuristic"
            event["metadata"] = metadata

    return events, staff_visitors


def add_reentry_events(events, min_gap_seconds):
    events_by_visitor = defaultdict(list)

    for event in events:
        events_by_visitor[event["visitor_id"]].append(event)

    generated_events = []

    for visitor_id, visitor_events in events_by_visitor.items():
        visitor_events.sort(key=lambda event: event["timestamp"])

        last_exit_time = None
        last_exit_event = None

        for event in visitor_events:
            event_time = parse_time(event["timestamp"])

            if event["event_type"] == "EXIT":
                last_exit_time = event_time
                last_exit_event = event

            if event["event_type"] == "ENTRY" and last_exit_time is not None:
                gap_seconds = (event_time - last_exit_time).total_seconds()

                if gap_seconds >= min_gap_seconds:
                    reentry_event = make_event(
                        base_event=event,
                        event_type="REENTRY",
                        timestamp=event_time,
                        zone_id=event.get("zone_id"),
                        confidence=min(float(event.get("confidence", 0.8)), 0.85),
                        extra_metadata={
                            "previous_exit_timestamp": to_iso(last_exit_time),
                            "reentry_gap_seconds": round(gap_seconds, 2),
                            "matched_exit_event_id": last_exit_event.get("event_id") if last_exit_event else None
                        }
                    )

                    generated_events.append(reentry_event)
                    last_exit_time = None
                    last_exit_event = None

    return events + generated_events, generated_events


def add_billing_abandon_events(events, window_minutes):
    events_by_visitor = defaultdict(list)

    for event in events:
        events_by_visitor[event["visitor_id"]].append(event)

    generated_events = []

    for visitor_id, visitor_events in events_by_visitor.items():
        visitor_events.sort(key=lambda event: event["timestamp"])

        purchase_times = [
            parse_time(event["timestamp"])
            for event in visitor_events
            if event["event_type"] == "PURCHASE"
        ]

        billing_join_events = [
            event
            for event in visitor_events
            if event["event_type"] == "BILLING_QUEUE_JOIN"
        ]

        for billing_event in billing_join_events:
            billing_time = parse_time(billing_event["timestamp"])
            window_end = billing_time + timedelta(minutes=window_minutes)

            has_purchase_after_billing = False

            for purchase_time in purchase_times:
                if billing_time <= purchase_time <= window_end:
                    has_purchase_after_billing = True
                    break

            if not has_purchase_after_billing:
                abandon_event = make_event(
                    base_event=billing_event,
                    event_type="BILLING_QUEUE_ABANDON",
                    timestamp=window_end,
                    zone_id="BILLING",
                    confidence=min(float(billing_event.get("confidence", 0.8)), 0.8),
                    extra_metadata={
                        "billing_join_timestamp": billing_event["timestamp"],
                        "purchase_window_minutes": window_minutes,
                        "abandon_reason": "no_purchase_after_billing_window"
                    }
                )

                generated_events.append(abandon_event)

    return events + generated_events, generated_events


def sort_events(events):
    return sorted(events, key=lambda event: (event["timestamp"], event["visitor_id"], event["event_type"]))


def enrich_events(
    input_path,
    output_path,
    low_conf_threshold,
    staff_min_events,
    staff_min_span_seconds,
    staff_min_zone_switches,
    reentry_gap_seconds,
    billing_abandon_window_minutes
):
    events = load_events(input_path)

    events = mark_low_confidence(events, low_conf_threshold)

    events, staff_visitors = detect_staff_visitors(
        events=events,
        min_events=staff_min_events,
        min_span_seconds=staff_min_span_seconds,
        min_zone_switches=staff_min_zone_switches
    )

    events, reentry_events = add_reentry_events(
        events=events,
        min_gap_seconds=reentry_gap_seconds
    )

    events, abandon_events = add_billing_abandon_events(
        events=events,
        window_minutes=billing_abandon_window_minutes
    )

    events = sort_events(events)

    write_events(output_path, events)

    print(f"Input events: {len(load_events(input_path))}")
    print(f"Staff visitors marked: {len(staff_visitors)}")
    print(f"REENTRY events added: {len(reentry_events)}")
    print(f"BILLING_QUEUE_ABANDON events added: {len(abandon_events)}")
    print(f"Output events: {len(events)}")
    print(f"Output path: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", default="data/final_events_with_purchases.jsonl")
    parser.add_argument("--output", default="data/final_enriched_events.jsonl")
    parser.add_argument("--low-conf-threshold", type=float, default=0.5)
    parser.add_argument("--staff-min-events", type=int, default=80)
    parser.add_argument("--staff-min-span-seconds", type=int, default=600)
    parser.add_argument("--staff-min-zone-switches", type=int, default=8)
    parser.add_argument("--reentry-gap-seconds", type=int, default=30)
    parser.add_argument("--billing-abandon-window-minutes", type=int, default=5)

    args = parser.parse_args()

    enrich_events(
        input_path=args.input,
        output_path=args.output,
        low_conf_threshold=args.low_conf_threshold,
        staff_min_events=args.staff_min_events,
        staff_min_span_seconds=args.staff_min_span_seconds,
        staff_min_zone_switches=args.staff_min_zone_switches,
        reentry_gap_seconds=args.reentry_gap_seconds,
        billing_abandon_window_minutes=args.billing_abandon_window_minutes
    )