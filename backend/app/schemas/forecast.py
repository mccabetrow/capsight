"""
Forecast schemas for request/response validation.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict
from app.schemas.data import Provenance, TrustMeta, Driver, Assumption, SourceWithTimestamp


# Base forecast schema with common fields and trust/accuracy metadata.
class ForecastBase(BaseModel):
    property_id: uuid.UUID = Field(..., description="Associated property ID")
    model_version: str = Field(..., max_length=50, description="ML model version used")
    forecast_type: str = Field(default="price_appreciation", max_length=50, description="Type of forecast")
    time_horizon_months: int = Field(..., ge=1, le=120, description="Forecast time horizon in months")
    predicted_value: Decimal = Field(..., description="Predicted value (point estimate)")
    interval_low: Optional[Decimal] = Field(None, description="Lower bound of 80% prediction interval")
    interval_high: Optional[Decimal] = Field(None, description="Upper bound of 80% prediction interval")
    confidence_score: Decimal = Field(..., ge=0, le=1, description="Model confidence score (0-1)")
    confidence_reason: Optional[str] = Field(None, description="Reason for confidence score")
    provenance: Provenance = Field(..., description="Provenance metadata (source, as_of, ingested_at)")
    trust: TrustMeta = Field(..., description="Trust/accuracy metadata (staleness, health, warning, etc.)")
    drivers: Optional[list[Driver]] = Field(None, description="Top 3-5 drivers for forecast")
    assumptions: Optional[list[Assumption]] = Field(None, description="Key assumptions used")
    sources: Optional[list[SourceWithTimestamp]] = Field(None, description="List of data sources with timestamps")
    methodology: Optional[str] = Field(None, description="Brief methodology description")


class ForecastCreate(ForecastBase):
    """Forecast creation schema."""
    pass


class ForecastRead(ForecastBase):
    """Forecast read schema for API responses, with full trust/accuracy layer."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(..., description="Forecast ID")
    created_at: datetime = Field(..., description="Forecast creation timestamp")
    updated_at: datetime = Field(..., description="Forecast last update timestamp")


class ForecastUpdate(BaseModel):
    """Forecast update schema."""
    model_version: Optional[str] = Field(None, max_length=50, description="ML model version used")
    forecast_type: Optional[str] = Field(None, max_length=50, description="Type of forecast")
    time_horizon_months: Optional[int] = Field(None, ge=1, le=120, description="Forecast time horizon in months")
    predicted_value: Optional[Decimal] = Field(None, description="Predicted value")
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Model confidence score (0-1)")
    prediction_interval_lower: Optional[Decimal] = Field(None, description="Lower bound of prediction interval")
    prediction_interval_upper: Optional[Decimal] = Field(None, description="Upper bound of prediction interval")
    market_factors: Optional[Dict[str, Any]] = Field(None, description="Key market factors considered")
    assumptions: Optional[Dict[str, Any]] = Field(None, description="Model assumptions")
    methodology: Optional[str] = Field(None, description="Brief methodology description")


class ForecastInDB(ForecastBase):
    """Forecast schema for database operations."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ForecastSummary(BaseModel):
    """Forecast summary schema for list views."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Forecast ID")
    property_id: uuid.UUID = Field(..., description="Associated property ID")
    model_version: str = Field(..., description="ML model version used")
    forecast_type: str = Field(..., description="Type of forecast")
    time_horizon_months: int = Field(..., description="Forecast time horizon in months")
    predicted_value: Decimal = Field(..., description="Predicted value")
    confidence_score: Decimal = Field(..., description="Model confidence score (0-1)")
    created_at: datetime = Field(..., description="Forecast creation timestamp")


class ForecastQuery(BaseModel):
    """Forecast query schema for filtering."""
    property_id: Optional[uuid.UUID] = Field(None, description="Filter by property ID")
    model_version: Optional[str] = Field(None, description="Filter by model version")
    forecast_type: Optional[str] = Field(None, description="Filter by forecast type")
    min_confidence: Optional[Decimal] = Field(None, ge=0, le=1, description="Minimum confidence score")
    min_time_horizon: Optional[int] = Field(None, ge=1, description="Minimum time horizon")
    max_time_horizon: Optional[int] = Field(None, le=120, description="Maximum time horizon")
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=10, ge=1, le=100, description="Number of records to return")


class ForecastBatch(BaseModel):
    """Batch forecast schema for multiple properties."""
    property_ids: list[uuid.UUID] = Field(..., min_items=1, max_items=100, description="List of property IDs")
    model_version: str = Field(..., max_length=50, description="ML model version to use")
    forecast_type: str = Field(default="price_appreciation", max_length=50, description="Type of forecast")
    time_horizon_months: int = Field(..., ge=1, le=120, description="Forecast time horizon in months")


class ForecastBatchResult(BaseModel):
    """Batch forecast result schema."""
    total_requested: int = Field(..., description="Total forecasts requested")
    successful: int = Field(..., description="Successfully generated forecasts")
    failed: int = Field(..., description="Failed forecast generations")
    forecasts: list[ForecastRead] = Field(..., description="Generated forecasts")
    errors: Optional[list[str]] = Field(None, description="Error messages for failed forecasts")
