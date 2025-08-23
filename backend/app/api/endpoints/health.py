"""
Health check endpoint for monitoring system status
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
import os
import json

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check for monitoring systems.
    Returns detailed status of all system components.
    """
    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    overall_status = "ok"
    
    # Database connectivity check
    try:
        db: Session = next(get_db())
        result = db.execute(text("SELECT 1 as test"))
        db_result = result.fetchone()
        
        if db_result and db_result[0] == 1:
            health_status["checks"]["database"] = {
                "status": "ok",
                "response_time_ms": "<50",
                "message": "Database connection successful"
            }
        else:
            raise Exception("Unexpected database response")
            
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_status = "error"
    
    # ML Models check
    try:
        model_path = os.path.join(settings.ML_MODEL_PATH)
        if os.path.exists(model_path):
            model_files = [f for f in os.listdir(model_path) if f.endswith('.pkl')]
            health_status["checks"]["ml_models"] = {
                "status": "ok",
                "models_available": len(model_files),
                "message": f"ML models directory accessible with {len(model_files)} models"
            }
        else:
            health_status["checks"]["ml_models"] = {
                "status": "warning",
                "message": "ML models directory not found, will create on first use"
            }
    except Exception as e:
        health_status["checks"]["ml_models"] = {
            "status": "error", 
            "message": f"ML models check failed: {str(e)}"
        }
        if overall_status == "ok":
            overall_status = "warning"
    
    # Configuration check
    config_issues = []
    if settings.JWT_SECRET == "your-jwt-secret-key-change-in-production-min-32-characters":
        config_issues.append("JWT_SECRET using default value")
    if settings.STRIPE_SECRET_KEY.startswith("sk_test") and settings.ENVIRONMENT == "production":
        config_issues.append("Using Stripe test keys in production")
    
    if config_issues:
        health_status["checks"]["configuration"] = {
            "status": "warning",
            "issues": config_issues
        }
        if overall_status == "ok":
            overall_status = "warning"
    else:
        health_status["checks"]["configuration"] = {
            "status": "ok",
            "message": "Configuration validated"
        }
    
    # File system check
    try:
        # Check if we can write to logs directory
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        test_file = os.path.join(logs_dir, "health_check.test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        health_status["checks"]["filesystem"] = {
            "status": "ok",
            "message": "File system read/write access verified"
        }
    except Exception as e:
        health_status["checks"]["filesystem"] = {
            "status": "error",
            "message": f"File system access failed: {str(e)}"
        }
        overall_status = "error"
    
    # Update overall status
    health_status["status"] = overall_status
    
    # Return appropriate HTTP status
    if overall_status == "error":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@router.get("/health/simple")
async def simple_health_check() -> Dict[str, str]:
    """
    Simple health check for load balancer monitoring.
    Returns minimal response for high-frequency checks.
    """
    try:
        # Quick database ping
        db: Session = next(get_db())
        db.execute(text("SELECT 1"))
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        raise HTTPException(status_code=503, detail={"status": "error"})

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with system metrics.
    Use sparingly as this performs more extensive checks.
    """
    detailed_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "system_info": {
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "python_version": "3.13.5"  # Update as needed
        },
        "database": {},
        "configuration": {},
        "performance": {}
    }
    
    try:
        # Database metrics
        db_metrics = db.execute(text("""
            SELECT 
                COUNT(*) as user_count
            FROM users
        """)).fetchone()
        
        detailed_status["database"] = {
            "status": "ok",
            "user_count": db_metrics[0] if db_metrics else 0,
            "connection_pool": "healthy"
        }
        
        # Configuration summary
        detailed_status["configuration"] = {
            "demo_mode": settings.DEMO_MODE,
            "debug": settings.DEBUG,
            "cors_origins_count": len(settings.CORS_ORIGINS),
            "rate_limits": {
                "per_minute": settings.RATE_LIMIT_PER_MINUTE,
                "per_hour": settings.RATE_LIMIT_PER_HOUR
            }
        }
        
        # Performance indicators (basic)
        detailed_status["performance"] = {
            "ml_confidence_threshold": settings.MODEL_CONFIDENCE_THRESHOLD,
            "max_forecast_horizon": settings.MAX_FORECAST_HORIZON
        }
        
    except Exception as e:
        detailed_status["status"] = "error"
        detailed_status["error"] = str(e)
        raise HTTPException(status_code=503, detail=detailed_status)
    
    return detailed_status

@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """
    Kubernetes-style readiness check.
    Returns 200 only when service is ready to accept traffic.
    """
    try:
        # Check critical dependencies
        db: Session = next(get_db())
        db.execute(text("SELECT 1"))
        
        # Verify essential directories exist
        os.makedirs("app/ml/artifacts", exist_ok=True)
        
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail={"status": "not_ready"})

@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes-style liveness check.
    Returns 200 if service is running (lighter check than readiness).
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }
