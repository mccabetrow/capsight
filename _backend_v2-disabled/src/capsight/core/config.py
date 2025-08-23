"""
CapSight Backend Requirements & Configuration
Production-ready real-time predictive analytics for CRE investors
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class AccuracyTarget(BaseModel):
    """SLA accuracy targets for model performance"""
    caprate_mae_bps: float = Field(default=75.0, description="Cap-rate forecast MAE in basis points")
    noi_mape_percent: float = Field(default=12.0, description="NOI growth MAPE in percentage")
    arbitrage_top_decile_precision: float = Field(default=0.60, description="Top-decile precision threshold")
    confidence_calibration_tolerance: float = Field(default=0.05, description="Calibration bin tolerance")

class FreshnessTarget(BaseModel):
    """SLA freshness targets for data streams"""
    intraday_rates_minutes: int = Field(default=15, description="Intraday rates/credit data max latency")
    hourly_mortgage_minutes: int = Field(default=60, description="Mortgage pricing max latency")
    daily_signals_hours: int = Field(default=24, description="Daily demand signals max latency")
    news_sentiment_minutes: int = Field(default=60, description="News/sentiment max latency")

class Settings(BaseSettings):
    """CapSight Core Configuration"""
    
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    # Kafka/Streaming
    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_schema_registry_url: str = Field(default="http://localhost:8081", env="KAFKA_SCHEMA_REGISTRY_URL")
    
    # Feature Store
    feast_repo_path: str = Field(default="./feature_repo", env="FEAST_REPO_PATH")
    feast_online_store_url: str = Field(..., env="FEAST_ONLINE_STORE_URL")
    
    # ML Models
    mlflow_tracking_uri: str = Field(default="./mlruns", env="MLFLOW_TRACKING_URI")
    model_registry_s3_bucket: str = Field(..., env="MODEL_REGISTRY_S3_BUCKET")
    
    # External APIs
    fred_api_key: str = Field(..., env="FRED_API_KEY")
    bloomberg_api_key: Optional[str] = Field(None, env="BLOOMBERG_API_KEY")
    refinitiv_api_key: Optional[str] = Field(None, env="REFINITIV_API_KEY")
    safegraph_api_key: Optional[str] = Field(None, env="SAFEGRAPH_API_KEY")
    google_trends_api_key: Optional[str] = Field(None, env="GOOGLE_TRENDS_API_KEY")
    
    # Monitoring
    prometheus_port: int = Field(default=8000, env="PROMETHEUS_PORT")
    grafana_dashboard_url: Optional[str] = Field(None, env="GRAFANA_DASHBOARD_URL")
    pagerduty_api_key: Optional[str] = Field(None, env="PAGERDUTY_API_KEY")
    
    # SLA Targets
    accuracy_targets: AccuracyTarget = Field(default_factory=AccuracyTarget)
    freshness_targets: FreshnessTarget = Field(default_factory=FreshnessTarget)
    
    # Security
    jwt_secret: str = Field(..., env="JWT_SECRET")
    api_rate_limit_per_minute: int = Field(default=100, env="API_RATE_LIMIT")
    
    # Feature Flags
    enable_challenger_models: bool = Field(default=True, env="ENABLE_CHALLENGER_MODELS")
    enable_real_time_inference: bool = Field(default=True, env="ENABLE_REAL_TIME_INFERENCE")
    enable_feedback_loop: bool = Field(default=True, env="ENABLE_FEEDBACK_LOOP")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Kafka Topics Configuration
KAFKA_TOPICS = {
    "treasury_rates": "capsight.treasury_rates",
    "mbs_spreads": "capsight.mbs_spreads", 
    "mortgage_pricing": "capsight.mortgage_pricing",
    "reit_data": "capsight.reit_data",
    "cmbs_spreads": "capsight.cmbs_spreads",
    "mobility_data": "capsight.mobility_data",
    "search_trends": "capsight.search_trends",
    "news_sentiment": "capsight.news_sentiment",
    "model_predictions": "capsight.model_predictions",
    "feedback_events": "capsight.feedback_events"
}

# Feature Store Schema
FEATURE_GROUPS = {
    "treasury_features": {
        "entities": ["date"],
        "features": [
            "treasury_10y_rate", "treasury_2y_rate", "yield_curve_slope",
            "treasury_volatility", "fed_funds_rate"
        ],
        "ttl": 86400  # 24 hours
    },
    "credit_features": {
        "entities": ["date"],
        "features": [
            "mbs_spread", "cmbs_aaa_spread", "cmbs_bbb_spread", 
            "investment_grade_spread", "high_yield_spread"
        ],
        "ttl": 86400
    },
    "market_features": {
        "entities": ["market_id", "date"],
        "features": [
            "reit_implied_caprate", "transaction_volume", "rent_growth",
            "occupancy_rate", "construction_starts", "absorption_rate"
        ],
        "ttl": 604800  # 7 days
    },
    "property_features": {
        "entities": ["property_id", "date"], 
        "features": [
            "current_noi", "current_caprate", "occupancy", "rent_psf",
            "nearby_foot_traffic", "search_interest", "submarket_sentiment"
        ],
        "ttl": 2592000  # 30 days
    }
}

# Model Registry Configuration
MODEL_STAGES = {
    "STAGING": "staging",
    "PRODUCTION": "production", 
    "CHAMPION": "champion",
    "CHALLENGER": "challenger",
    "ARCHIVED": "archived"
}

# Monitoring Thresholds
ACCURACY_ALERTS = {
    "caprate_mae_breach": settings.accuracy_targets.caprate_mae_bps,
    "noi_mape_breach": settings.accuracy_targets.noi_mape_percent,
    "confidence_miscalibration": settings.accuracy_targets.confidence_calibration_tolerance
}

FRESHNESS_ALERTS = {
    "treasury_stale_minutes": settings.freshness_targets.intraday_rates_minutes,
    "mortgage_stale_minutes": settings.freshness_targets.hourly_mortgage_minutes, 
    "mobility_stale_hours": settings.freshness_targets.daily_signals_hours
}
