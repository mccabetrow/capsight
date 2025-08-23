"""
Subscription management endpoints with Stripe integration.
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.services.auth import AuthService
from app.services.subscriptions import SubscriptionService
from app.schemas.user import User
from app.schemas.subscriptions import SubscriptionPlan, SubscriptionStatus, SubscriptionCreate

router = APIRouter()


@router.get("/plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans() -> Any:
    """Get available subscription plans."""
    return [
        SubscriptionPlan(
            id="basic",
            name="Basic",
            description="Basic access to arbitrage opportunities",
            price=99.00,
            currency="USD",
            interval="month",
            features=[
                "Up to 10 opportunities per month",
                "Basic market forecasts",
                "Email alerts"
            ]
        ),
        SubscriptionPlan(
            id="pro",
            name="Pro",
            description="Advanced features for serious investors",
            price=299.00,
            currency="USD",
            interval="month",
            features=[
                "Up to 100 opportunities per month",
                "Advanced ML forecasts",
                "Real-time alerts",
                "Custom filters",
                "Market insights"
            ]
        ),
        SubscriptionPlan(
            id="enterprise",
            name="Enterprise",
            description="Full access for institutional investors",
            price=999.00,
            currency="USD",
            interval="month",
            features=[
                "Unlimited opportunities",
                "Custom ML models",
                "API access",
                "Priority support",
                "Custom integrations",
                "White-label options"
            ]
        )
    ]


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get current user's subscription status."""
    try:
        subscription_service = SubscriptionService(db)
        status_info = await subscription_service.get_subscription_status(current_user.id)
        
        return SubscriptionStatus(
            user_id=current_user.id,
            plan_id=status_info.get("plan_id"),
            status=status_info.get("status"),
            current_period_end=status_info.get("current_period_end"),
            cancel_at_period_end=status_info.get("cancel_at_period_end", False),
            usage=status_info.get("usage", {}),
            disclaimer=settings.LEGAL_DISCLAIMER
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription status: {str(e)}"
        )


@router.post("/create", response_model=dict)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Create a new subscription with Stripe."""
    try:
        subscription_service = SubscriptionService(db)
        
        # Create Stripe subscription
        checkout_session = await subscription_service.create_checkout_session(
            user_id=current_user.id,
            plan_id=subscription_data.plan_id,
            success_url=subscription_data.success_url,
            cancel_url=subscription_data.cancel_url
        )
        
        return {
            "checkout_session_id": checkout_session.id,
            "checkout_url": checkout_session.url,
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.post("/cancel")
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Cancel current subscription."""
    try:
        subscription_service = SubscriptionService(db)
        
        result = await subscription_service.cancel_subscription(current_user.id)
        
        return {
            "message": "Subscription cancelled successfully",
            "effective_date": result.get("cancel_at"),
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """Handle Stripe webhook events."""
    try:
        subscription_service = SubscriptionService(db)
        
        # Get the raw body and signature
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        # Process webhook
        result = await subscription_service.handle_webhook(
            payload=payload,
            sig_header=sig_header,
            endpoint_secret=settings.STRIPE_WEBHOOK_SECRET
        )
        
        return {"status": "success", "processed": result}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/usage")
async def get_usage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get current usage statistics."""
    try:
        subscription_service = SubscriptionService(db)
        
        usage = await subscription_service.get_usage_stats(current_user.id)
        
        return {
            "user_id": current_user.id,
            "usage": usage,
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage stats: {str(e)}"
        )
