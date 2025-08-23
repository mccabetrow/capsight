"""
Pydantic schemas for backtesting API and data structures
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
import uuid

class BacktestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AssetType(str, Enum):
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTIFAMILY = "multifamily"
    COMMERCIAL = "commercial"

class Market(str, Enum):
    TX_DAL = "TX-DAL"
    TX_HOU = "TX-HOU" 
    TX_AUS = "TX-AUS"
    CA_LAX = "CA-LAX"
    CA_SF = "CA-SF"
    CA_SD = "CA-SD"
    NY_NYC = "NY-NYC"
    FL_MIA = "FL-MIA"
    FL_ORL = "FL-ORL"
    WA_SEA = "WA-SEA"
    CO_DEN = "CO-DEN"
    AZ_PHX = "AZ-PHX"

# Request/Response schemas
class BacktestRunRequest(BaseModel):
    """Request to start a new backtest run"""
    start_date: date = Field(..., description="Start date for backtest period")
    end_date: date = Field(..., description="End date for backtest period")
    horizon_months: int = Field(default=6, ge=1, le=24, description="Forecast horizon in months")
    sample_size: Optional[int] = Field(default=1000, ge=1, le=10000, description="Max properties to test")
    markets: Optional[List[Union[Market, str]]] = Field(default=None, description="Markets to include, None for all")
    asset_types: Optional[List[Union[AssetType, str]]] = Field(default=None, description="Asset types to include, None for all")
    scenario_label: Optional[str] = Field(default=None, description="Optional scenario label for what-if analysis")
    scenario_params: Optional[Dict[str, Any]] = Field(default=None, description="Scenario parameters for what-if replay")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Optional run description")
    
    @validator("end_date")
    def end_after_start(cls, v, values):
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v
    
    @validator("sample_size")
    def reasonable_sample_size(cls, v):
        if v > 10000:
            raise ValueError("sample_size cannot exceed 10,000")
        return v

class BacktestRunResponse(BaseModel):
    """Response for backtest run creation"""
    run_id: uuid.UUID
    status: BacktestStatus
    created_at: datetime
    estimated_completion_time: Optional[datetime]
    message: str

class BacktestRunStatus(BaseModel):
    """Status information for a backtest run"""
    run_id: uuid.UUID
    status: BacktestStatus
    progress_pct: float = Field(ge=0, le=100, description="Completion percentage")
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    total_properties: Optional[int]
    processed_properties: int = 0
    failed_properties: int = 0
    current_asof_date: Optional[date]
    notes: Optional[str]
    error_message: Optional[str]

# Result schemas
class BacktestResult(BaseModel):
    """Individual property backtest result"""
    id: uuid.UUID
    run_id: uuid.UUID
    asof_date: date
    property_id: str
    market: str
    asset_type: str
    
    # Predictions
    y_pred_noi: float
    y_pred_caprate_bps: float
    arbitrage_score: float
    confidence: float
    interval_lower: float
    interval_upper: float
    decile_rank: int = Field(ge=1, le=10)
    
    # Actuals (if available)
    y_true_noi: Optional[float]
    y_true_caprate_bps: Optional[float]
    
    # Computed metrics
    noi_mape: Optional[float]
    caprate_mae_bps: Optional[float]
    
    # Metadata
    model_name: str
    model_version: str
    training_data_cutoff: datetime
    data_sources: List[str]
    feature_fingerprint: str
    created_at: datetime

class BacktestMetrics(BaseModel):
    """Aggregate metrics for a backtest run"""
    run_id: uuid.UUID
    
    # Core accuracy metrics
    caprate_mae_bps: float
    noi_mape_pct: float
    accuracy_within_5pct: float
    
    # Ranking and calibration
    rank_ic: float
    top_decile_precision: float
    top_decile_recall: float
    calibration_error: float
    coverage_95pct: float
    
    # Performance
    avg_response_time_ms: float
    p99_response_time_ms: float
    
    # Business metrics
    total_properties: int
    successful_predictions: int
    failed_predictions: int
    uplift_vs_baseline_pct: Optional[float]
    
    # SLA compliance
    sla_targets_met: Dict[str, bool]
    overall_sla_compliance_pct: float
    
    # Breakdowns
    metrics_by_market: Dict[str, Dict[str, float]]
    metrics_by_asset_type: Dict[str, Dict[str, float]]
    
    computed_at: datetime

class PredictionSnapshot(BaseModel):
    """Snapshot of prediction for audit trail"""
    id: uuid.UUID
    asof_date: date
    property_id: str
    feature_fingerprint: str
    payload: Dict[str, Any]
    created_at: datetime

# Report schemas
class ReportRequest(BaseModel):
    """Request for report generation"""
    run_id: uuid.UUID
    report_type: str = Field(default="accuracy_proof", regex="^(summary|executive|accuracy_proof|calibration|uplift)$")
    format: str = Field(default="html", regex="^(html|pdf|markdown)$")
    include_charts: bool = True
    include_raw_data: bool = False

class ReportResponse(BaseModel):
    """Report generation response"""
    report_url: str
    report_type: str
    format: str
    generated_at: datetime
    expires_at: Optional[datetime]

# What-if scenario schemas
class ScenarioParameter(BaseModel):
    """Single scenario parameter for what-if analysis"""
    parameter_name: str = Field(..., description="Name of parameter to modify")
    base_value: Union[float, int, str] = Field(..., description="Original value")
    scenario_value: Union[float, int, str] = Field(..., description="Modified value for scenario")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    description: Optional[str] = Field(default=None, description="Human-readable description")

class WhatIfScenario(BaseModel):
    """What-if scenario definition"""
    scenario_id: uuid.UUID
    scenario_name: str = Field(..., max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parameters: List[ScenarioParameter]
    base_run_id: uuid.UUID
    created_at: datetime

# Database model schemas (for ORM)
class BacktestRunDB(BaseModel):
    """Database model for backtest_runs table"""
    id: uuid.UUID
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    status: BacktestStatus
    horizon_months: int
    sample_size: int
    markets_filter: Optional[List[str]]
    asset_types_filter: Optional[List[str]]
    scenario_label: Optional[str]
    scenario_params: Optional[Dict[str, Any]]
    notes: Optional[str]
    total_properties: Optional[int]
    processed_properties: int = 0
    failed_properties: int = 0
    created_at: datetime

    class Config:
        orm_mode = True

class BacktestResultDB(BaseModel):
    """Database model for backtest_results table"""
    id: uuid.UUID
    run_id: uuid.UUID
    asof_date: date
    property_id: str
    market: str
    asset_type: str
    y_true_noi: Optional[float]
    y_pred_noi: float
    noi_mape: Optional[float]
    y_true_caprate_bps: Optional[float]
    y_pred_caprate_bps: float
    caprate_mae_bps: Optional[float]
    arbitrage_score: float
    decile_rank: int
    confidence: float
    interval_lower: float
    interval_upper: float
    model_name: str
    model_version: str
    training_data_cutoff: datetime
    data_sources: List[str]
    feature_fingerprint: str
    created_at: datetime

    class Config:
        orm_mode = True
