"""
CapSight Backend v2 - Main Application Module
Production-ready real-time predictive analytics for CRE investors
"""

from .core.config import settings
from .core.utils import logger

from .ingestion import StreamingIngestionService, BatchETLService
from .models import FeatureStoreService, RealTimeFeatureService, ModelRegistry
from .api import app, prediction_service
from .monitoring import HealthChecker

__version__ = "2.1.0"
__title__ = "CapSight Backend v2"
__description__ = "Real-time predictive analytics for commercial real estate arbitrage"

# Export main components
__all__ = [
    "settings",
    "logger", 
    "app",
    "prediction_service",
    "StreamingIngestionService",
    "BatchETLService",
    "FeatureStoreService",
    "RealTimeFeatureService", 
    "ModelRegistry",
    "HealthChecker"
]

# Log initialization
logger.info("CapSight Backend v2 module loaded", 
           version=__version__,
           environment=settings.environment)
