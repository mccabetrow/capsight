"""
Backtesting configuration and constants
"""
from pydantic import BaseSettings, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os

class BacktestConfig(BaseSettings):
    """Configuration for backtesting subsystem"""
    
    # Data access
    feast_repo_path: str = Field(default=".", env="FEAST_REPO_PATH")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    mlflow_tracking_uri: str = Field(default="http://localhost:5000", env="MLFLOW_TRACKING_URI")
    
    # Backtest parameters
    default_horizon_months: int = Field(default=6, description="Default forecast horizon")
    max_horizon_months: int = Field(default=24, description="Maximum allowed horizon")
    min_train_window_months: int = Field(default=12, description="Minimum training window")
    
    # Feature TTL and latency constraints (in seconds)
    feature_ttl_constraints: Dict[str, int] = Field(default={
        "mortgage_rates": 3600,        # 1 hour
        "market_prices": 86400,        # 1 day  
        "economic_indicators": 604800,  # 1 week
        "demographics": 2592000,       # 1 month
    })
    
    # Sampling and performance
    max_sample_size: int = Field(default=10000, description="Max properties per backtest")
    batch_size: int = Field(default=100, description="Batch size for predictions")
    max_concurrent_requests: int = Field(default=5, description="Max concurrent API calls")
    
    # SLA thresholds
    accuracy_sla_threshold: float = Field(default=0.942, description="94.2% accuracy SLA")
    caprate_mae_sla_bps: float = Field(default=25.0, description="25 bps cap rate MAE SLA")
    noi_mape_sla_pct: float = Field(default=8.0, description="8% NOI MAPE SLA")
    response_time_sla_ms: int = Field(default=100, description="100ms response time SLA")
    
    # Report generation
    report_output_dir: str = Field(default="./backtest_reports", env="BACKTEST_REPORT_DIR")
    enable_pdf_generation: bool = Field(default=True, description="Enable PDF report generation")
    
    # Asset types and markets
    supported_asset_types: List[str] = Field(default=[
        "single_family", "condo", "townhouse", "multifamily", "commercial"
    ])
    
    supported_markets: List[str] = Field(default=[
        "TX-DAL", "TX-HOU", "TX-AUS", "CA-LAX", "CA-SF", "CA-SD", 
        "NY-NYC", "FL-MIA", "FL-ORL", "WA-SEA", "CO-DEN", "AZ-PHX"
    ])
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global config instance
config = BacktestConfig()

# Metric definitions
CORE_METRICS = {
    "caprate_mae_bps": {
        "name": "Cap Rate MAE (bps)",
        "description": "Mean Absolute Error for cap rate predictions in basis points",
        "sla_threshold": config.caprate_mae_sla_bps,
        "higher_is_better": False
    },
    "noi_mape_pct": {
        "name": "NOI MAPE (%)", 
        "description": "Mean Absolute Percentage Error for NOI predictions",
        "sla_threshold": config.noi_mape_sla_pct,
        "higher_is_better": False
    },
    "accuracy_within_5pct": {
        "name": "Accuracy within 5%",
        "description": "Percentage of predictions within 5% of actual",
        "sla_threshold": config.accuracy_sla_threshold,
        "higher_is_better": True
    },
    "rank_ic": {
        "name": "Rank Information Coefficient",
        "description": "Spearman correlation between predicted and actual rankings",
        "sla_threshold": 0.3,
        "higher_is_better": True
    },
    "top_decile_precision": {
        "name": "Top Decile Precision",
        "description": "Precision of top 10% predicted properties",
        "sla_threshold": 0.85,
        "higher_is_better": True
    },
    "calibration_error": {
        "name": "Calibration Error",
        "description": "Average deviation from perfect confidence calibration",
        "sla_threshold": 0.05,
        "higher_is_better": False
    }
}

# Market metadata
MARKET_METADATA = {
    "TX-DAL": {"name": "Dallas-Fort Worth", "state": "TX", "timezone": "America/Chicago"},
    "TX-HOU": {"name": "Houston", "state": "TX", "timezone": "America/Chicago"},
    "TX-AUS": {"name": "Austin", "state": "TX", "timezone": "America/Chicago"},
    "CA-LAX": {"name": "Los Angeles", "state": "CA", "timezone": "America/Los_Angeles"},
    "CA-SF": {"name": "San Francisco", "state": "CA", "timezone": "America/Los_Angeles"},
    "CA-SD": {"name": "San Diego", "state": "CA", "timezone": "America/Los_Angeles"},
    "NY-NYC": {"name": "New York City", "state": "NY", "timezone": "America/New_York"},
    "FL-MIA": {"name": "Miami", "state": "FL", "timezone": "America/New_York"},
    "FL-ORL": {"name": "Orlando", "state": "FL", "timezone": "America/New_York"},
    "WA-SEA": {"name": "Seattle", "state": "WA", "timezone": "America/Los_Angeles"},
    "CO-DEN": {"name": "Denver", "state": "CO", "timezone": "America/Denver"},
    "AZ-PHX": {"name": "Phoenix", "state": "AZ", "timezone": "America/Phoenix"}
}
