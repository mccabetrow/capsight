"""
CapSight Backend Application
AI-Powered Real Estate Arbitrage Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import api_router

# Create FastAPI app
app = FastAPI(
    title="CapSight API",
    description="AI-Powered Real Estate Arbitrage Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint with legal disclaimer."""
    return {
        "message": "CapSight API - Real Estate Arbitrage Platform",
        "version": "1.0.0",
        "disclaimer": "For informational purposes only. Not investment advice. CapSight does not guarantee outcomes.",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
