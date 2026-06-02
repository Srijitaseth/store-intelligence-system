# CHOICES.md

## Overview

This document explains the major engineering decisions made while building the Store Intelligence System.

The challenge required an end-to-end system that starts from raw CCTV footage and produces real-time store analytics through production-ready APIs. The main decisions were around the detection model, tracking approach, event schema, zone design, storage choice, event ingestion design, POS conversion logic, and API architecture.

The goal was not to build the most complex system, but to build a working, explainable, reproducible system that can run locally and demonstrate clear engineering trade-offs.

---

## Decision 1: Detection Model and Tracking Approach

### Options Considered

I considered the following options for detecting people in CCTV footage:

1. YOLOv8
2. YOLOv9
3. RT-DETR
4. MediaPipe
5. A custom-trained person detector

For tracking, I considered:

1. ByteTrack
2. DeepSORT
3. StrongSORT
4. Custom centroid tracking

### What AI Suggested

AI suggested starting with YOLOv8 and ByteTrack because they are practical, well-supported, easy to run locally, and suitable for person detection in retail CCTV footage.

AI also suggested not training a custom model because the challenge focuses more on building a complete end-to-end system than on model training.

### What I Chose

I chose YOLOv8 with ByteTrack.

### Why I Chose It

YOLOv8 gave a strong baseline for person detection without training a new model. It was easy to install using the Ultralytics package and could process the provided MP4 clips directly.

ByteTrack was selected because it integrates easily with Ultralytics tracking and gives stable tracking IDs. Those IDs were used to create visitor tokens like `VIS_1`, `VIS_2`, etc.

This choice allowed me to focus on the full system:

```text
CCTV → detection → tracking → event generation → API → dashboard
```

Instead of spending most of the time on model training.

### Trade-Off

YOLOv8 and ByteTrack work well for a prototype, but they are not perfect for cross-camera re-identification. A person seen in one camera can receive a different visitor ID in another camera.

For a production system, I would add a Re-ID model such as OSNet or a StrongSORT-style appearance embedding pipeline.

---

## Decision 2: Camera-Wise Zone Configuration

### Problem

Initially, I used one global set of zone coordinates for all cameras.

This failed because different CCTV videos had different camera perspectives. For example, a billing area in one camera appeared on the right side of the frame, but in the billing camera the billing counter appeared on the left side.

### Options Considered

1. One global zone configuration
2. Camera-wise rectangular zones
3. Polygon-based zones
4. Automatic zone calibration from layout images

### What AI Suggested

AI suggested debugging bounding box center coordinates and checking whether those coordinates were inside the configured zones.

That helped reveal that some cameras were using incorrect zone boundaries.

### What I Chose

I chose camera-wise rectangular zone configuration using:

```text
data/camera_zones.json
```

Each camera ID has its own `entry_line_y` and zone definitions.

Example camera IDs:

```text
CAM_ENTRY_01
CAM_ZONE_01
CAM_ZONE_02
CAM_BILLING_01
```

### Why I Chose It

This approach is simple, explainable, and easy to debug.

It also avoids hardcoding zones directly inside `detect.py`.

The detection pipeline now loads the correct zones based on the `camera_id` passed in the command.

### Trade-Off

Rectangular zones are not as accurate as polygon zones. Real CCTV perspectives are angled, so polygons would better represent actual store regions.

However, rectangles were sufficient for the challenge MVP and made the implementation easier to verify.

---

## Decision 3: Store Layout PNG Usage

### Problem

The challenge provided Store 1 and Store 2 layout PNGs.

These images show the physical store plan, including entry, FOH, BOH, product display zones, and cash counter/billing areas.

### Options Considered

1. Feed layout PNGs directly into the detection model
2. Use layout PNGs for automatic camera calibration
3. Use layout PNGs as visual references and encode final runtime zones manually

### What AI Suggested

AI clarified that YOLO should run on CCTV video frames, not on layout PNGs. The PNGs are useful for understanding store structure, but the runtime zone detection should use camera-frame coordinates.

### What I Chose

I used the layout PNGs as visual references.

I documented their use in:

```text
data/store_layout_reference.json
```

The actual runtime zone boundaries are stored in:

```text
data/camera_zones.json
```

### Why I Chose It

The layout images and CCTV frames do not share the same coordinate system. A point on the layout PNG does not directly map to a pixel location in a CCTV frame unless camera calibration/homography is performed.

Since the challenge needs a working end-to-end system, manual camera-wise frame zones were a practical choice.

### Trade-Off

This is not fully automatic. A production system would use camera calibration, homography mapping, or a manual calibration UI to map store-layout zones to camera-frame coordinates more accurately.

---

## Decision 4: Event Schema Design

### Options Considered

1. Separate schemas for detection, billing, dwell, and purchase events
2. One unified event schema for all event types
3. Minimal schema with only visitor ID, event type, and timestamp

### What AI Suggested

AI suggested using one consistent schema close to the challenge specification.

### What I Chose

I chose one unified event schema for all event types.

Each event contains:

```text
event_id
store_id
camera_id
visitor_id
event_type
timestamp
zone_id
dwell_ms
is_staff
confidence
metadata
```

### Why I Chose It

A unified schema made ingestion easier. The API can accept all events through one endpoint:

```text
POST /events/ingest
```

It also made downstream analytics simpler because metrics, funnel, heatmap, and anomalies all read from the same events table.

### Trade-Off

Some event types do not need all fields. For example, `ENTRY` does not need `zone_id`, and `PURCHASE` does not need `dwell_ms`.

However, keeping one schema made validation and storage simpler.

---

## Decision 5: API Framework

### Options Considered

1. FastAPI
2. Flask
3. Django REST Framework
4. Node.js Express

### What AI Suggested

AI suggested FastAPI because it is lightweight, typed, easy to document, and works well with Pydantic validation.

### What I Chose

I chose FastAPI.

### Why I Chose It

FastAPI helped quickly build:

```text
POST /events/ingest
GET /stores/{store_id}/metrics
GET /stores/{store_id}/funnel
GET /stores/{store_id}/heatmap
GET /stores/{store_id}/anomalies
GET /health
```

It also provides Swagger documentation automatically at:

```text
/docs
```

This made testing easier during development.

### Trade-Off

FastAPI is excellent for this challenge and for many production APIs, but at very high event volume I would pair it with Kafka, Redis Streams, or a background worker system instead of handling everything directly through synchronous API calls.

---

## Decision 6: Storage Choice

### Options Considered

1. SQLite
2. PostgreSQL
3. MongoDB
4. In-memory Python dictionaries

### What AI Suggested

AI suggested SQLite for local reproducibility and PostgreSQL for production.

### What I Chose

I chose SQLite.

### Why I Chose It

SQLite requires no setup, runs locally, and is easy to inspect. This is useful for a take-home challenge because the evaluator can run the system without configuring an external database.

SQLite also made it simple to verify inserted events using direct SQL queries.

### Trade-Off

SQLite is not ideal for high-concurrency writes across 40 live stores. In production, I would use PostgreSQL with indexes on:

```text
store_id
visitor_id
event_type
timestamp
event_id
```

---

## Decision 7: Event Streaming Approach

### Options Considered

1. Kafka
2. Redis Streams
3. JSONL event files replayed into the API
4. Direct database writes from the detection pipeline

### What AI Suggested

AI suggested using JSONL replay for the challenge MVP and documenting that Kafka would be a production upgrade.

### What I Chose

I chose JSONL event files plus API ingestion.

Detection writes events to files such as:

```text
data/generated_events.jsonl
data/zone_cam1_events.jsonl
data/zone_cam2_events.jsonl
data/billing_cam5_events.jsonl
```

Then these files are combined and sent to the API.

### Why I Chose It

JSONL is easy to debug, easy to replay, and easy to inspect.

This was very useful while validating detection output and API correctness.

### Trade-Off

JSONL replay is not a real production event stream. For live deployment, I would use Kafka or Redis Streams. The event schema was designed so this upgrade would not require changing the API logic significantly.

---

## Decision 8: POS Conversion Logic

### Problem

The POS CSV contains transactions but no customer identity.

The challenge says conversion must be inferred using the visitor’s presence in the billing zone near the transaction time.

### Options Considered

1. Ignore POS and set conversion to zero
2. Count billing queue join as conversion
3. Generate `PURCHASE` events from POS rows and billing visitors
4. Build a more complex time-window matching engine

### What AI Suggested

AI suggested generating `PURCHASE` events from POS rows and billing queue visitors so that conversion rate could be calculated using the same event system.

### What I Chose

I chose to generate `PURCHASE` events using:

```text
pipeline/generate_purchase_events.py
```

The script reads:

```text
data/all_events.jsonl
data/pos_transactions.csv
```

and writes:

```text
data/purchase_events.jsonl
```

Then the final file is created:

```text
data/final_events_with_purchases.jsonl
```

### Why I Chose It

This kept POS conversion inside the same event-driven architecture.

After adding purchase events, the final verified output was:

```text
Unique visitors: 134
Converted visitors: 63
Conversion rate: 47.01%
```

### Trade-Off

The current implementation approximates POS correlation. A production implementation would match POS timestamps with visitors who were in billing within the required five-minute window and avoid assigning multiple purchases incorrectly.

---

## Decision 9: Dashboard Choice

### Options Considered

1. Terminal dashboard
2. Streamlit dashboard
3. React frontend
4. Plain HTML page

### What AI Suggested

AI suggested Streamlit because it is fast to build and good enough for showing live metrics.

### What I Chose

I chose Streamlit.

### Why I Chose It

Streamlit allowed me to quickly show:

```text
Unique visitors
Converted visitors
Conversion rate
Queue depth
Average dwell per zone
Funnel
Heatmap
Anomalies
Health
```

It also helped prove that the detection pipeline and API are connected.

### Trade-Off

Streamlit is good for a demo dashboard. For a production dashboard, I would build a React frontend with charts, filters, historical time windows, and live WebSocket updates.

---

## Final Verified Output

The final system successfully produced:

```text
Unique visitors: 134
Converted visitors: 63
Conversion rate: 47.01%
Billing queue visitors: 63
Purchase visitors: 63
```

The dashboard also displayed:

```text
Metrics
Funnel
Heatmap
Anomalies
Health
```

## Summary

The main design philosophy was to build a practical, explainable, end-to-end system.

The system avoids unnecessary complexity while still covering the core challenge requirements:

* Detection
* Tracking
* Event generation
* Event ingestion
* Metrics
* Funnel
* Heatmap
* Anomalies
* POS conversion
* Dashboard
* Documentation

The current system is a strong MVP and can be extended into a more production-grade architecture with better Re-ID, polygon zones, historical anomaly baselines, and a real streaming layer.
