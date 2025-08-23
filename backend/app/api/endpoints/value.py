"""
Property valuation endpoints.
Implements robust weighted median methodology with conformal prediction.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.valuation import (
    ValuationRequest, 
    ValuationResponse, 
    ValuationMetadata,
    ConformalPrediction
)
from app.services.valuation import ValuationService
from app.services.accuracy import AccuracyService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/value", response_model=ValuationResponse)
async def get_property_value(
    request: ValuationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get property valuation using weighted median methodology.
    
    Returns robust valuation with confidence intervals via conformal prediction.
    Automatically logs requests for accuracy monitoring.
    """
    try:
        logger.info(f"Valuation request for user {current_user.id}: {request.dict()}")
        
        # Initialize services
        valuation_service = ValuationService(db)
        accuracy_service = AccuracyService(db)
        
        # Get valuation
        result = await valuation_service.get_valuation(
            property_type=request.property_type,
            building_size=request.building_size,
            lot_size=request.lot_size,
            year_built=request.year_built,
            latitude=request.latitude,
            longitude=request.longitude,
            market_slug=request.market_slug,
            user_id=current_user.id
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Insufficient comparable data for this property"
            )
        
        # Log request for accuracy monitoring
        background_tasks.add_task(
            accuracy_service.log_valuation_request,
            user_id=current_user.id,
            request_data=request.dict(),
            result_data=result.dict()
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Valuation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during valuation"
        )

@router.get("/value/health")
async def valuation_health(db: Session = Depends(get_db)):
    """Check valuation service health."""
    try:
        valuation_service = ValuationService(db)
        health_check = await valuation_service.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "details": health_check
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )

@router.get("/value/markets")
async def get_available_markets(db: Session = Depends(get_db)):
    """Get list of available markets for valuation."""
    try:
        valuation_service = ValuationService(db)
        markets = await valuation_service.get_available_markets()
        
        return {
            "markets": markets,
            "total": len(markets)
        }
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching available markets"
        )
