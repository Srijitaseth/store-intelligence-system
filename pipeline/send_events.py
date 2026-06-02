import json
import argparse
import requests


def load_jsonl(path):
    events = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    return events


def send_in_batches(events, api_url, batch_size=500):
    for start in range(0, len(events), batch_size):
        batch = events[start:start + batch_size]

        response = requests.post(
            f"{api_url}/events/ingest",
            json={"events": batch},
            timeout=30
        )

        print("Status:", response.status_code)
        print("Response:", response.json())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--events", default="data/generated_events.jsonl")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")

    args = parser.parse_args()

    events = load_jsonl(args.events)

    print(f"Loaded {len(events)} events from {args.events}")

    send_in_batches(events, args.api_url)