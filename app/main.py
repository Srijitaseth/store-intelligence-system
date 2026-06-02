import time
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import create_tables, get_db
from app.models import IngestRequest
from app.ingestion import save_event
from app.metrics import get_store_metrics
from app.funnel import get_store_funnel
from app.heatmap import get_store_heatmap
from app.anomalies import get_store_anomalies
from app.health import get_health

app = FastAPI(title="Store Intelligence API")


@app.on_event("startup")
def startup_event():
    create_tables()


@app.post("/events/ingest")
def ingest_events(payload: IngestRequest, db: Session = Depends(get_db)):
    start_time = time.time()

    inserted = 0
    duplicates = 0
    failed = 0
    errors = []

    for index, event in enumerate(payload.events):
        try:
            result = save_event(db, event)

            if result == "inserted":
                inserted += 1
            elif result == "duplicate":
                duplicates += 1

        except Exception as error:
            failed += 1
            errors.append({
                "index": index,
                "event_id": getattr(event, "event_id", None),
                "error": str(error)
            })

    latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "received": len(payload.events),
        "inserted": inserted,
        "duplicates": duplicates,
        "failed": failed,
        "latency_ms": latency_ms,
        "errors": errors
    }


@app.get("/stores/{store_id}/metrics")
def metrics(store_id: str, db: Session = Depends(get_db)):
    return get_store_metrics(db, store_id)


@app.get("/stores/{store_id}/funnel")
def funnel(store_id: str, db: Session = Depends(get_db)):
    return get_store_funnel(db, store_id)


@app.get("/stores/{store_id}/heatmap")
def heatmap(store_id: str, db: Session = Depends(get_db)):
    return get_store_heatmap(db, store_id)


@app.get("/stores/{store_id}/anomalies")
def anomalies(store_id: str, db: Session = Depends(get_db)):
    return get_store_anomalies(db, store_id)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    return get_health(db)