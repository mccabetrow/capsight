"""
Application configuration using Pydantic Settings.
"""

import os
from typing import List, Optional

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Project info
    PROJECT_NAME: str = "CapSight"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    JWT_SECRET: str = "your-jwt-secret-key-change-in-production-min-32-characters"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # Database Configuration with Read Replicas
    DATABASE_URL: str = "postgresql://capsight:password123@localhost:5432/capsight_db"
    DATABASE_READ_URL: Optional[str] = None  # Read replica URL
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = False
    
    # Connection Pooling with PgBouncer
    USE_PGBOUNCER: bool = False  # Enable in production
    PGBOUNCER_URL: Optional[str] = None
    
    # Redis Configuration with Clustering
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SENTINEL_HOSTS: Optional[List[str]] = None  # ["sentinel1:26379", "sentinel2:26379"]
    REDIS_SENTINEL_SERVICE: str = "capsight-redis"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_POOL_SIZE: int = 10
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://app.capsight.ai",
    ]
    
    # Stripe
    STRIPE_SECRET_KEY: str = "sk_test_dummy_stripe_secret_key_for_development"
    STRIPE_WEBHOOK_SECRET: str = "whsec_dummy_webhook_secret_for_development"
    
    # Legal & Compliance
    LEGAL_DISCLAIMER: str = "Outputs are informational only and not investment advice. CapSight makes no warranty of accuracy or future performance."
    
    # ML Configuration
    MODEL_CONFIDENCE_THRESHOLD: float = 0.8
    MAX_FORECAST_HORIZON: int = 36
    ML_MODEL_PATH: str = "app/ml/artifacts/models"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Background jobs
    ENABLE_BACKGROUND_JOBS: bool = True
    JOB_SCHEDULER_TIMEZONE: str = "UTC"
    
    # Alerting & Monitoring
    PAGERDUTY_INTEGRATION_KEY: Optional[str] = None
    OPSGENIE_API_KEY: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # Business metrics thresholds
    MIN_DAILY_PREDICTIONS: int = 50
    MIN_MODEL_CONFIDENCE: float = 0.7
    MAX_ERROR_RATE: float = 2.0
    MIN_SYSTEM_UPTIME: float = 99.0
    
    # Anomaly detection settings
    ANOMALY_Z_THRESHOLD: float = 3.0
    ANOMALY_IQR_MULTIPLIER: float = 1.5
    DRIFT_P_VALUE_THRESHOLD: float = 0.05
    
    # Model monitoring
    ENABLE_DRIFT_DETECTION: bool = True
    ENABLE_ANOMALY_DETECTION: bool = True
    MODEL_VALIDATION_INTERVAL_HOURS: int = 24
    
    # Feature Flags
    DEMO_MODE: bool = True
    DEBUG: bool = False
    TESTING: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json" if ENVIRONMENT == "production" else "text"
    
    # Email (SMTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    # Feature flags
    ENABLE_FORECASTING: bool = True
    ENABLE_OPPORTUNITIES: bool = True
    ENABLE_BILLING: bool = True
    
    # Legal
    LEGAL_DISCLAIMER: str = "For informational purposes only. Not investment advice. CapSight does not guarantee outcomes."
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
