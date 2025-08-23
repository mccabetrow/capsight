"""
Business Metrics API Routes
Endpoints for business dashboard and KPI monitoring
"""

from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.services.business_metrics import business_metrics
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/metrics", tags=["Business Metrics"])

@router.get("/dashboard")
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive business dashboard metrics
    Requires admin access
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        dashboard_data = await business_metrics.get_dashboard_data()
        return {
            "success": True,
            "data": dashboard_data,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics: {str(e)}")

@router.get("/kpi")
async def get_kpi_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get key performance indicators summary
    Requires admin access
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        kpi_data = await business_metrics.get_kpi_summary()
        return {
            "success": True,
            "data": kpi_data,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate KPIs: {str(e)}")

@router.get("/alerts")
async def get_business_alerts(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get business alerts and warnings
    Requires admin access
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        metrics = await business_metrics.collector.collect_metrics()
        alerts = await business_metrics._generate_alerts(metrics)
        
        return {
            "success": True,
            "data": {
                "alerts": alerts,
                "alert_count": len(alerts),
                "critical_count": len([a for a in alerts if a["type"] == "critical"]),
                "warning_count": len([a for a in alerts if a["type"] == "warning"])
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate alerts: {str(e)}")

@router.get("/health")
async def get_system_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get system health metrics
    Requires admin access
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        metrics = await business_metrics.collector.collect_metrics()
        
        # Determine overall health status
        health_status = "healthy"
        if metrics.error_rate_24h > 2.0 or metrics.system_uptime < 99.0:
            health_status = "degraded"
        elif metrics.error_rate_24h > 5.0 or metrics.system_uptime < 95.0:
            health_status = "unhealthy"
        
        return {
            "success": True,
            "data": {
                "status": health_status,
                "uptime": metrics.system_uptime,
                "error_rate": metrics.error_rate_24h,
                "response_time_p95": metrics.api_response_time_p95,
                "active_users": metrics.daily_active_users,
                "predictions_today": metrics.daily_predictions,
                "model_health": {
                    "avg_confidence": metrics.avg_confidence_score,
                    "high_confidence_rate": (metrics.high_confidence_predictions / 
                                           max(metrics.daily_predictions, 1)) * 100
                }
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")

@router.get("/trends")
async def get_market_trends(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get market trends and insights
    Available to all authenticated users
    """
    try:
        metrics = await business_metrics.collector.collect_metrics()
        
        return {
            "success": True,
            "data": {
                "market_trends": {
                    "top_markets": metrics.top_markets,
                    "property_types": metrics.property_type_distribution,
                    "growth_trends": metrics.prediction_trends
                },
                "model_insights": {
                    "avg_confidence": metrics.avg_confidence_score,
                    "avg_investment_score": metrics.avg_investment_score,
                    "avg_prediction_value": metrics.avg_prediction_value
                },
                "market_summary": {
                    "total_predictions_today": metrics.daily_predictions,
                    "high_confidence_predictions": metrics.high_confidence_predictions,
                    "market_coverage": len(metrics.top_markets)
                }
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get market trends: {str(e)}")
