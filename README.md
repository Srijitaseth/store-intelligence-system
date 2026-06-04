## Final Submission Deliverables

This repository includes all mandatory HackerEarth submission deliverables:

| Deliverable      | Location                            | Status   |
| ---------------- | ----------------------------------- | -------- |
| Event log file   | `data/submission/events.jsonl`      | Included |
| README           | `README.md`                         | Included |
| Design document  | `DESIGN.md`                         | Included |
| Choices document | `CHOICES.md`                        | Included |
| Additional docs  | `docs/DESIGN.md`, `docs/CHOICES.md` | Included |

### Event Log File

The final event log file is available at:

```text
data/submission/events.jsonl
```

It is generated in valid JSONL format and contains 606 event records. Each line represents one event object and follows the required event schema with fields such as `event_id`, `store_id`, `camera_id`, `visitor_id`, `event_type`, `timestamp`, `zone_id`, `dwell_ms`, `is_staff`, `confidence`, and `metadata`.

The file was validated using JSON parsing and schema field checks before submission.

# Store Intelligence System

This project is an AI-powered Store Intelligence System built for the Purplle Tech Challenge 2026 Round 2.

It processes raw CCTV footage, detects and tracks people using YOLOv8, converts movement into structured behavioral events, ingests those events through a FastAPI backend, and exposes real-time store analytics such as visitor count, conversion rate, dwell time, funnel, heatmap, anomalies, and health status.

## Features

* Person detection from CCTV footage using YOLOv8
* Visitor tracking using ByteTrack
* Structured event generation in JSONL format
* Camera-wise zone configuration using `camera_zones.json`
* Entry, exit, zone enter, zone exit, zone dwell, billing queue, and purchase events
* FastAPI backend for event ingestion and analytics
* SQLite storage for local reproducibility
* POS transaction correlation using generated purchase events
* Live Streamlit dashboard
* Health and anomaly monitoring endpoints

## Tech Stack

* Python
* FastAPI
* SQLite
* SQLAlchemy
* Pydantic
* Ultralytics YOLOv8
* ByteTrack
* OpenCV
* Streamlit
* Pytest

## Project Structure

```text
store-intelligence/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── ingestion.py
│   ├── metrics.py
│   ├── funnel.py
│   ├── heatmap.py
│   ├── anomalies.py
│   └── health.py
├── pipeline/
│   ├── detect.py
│   ├── emit.py
│   ├── zones.py
│   ├── send_events.py
│   └── generate_purchase_events.py
├── dashboard/
│   └── streamlit_app.py
├── data/
│   └── camera_zones.json
├── docs/
├── tests/
├── requirements.txt
├── README.md
└── .gitignore
```

## Important Dataset Note

The CCTV videos, generated JSONL event files, POS CSV, local SQLite database, and YOLO model weights are intentionally excluded from GitHub using `.gitignore`.

The evaluator should place the local input files in the expected folders before running the pipeline.

Expected local-only files:

```text
local_videos/
data/pos_transactions.csv
```
## Store Layout Usage

The provided Store 1 and Store 2 layout PNGs were used as visual references to understand the physical store structure, including the entrance, FOH customer browsing area, product display zones, billing/cash counter area, and BOH region.

The detection pipeline does not run inference directly on the layout PNGs. YOLOv8 runs on CCTV video frames. Since each CCTV camera has its own perspective, the runtime zone boundaries are defined in `data/camera_zones.json` using camera-frame coordinates.

A separate reference file, `data/store_layout_reference.json`, documents how the layout images map conceptually to the runtime zones:

- `ENTRY_ZONE`: entrance and entry-facing movement region
- `MAIN_FLOOR`: FOH customer browsing and product display area
- `BILLING`: cash counter and billing queue region


## Setup

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API locally:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Docker

The project includes Docker support through `Dockerfile` and `docker-compose.yml`.

To run the API with Docker:

```bash
docker compose up --build
```

This starts the FastAPI service on:

```text
http://127.0.0.1:8000
```

If Docker is not installed locally, install Docker Desktop first. The API can still be run locally without Docker using:

```bash
uvicorn app.main:app --reload
```


## Running the Detection Pipeline

Run detection on the entry camera:

```bash
python -m pipeline.detect --video "local_videos/CAM 3 - entry.mp4" --output data/generated_events.jsonl --store-id STORE_BLR_002 --camera-id CAM_ENTRY_01
```

Run detection on zone cameras:

```bash
python -m pipeline.detect --video "local_videos/CAM 1 - zone.mp4" --output data/zone_cam1_events.jsonl --store-id STORE_BLR_002 --camera-id CAM_ZONE_01
```

```bash
python -m pipeline.detect --video "local_videos/CAM 2 - zone.mp4" --output data/zone_cam2_events.jsonl --store-id STORE_BLR_002 --camera-id CAM_ZONE_02
```

Run detection on billing camera:

```bash
python -m pipeline.detect --video "local_videos/CAM 5 - billing.mp4" --output data/billing_cam5_events.jsonl --store-id STORE_BLR_002 --camera-id CAM_BILLING_01
```

## Combining Events


Combine all generated detection events:

```bash
cat data/generated_events.jsonl data/zone_cam1_events.jsonl data/zone_cam2_events.jsonl data/billing_cam5_events.jsonl > data/all_events.jsonl
```

Generate purchase events from POS data:

```bash
python -m pipeline.generate_purchase_events
```

Combine detection events with purchase events:

```bash
cat data/all_events.jsonl data/purchase_events.jsonl > data/final_events_with_purchases.jsonl
```

## Sending Events to API

Start FastAPI first:

```bash
uvicorn app.main:app --reload
```

Then send events:

```bash
python -m pipeline.send_events --events data/final_events_with_purchases.jsonl
```
## Edge-Case Enrichment

After combining detection events and purchase events, run the enrichment step:

```bash
python -m pipeline.enrich_events

## API Endpoints

### Ingest events

```text
POST /events/ingest
```

Accepts event batches and stores them idempotently using `event_id`.

### Metrics

```text
GET /stores/{store_id}/metrics
```

Returns unique visitors, converted visitors, conversion rate, average dwell per zone, and current queue depth.

### Funnel

```text
GET /stores/{store_id}/funnel
```

Returns customer journey stages:

```text
Entry → Zone Visit → Billing Queue → Purchase
```

### Heatmap

```text
GET /stores/{store_id}/heatmap
```

Returns zone visit frequency, average dwell time, normalized heatmap score, and data confidence.

### Anomalies

```text
GET /stores/{store_id}/anomalies
```

Returns operational anomalies such as billing queue spike.

### Health

```text
GET /health
```

Returns service status, database connectivity, and last event timestamp per store.

## Dashboard

The project includes a Streamlit dashboard for the live dashboard bonus. The dashboard reads data from the FastAPI backend, so start the API first.

Start the FastAPI API:

```bash
uvicorn app.main:app --reload
```

Run the dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

The dashboard will be available at:

```text
http://localhost:8501
```

The dashboard shows:

* Unique visitors
* Converted visitors
* Conversion rate
* Queue depth
* Average dwell per zone
* Funnel
* Heatmap
* Anomalies
* Health status


## Current Verified Output

On the processed sample videos, the system produced:

```text
Unique visitors: 134
Converted visitors: 63
Conversion rate: 47.01%
Billing Queue visitors: 63
Purchase visitors: 63
```

## Design Notes

The detection pipeline uses YOLOv8 for person detection and ByteTrack for tracking. Each tracked person receives a visitor token. Zone membership is calculated using camera-specific rectangular zones defined in `data/camera_zones.json`.

The backend uses FastAPI and SQLite for simplicity, reproducibility, and fast local evaluation. The architecture is designed so SQLite can later be replaced with PostgreSQL and the JSONL replay flow can later be replaced with Kafka or another streaming system.

## Limitations

* Staff detection is currently represented through the `is_staff` field but not fully automated.
* Re-identification across different camera views is approximated through visitor IDs generated per camera tracker.
* Zone boundaries are manually configured using camera coordinates.
* POS correlation is simulated by generating purchase events from billing queue visitors and POS rows.
* The current implementation is optimized for challenge reproducibility rather than production-scale distributed streaming.

## Future Improvements

* Add stronger cross-camera re-identification
* Improve staff classification using uniform detection
* Use polygon zones instead of rectangle zones
* Add PostgreSQL and Redis for production deployment
* Add Kafka for real-time event streaming
* Add more robust anomaly detection using historical baselines
