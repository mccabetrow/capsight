"""
API router configuration for CapSight.
"""

from fastapi import APIRouter
from app.api.endpoints import data_ingestion, predictions, opportunities, auth, users, subscriptions, health, forecasts

api_router = APIRouter()

# Include all API endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"]) 
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
api_router.include_router(data_ingestion.router, prefix="/data", tags=["Data Ingestion"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])
api_router.include_router(forecasts.router, prefix="/forecasts", tags=["Forecasts"])

# Health checks (no prefix for monitoring tools)
api_router.include_router(health.router, tags=["Health"])
