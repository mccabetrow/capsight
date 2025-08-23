from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ...core.database import get_db
from ...core.auth import get_current_user
from ...models.user import User
from ...models.audit import AuditLog
from ...schemas.audit import AuditLogResponse, AuditStatsResponse

router = APIRouter()

@router.get("/audit", response_model=Dict[str, Any])
async def get_audit_logs(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    route: Optional[str] = Query(None, description="Filter by API route"),
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    limit: int = Query(100, le=1000, description="Number of records to return"),
    offset: int = Query(0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit logs for compliance tracking.
    Available to Pro and Enterprise users only.
    """
    # Check user has access to audit logs
    if current_user.subscription_tier not in ['pro', 'enterprise']:
        raise HTTPException(
            status_code=403, 
            detail="Audit logs are available to Pro and Enterprise plans only"
        )
    
    # Parse dates
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)  # Include full end day
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Build query filters
    filters = [
        AuditLog.timestamp >= start_dt,
        AuditLog.timestamp < end_dt
    ]
    
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if route:
        filters.append(AuditLog.route.ilike(f"%{route}%"))
    if model_version:
        filters.append(AuditLog.model_version == model_version)
    
    # Get total count
    total_query = db.query(func.count(AuditLog.id)).filter(and_(*filters))
    total = total_query.scalar()
    
    # Get paginated results
    logs_query = db.query(
        AuditLog, 
        User.email.label('user_email')
    ).join(
        User, AuditLog.user_id == User.id
    ).filter(
        and_(*filters)
    ).order_by(
        AuditLog.timestamp.desc()
    ).offset(offset).limit(limit)
    
    logs = logs_query.all()
    
    # Format response
    items = []
    for log, user_email in logs:
        items.append({
            "id": log.id,
            "request_id": log.request_id,
            "user_id": log.user_id,
            "user_email": user_email,
            "route": log.route,
            "model_version": log.model_version,
            "response_type": log.response_type,
            "confidence": log.confidence,
            "disclaimer_version": log.disclaimer_version,
            "latency_ms": log.latency_ms,
            "timestamp": log.timestamp.isoformat(),
            "metadata": log.metadata or {}
        })
    
    # Calculate summary stats
    stats_query = db.query(
        func.count(AuditLog.id).label('total_predictions'),
        func.avg(AuditLog.confidence).label('avg_confidence'),
        func.count(func.distinct(AuditLog.user_id)).label('unique_users')
    ).filter(and_(*filters))
    
    stats = stats_query.first()
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "stats": {
            "total_predictions": stats.total_predictions or 0,
            "avg_confidence": float(stats.avg_confidence or 0),
            "unique_users": stats.unique_users or 0
        }
    }

@router.post("/audit/log")
async def create_audit_log(
    request_id: str,
    route: str,
    model_version: str,
    response_type: str,
    confidence: float,
    disclaimer_version: str = "1.0",
    latency_ms: int = 0,
    metadata: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an audit log entry.
    Called automatically by ML endpoints.
    """
    audit_log = AuditLog(
        request_id=request_id,
        user_id=current_user.id,
        route=route,
        model_version=model_version,
        response_type=response_type,
        confidence=confidence,
        disclaimer_version=disclaimer_version,
        latency_ms=latency_ms,
        metadata=metadata or {},
        timestamp=datetime.utcnow()
    )
    
    db.add(audit_log)
    db.commit()
    
    return {"status": "logged", "id": audit_log.id}
