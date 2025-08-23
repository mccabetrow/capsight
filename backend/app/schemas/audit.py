from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class AuditLogResponse(BaseModel):
    id: str
    request_id: str
    user_id: str
    user_email: str
    route: str
    model_version: str
    response_type: str
    confidence: float
    disclaimer_version: str
    latency_ms: int
    timestamp: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True

class AuditStatsResponse(BaseModel):
    total_predictions: int
    avg_confidence: float
    unique_users: int
    avg_latency_ms: float

class AuditLogCreate(BaseModel):
    request_id: str
    route: str
    model_version: str
    response_type: str
    confidence: float
    disclaimer_version: str = "1.0"
    latency_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None
