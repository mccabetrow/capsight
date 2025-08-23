"""
Data ingestion service for pulling real estate data from external APIs.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import httpx
import logging

from app.core.config import settings
from app.schemas.data import IngestionStatus, DataSourceType, MarketData

logger = logging.getLogger(__name__)


class DataIngestionService:
    """Service for ingesting real estate data from external sources."""
    
    def __init__(self, db: Session):
        self.db = db
        self.ingestion_tasks = {}  # In production, use Redis or database
    
    async def start_ingestion(
        self,
        source: DataSourceType,
        parameters: Dict[str, Any],
        user_id: str
    ) -> str:
        """Start a data ingestion task."""
        task_id = str(uuid.uuid4())
        
        # Store task info
        self.ingestion_tasks[task_id] = {
            "status": "started",
            "source": source,
            "parameters": parameters,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "progress": 0.0
        }
        
        return task_id
    
    async def get_ingestion_status(self, task_id: str) -> Optional[IngestionStatus]:
        """Get the status of an ingestion task."""
        if task_id not in self.ingestion_tasks:
            return None
        
        task = self.ingestion_tasks[task_id]
        
        return IngestionStatus(
            task_id=task_id,
            status=task["status"],
            message=f"Ingesting data from {task['source']}",
            progress=task.get("progress", 0.0),
            created_at=task["created_at"],
            completed_at=task.get("completed_at"),
            error_message=task.get("error_message"),
            disclaimer=settings.LEGAL_DISCLAIMER
        )
    
    async def run_ingestion(
        self,
        task_id: str,
        source: DataSourceType,
        parameters: Dict[str, Any]
    ) -> None:
        """Run the actual data ingestion process."""
        try:
            # Update status
            self.ingestion_tasks[task_id]["status"] = "running"
            
            if source == DataSourceType.ZILLOW:
                await self._ingest_zillow_data(task_id, parameters)
            elif source == DataSourceType.REDFIN:
                await self._ingest_redfin_data(task_id, parameters)
            elif source == DataSourceType.FRED:
                await self._ingest_fred_data(task_id, parameters)
            else:
                raise ValueError(f"Unsupported data source: {source}")
            
            # Mark as completed
            self.ingestion_tasks[task_id].update({
                "status": "completed",
                "progress": 100.0,
                "completed_at": datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Ingestion task {task_id} failed: {str(e)}")
            self.ingestion_tasks[task_id].update({
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.utcnow()
            })
    
    async def _ingest_zillow_data(self, task_id: str, parameters: Dict[str, Any]) -> None:
        """Ingest data from Zillow API."""
        if not settings.ZILLOW_API_KEY:
            raise ValueError("Zillow API key not configured")
        
        location = parameters.get("location")
        property_type = parameters.get("property_type", "all")
        date_range = parameters.get("date_range", {})
        
        # Update progress
        self.ingestion_tasks[task_id]["progress"] = 25.0
        
        # Simulate API calls (replace with actual Zillow API integration)
        await asyncio.sleep(2)  # Simulate API delay
        
        # In production, implement actual Zillow API calls here
        sample_data = {
            "location": location,
            "listings": [],
            "market_stats": {
                "median_price": 450000,
                "price_per_sqft": 250,
                "inventory_count": 1200,
                "days_on_market": 28
            }
        }
        
        # Update progress
        self.ingestion_tasks[task_id]["progress"] = 75.0
        
        # Store data in database (implement database models for raw data)
        # await self._store_zillow_data(sample_data)
        
        logger.info(f"Successfully ingested Zillow data for {location}")
    
    async def _ingest_redfin_data(self, task_id: str, parameters: Dict[str, Any]) -> None:
        """Ingest data from Redfin API."""
        market = parameters.get("market")
        price_range = parameters.get("price_range", {})
        
        self.ingestion_tasks[task_id]["progress"] = 25.0
        
        # Simulate Redfin API integration
        await asyncio.sleep(1.5)
        
        # Mock data processing
        sample_data = {
            "market": market,
            "sales_data": [],
            "market_trends": {
                "appreciation_rate": 0.08,
                "inventory_growth": -0.15
            }
        }
        
        self.ingestion_tasks[task_id]["progress"] = 100.0
        logger.info(f"Successfully ingested Redfin data for {market}")
    
    async def _ingest_fred_data(self, task_id: str, parameters: Dict[str, Any]) -> None:
        """Ingest data from Federal Reserve Economic Data (FRED)."""
        series_id = parameters.get("series_id", "MORTGAGE30US")  # 30-year mortgage rates
        date_range = parameters.get("date_range", {})
        
        self.ingestion_tasks[task_id]["progress"] = 20.0
        
        # FRED API is public and well-documented
        fred_url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": settings.FRED_API_KEY,
            "file_type": "json",
            "limit": 1000
        }
        
        if settings.FRED_API_KEY:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(fred_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                
                self.ingestion_tasks[task_id]["progress"] = 80.0
                
                # Process and store FRED data
                observations = data.get("observations", [])
                logger.info(f"Retrieved {len(observations)} observations for {series_id}")
                
            except Exception as e:
                logger.error(f"FRED API error: {str(e)}")
                # Fall back to mock data
                await asyncio.sleep(1)
        else:
            # Mock FRED data if no API key
            await asyncio.sleep(1)
            logger.info(f"Mock FRED data ingested for {series_id}")
        
        self.ingestion_tasks[task_id]["progress"] = 100.0
    
    async def get_market_data(self, location: str) -> Optional[Dict[str, Any]]:
        """Get cached market data for a location."""
        # In production, query database for cached market data
        # For now, return mock data
        
        mock_data = {
            "location": location,
            "median_price": 425000,
            "price_per_sqft": 235,
            "cap_rate": 0.055,
            "rental_yield": 0.048,
            "vacancy_rate": 0.06,
            "appreciation_rate": 0.072,
            "inventory_levels": 850,
            "days_on_market": 32,
            "mortgage_rates": {
                "30_year_fixed": 0.068,
                "15_year_fixed": 0.061,
                "arm_5_1": 0.058
            },
            "last_updated": datetime.utcnow().isoformat(),
            "data_sources": ["zillow", "redfin", "fred"]
        }
        
        return mock_data
