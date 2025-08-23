"""
Data ingestion endpoints for pulling real estate data from external APIs.
"""

from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth import AuthService
from app.services.data_ingestion import DataIngestionService
from app.schemas.user import User
from app.schemas.data import DataSource, IngestionStatus, IngestionRequest

router = APIRouter()


@router.post("/ingest-data", response_model=IngestionStatus)
async def ingest_data(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Trigger data ingestion from external sources.
    
    **Legal Notice**: All data ingested is subject to the disclaimer:
    "For informational purposes only. Not investment advice. CapSight does not guarantee outcomes."
    """
    try:
        ingestion_service = DataIngestionService(db)
        
        # Start background ingestion task
        task_id = await ingestion_service.start_ingestion(
            source=request.source,
            parameters=request.parameters,
            user_id=current_user.id
        )
        
        # Add background task
        background_tasks.add_task(
            ingestion_service.run_ingestion,
            task_id=task_id,
            source=request.source,
            parameters=request.parameters
        )
        
        return IngestionStatus(
            task_id=task_id,
            status="started",
            message=f"Data ingestion from {request.source} started",
            disclaimer="For informational purposes only. Not investment advice. CapSight does not guarantee outcomes."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data ingestion failed: {str(e)}"
        )


@router.get("/ingestion-status/{task_id}", response_model=IngestionStatus)
async def get_ingestion_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get status of data ingestion task."""
    try:
        ingestion_service = DataIngestionService(db)
        status_info = await ingestion_service.get_ingestion_status(task_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion task not found"
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ingestion status: {str(e)}"
        )


@router.get("/data-sources", response_model=List[DataSource])
async def get_data_sources(
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get available data sources."""
    try:
        return [
            DataSource(
                name="zillow",
                description="Zillow property listings and sales data",
                available=True,
                parameters=["location", "property_type", "date_range"]
            ),
            DataSource(
                name="redfin", 
                description="Redfin market data and listings",
                available=True,
                parameters=["market", "price_range", "date_range"]
            ),
            DataSource(
                name="fred",
                description="Federal Reserve Economic Data (interest rates, housing starts)",
                available=True,
                parameters=["series_id", "date_range"]
            )
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data sources: {str(e)}"
        )


@router.get("/market-data/{location}")
async def get_market_data(
    location: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get market data for a specific location."""
    try:
        ingestion_service = DataIngestionService(db)
        market_data = await ingestion_service.get_market_data(location)
        
        return {
            "location": location,
            "data": market_data,
            "disclaimer": "For informational purposes only. Not investment advice. CapSight does not guarantee outcomes.",
            "last_updated": market_data.get("last_updated") if market_data else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market data: {str(e)}"
        )
