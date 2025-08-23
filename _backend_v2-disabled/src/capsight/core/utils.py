"""
Core utilities and base classes for CapSight backend
"""

import asyncio
import time
import json
import logging
import sys
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from functools import wraps

try:
    import pandas as pd
    import numpy as np
    from pydantic import BaseModel, Field
    from prometheus_client import Counter, Histogram, Gauge
    import structlog
except ImportError:
    # Fallback for development - will be installed via requirements
    pass


# Structured logging setup
def configure_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """Configure structured logging for CapSight"""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True
    )
    
    return structlog.get_logger()


# Metrics collection
METRICS = {
    # API metrics
    "api_requests_total": Counter("capsight_api_requests_total", "Total API requests", ["method", "endpoint", "status"]),
    "api_request_duration": Histogram("capsight_api_request_duration_seconds", "API request duration", ["method", "endpoint"]),
    
    # Data freshness metrics
    "data_freshness_seconds": Gauge("capsight_data_freshness_seconds", "Time since last data update", ["source"]),
    "data_ingestion_rate": Counter("capsight_data_ingestion_rate", "Data ingestion events per second", ["source", "status"]),
    
    # Model metrics
    "model_inference_duration": Histogram("capsight_model_inference_seconds", "Model inference time", ["model_name", "model_version"]),
    "model_accuracy": Gauge("capsight_model_accuracy", "Model accuracy metric", ["model_name", "metric_type"]),
    "predictions_total": Counter("capsight_predictions_total", "Total predictions made", ["model_name", "model_version"]),
    
    # Feature store metrics
    "feature_retrieval_duration": Histogram("capsight_feature_retrieval_seconds", "Feature retrieval time", ["feature_group"]),
    "feature_compute_duration": Histogram("capsight_feature_compute_seconds", "Feature computation time", ["feature_name"]),
}


class TimestampedData(BaseModel):
    """Base class for all timestamped data"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(..., description="Data source identifier")
    version: str = Field(default="1.0", description="Schema version")


class PredictionResult(BaseModel):
    """Standard prediction result format"""
    property_id: str
    prediction_date: datetime
    model_name: str
    model_version: str
    
    # Core predictions
    implied_caprate: float = Field(..., description="Implied cap rate")
    caprate_confidence_lower: float = Field(..., description="Lower bound of prediction interval")
    caprate_confidence_upper: float = Field(..., description="Upper bound of prediction interval")
    
    # NOI forecast
    noi_12m_growth: float = Field(..., description="12-month NOI growth forecast")
    noi_growth_confidence_lower: float = Field(...)
    noi_growth_confidence_upper: float = Field(...)
    
    # Arbitrage score
    arbitrage_score: float = Field(..., description="0-100 arbitrage opportunity score")
    arbitrage_percentile: float = Field(..., description="Percentile rank of arbitrage score")
    
    # Explanations
    shap_values: Dict[str, float] = Field(..., description="SHAP feature importance")
    key_drivers: List[str] = Field(..., description="Top 3 prediction drivers")
    risk_factors: List[str] = Field(default_factory=list, description="Key risk factors")
    
    # Metadata
    features_used: Dict[str, Any] = Field(..., description="Input features and values")
    prediction_latency_ms: float = Field(..., description="Time taken for prediction")
    data_freshness_score: float = Field(..., description="0-1 score for input data freshness")


class HealthCheck(BaseModel):
    """Health check result"""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    uptime_seconds: float = Field(...)


# Decorators and utilities

def track_execution_time(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track execution time with Prometheus metrics"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            labels_dict = labels or {}
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                METRICS[metric_name].labels(**labels_dict).observe(time.time() - start_time)
                return result
            except Exception as e:
                METRICS[metric_name].labels(**labels_dict, status="error").observe(time.time() - start_time)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            labels_dict = labels or {}
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                METRICS[metric_name].labels(**labels_dict).observe(time.time() - start_time)
                return result
            except Exception as e:
                METRICS[metric_name].labels(**labels_dict, status="error").observe(time.time() - start_time)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def validate_data_freshness(max_age_seconds: int):
    """Decorator to validate data freshness before processing"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract timestamp from first argument if it's a TimestampedData instance
            if args and isinstance(args[0], TimestampedData):
                data_age = (datetime.now(timezone.utc) - args[0].timestamp).total_seconds()
                if data_age > max_age_seconds:
                    raise ValueError(f"Data is {data_age:.0f}s old, exceeds {max_age_seconds}s threshold")
                    
                # Update freshness metric
                METRICS["data_freshness_seconds"].labels(source=args[0].source).set(data_age)
            
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator


class Circuit:
    """Circuit breaker for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        return wrapper
    
    def _on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


class BatchProcessor:
    """Generic batch processor for streaming data"""
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 10.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batch = []
        self.last_flush = time.time()
        self.lock = asyncio.Lock()
    
    async def add(self, item: Any):
        async with self.lock:
            self.batch.append(item)
            if len(self.batch) >= self.batch_size or (time.time() - self.last_flush) > self.flush_interval:
                await self._flush()
    
    async def _flush(self):
        if not self.batch:
            return
        
        batch_to_process = self.batch.copy()
        self.batch.clear()
        self.last_flush = time.time()
        
        # Process batch (override in subclass)
        await self._process_batch(batch_to_process)
    
    async def _process_batch(self, batch: List[Any]):
        """Override this method in subclasses"""
        pass


def calculate_data_freshness_score(timestamps: List[datetime], weights: Optional[List[float]] = None) -> float:
    """Calculate weighted data freshness score (0-1, where 1 is perfectly fresh)"""
    if not timestamps:
        return 0.0
    
    now = datetime.now(timezone.utc)
    ages_hours = [(now - ts).total_seconds() / 3600 for ts in timestamps]
    
    if weights is None:
        weights = [1.0] * len(ages_hours)
    
    # Exponential decay: score = exp(-age_hours / 24)
    scores = [np.exp(-age / 24) for age in ages_hours]
    weighted_score = np.average(scores, weights=weights)
    
    return float(weighted_score)


def convert_to_business_timezone(timestamp: datetime, timezone_str: str = "US/Eastern") -> datetime:
    """Convert UTC timestamp to business timezone"""
    try:
        import pytz
        business_tz = pytz.timezone(timezone_str)
        return timestamp.astimezone(business_tz)
    except ImportError:
        # Fallback to UTC if pytz not available
        return timestamp


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    """Retry function with exponential backoff"""
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func() if asyncio.iscoroutinefunction(func) else func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                break
            
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            await asyncio.sleep(delay)
    
    raise last_exception


# Global logger instance
logger = configure_logging()
