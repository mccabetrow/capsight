"""
CapSight Backend v2 - FastAPI Application Entry Point
Production ASGI application for deployment
"""

import asyncio
from contextlib import asynccontextmanager

from capsight import app, prediction_service, logger
from capsight.ingestion import StreamingIngestionService
from capsight.monitoring import HealthChecker

# Global service instances
ingestion_service = None
health_checker = None

@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager"""
    global ingestion_service, health_checker
    
    logger.info("Starting CapSight Backend v2")
    
    # Initialize services
    try:
        # Initialize prediction service (already handled in app startup)
        logger.info("Prediction service initialized")
        
        # Initialize streaming ingestion
        ingestion_service = StreamingIngestionService()
        # Note: Start ingestion in background task to avoid blocking startup
        asyncio.create_task(ingestion_service.start())
        logger.info("Streaming ingestion service started")
        
        # Initialize health checker
        health_checker = HealthChecker()
        await health_checker.initialize()
        logger.info("Health monitoring initialized")
        
        logger.info("CapSight Backend v2 startup complete")
        
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        raise
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    logger.info("Shutting down CapSight Backend v2")
    
    if ingestion_service:
        await ingestion_service.stop()
    
    logger.info("CapSight Backend v2 shutdown complete")

# Configure lifespan
app.router.lifespan_context = lifespan

# Main FastAPI application
application = app

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:application",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to False for production
        workers=1,     # Use multiple workers for production
        log_config=None  # Use our structured logging
    )
