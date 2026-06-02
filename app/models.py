from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: Optional[int] = None


class StoreEvent(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: str
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: EventMetadata = EventMetadata()


class IngestRequest(BaseModel):
    events: List[StoreEvent]


class IngestResponse(BaseModel):
    received: int
    inserted: int
    duplicates: int
    failed: int
    errors: List[Dict[str, Any]]