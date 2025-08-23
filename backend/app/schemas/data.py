"""
Data ingestion related schemas.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class DataSourceType(str, Enum):
    """Data source types."""
    ZILLOW = "zillow"
    REDFIN = "redfin"
    FRED = "fred"
    CUSTOM = "custom"


class IngestionStatus(BaseModel):
    """Data ingestion status."""
    task_id: str
    status: str  # started, running, completed, failed
    message: str
    progress: Optional[float] = None
    disclaimer: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class IngestionRequest(BaseModel):
    """Data ingestion request."""
    source: DataSourceType
    parameters: Dict[str, Any]
    priority: Optional[str] = "normal"  # low, normal, high



# --- Provenance & Trust Layer Schemas ---
class Provenance(BaseModel):
    source: str  # e.g., 'Zillow', 'CoStar', 'Internal Model'
    as_of: datetime  # ISO date the data is valid as of
    ingested_at: datetime  # When data was ingested into system

class TrustMeta(BaseModel):
    confidence_score: float  # 0-1
    confidence_reason: str
    staleness_days: Optional[int] = None
    is_stale: Optional[bool] = None
    model_version: str
    model_health: Optional[str] = None  # Green/Yellow/Red
    interval_low: Optional[float] = None
    interval_high: Optional[float] = None
    point: Optional[float] = None
    warning: Optional[str] = None
    insufficient_evidence: Optional[bool] = None
    drivers: Optional[list] = None  # Top 3-5 drivers
    assumptions: Optional[list] = None  # Key assumptions
    sources: Optional[list] = None  # List of sources with timestamps
    audit_hash: Optional[str] = None  # For audit export

class Driver(BaseModel):
    name: str
    value: float
    direction: str  # 'up' or 'down'
    description: Optional[str] = None

class Assumption(BaseModel):
    name: str
    value: float
    description: Optional[str] = None

class SourceWithTimestamp(BaseModel):
    source: str
    as_of: datetime
    ingested_at: datetime


class MarketData(BaseModel):
    """Market data structure."""
    location: str
    property_type: Optional[str] = None
    median_price: Optional[float] = None
    price_per_sqft: Optional[float] = None
    cap_rate: Optional[float] = None
    rental_yield: Optional[float] = None
    vacancy_rate: Optional[float] = None
    appreciation_rate: Optional[float] = None
    inventory_levels: Optional[int] = None
    days_on_market: Optional[float] = None
    mortgage_rates: Optional[Dict[str, float]] = None
    last_updated: datetime
    data_quality_score: Optional[float] = None
    disclaimer: str

    class Config:
        from_attributes = True
