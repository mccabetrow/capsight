"""
API module initialization
"""

from .endpoints import app, prediction_service, PredictionService

__all__ = ["app", "prediction_service", "PredictionService"]
