"""
Prediction and forecasting schemas.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class PredictionType(str, Enum):
    """Types of predictions."""
    ARBITRAGE = "arbitrage"
    CAP_RATE = "cap_rate"
    PROPERTY_VALUE = "property_value"
    INTEREST_RATE = "interest_rate"
    RENTAL_YIELD = "rental_yield"


class ModelType(str, Enum):
    """ML model types."""
    LINEAR_REGRESSION = "linear_regression"
    ARIMA = "arima"
    PROPHET = "prophet"
    XGBOOST = "xgboost"
    LSTM = "lstm"


class PredictionRequest(BaseModel):
    """Request for arbitrage prediction."""
    property_data: Dict[str, Any]
    market_data: Dict[str, Any]
    prediction_horizon: Optional[int] = 30  # days
    include_confidence_interval: bool = True
    model_preferences: Optional[List[ModelType]] = None


class PredictionResponse(BaseModel):
    """Prediction response with arbitrage score."""
    prediction_id: str
    arbitrage_score: float = Field(..., ge=0.0, le=1.0, description="Arbitrage opportunity score (0-1)")
    expected_return: Optional[float] = None
    risk_score: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    contributing_factors: Dict[str, float]
    model_used: ModelType
    prediction_date: datetime
    expires_at: datetime
    disclaimer: str
    
    # Detailed breakdown
    cap_rate_forecast: Optional[float] = None
    property_value_forecast: Optional[float] = None
    financing_advantage: Optional[float] = None
    market_inefficiency_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class ForecastRequest(BaseModel):
    """Request for market forecasting."""
    location: str
    property_type: Optional[str] = None
    time_horizon: int = Field(..., ge=1, le=365, description="Forecast horizon in days")
    forecast_types: List[PredictionType] = [
        PredictionType.CAP_RATE,
        PredictionType.PROPERTY_VALUE,
        PredictionType.INTEREST_RATE
    ]
    confidence_level: float = Field(0.95, ge=0.5, le=0.99)


class ForecastData(BaseModel):
    """Individual forecast data point."""
    date: datetime
    value: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None


class ForecastResponse(BaseModel):
    """Forecast response with time series data."""
    forecast_id: str
    location: str
    property_type: Optional[str] = None
    forecasts: Dict[PredictionType, List[ForecastData]]
    model_performance: Dict[str, float]
    confidence_intervals: Dict[PredictionType, Tuple[float, float]]
    created_at: datetime
    expires_at: datetime
    disclaimer: str
    
    class Config:
        from_attributes = True


class ModelStatus(BaseModel):
    """ML model status information."""
    model_name: str
    model_type: ModelType
    version: str
    last_trained: datetime
    accuracy_score: Optional[float] = None
    status: str  # active, training, inactive, error
    performance_metrics: Dict[str, float]


class PredictionHistory(BaseModel):
    """Historical prediction record."""
    prediction_id: str
    user_id: str
    prediction_type: PredictionType
    request_data: Dict[str, Any]
    result: Dict[str, Any]
    created_at: datetime
    accuracy_score: Optional[float] = None  # Filled in later when actual results are known
    
    class Config:
        from_attributes = True
