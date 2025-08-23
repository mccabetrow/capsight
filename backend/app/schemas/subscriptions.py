"""
Subscription and billing schemas.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class SubscriptionPlanId(str, Enum):
    """Subscription plan identifiers."""
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status values."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"


class SubscriptionPlan(BaseModel):
    """Subscription plan details."""
    id: SubscriptionPlanId
    name: str
    description: str
    price: float
    currency: str = "USD"
    interval: str = "month"  # month, year
    features: List[str]
    opportunity_limit: Optional[int] = None  # None = unlimited
    api_calls_limit: Optional[int] = None
    support_level: str = "standard"  # standard, priority, dedicated
    custom_models: bool = False
    white_label: bool = False


class SubscriptionCreate(BaseModel):
    """Create subscription request."""
    plan_id: SubscriptionPlanId
    success_url: str
    cancel_url: str
    trial_days: Optional[int] = None


class SubscriptionStatus(BaseModel):
    """Current subscription status."""
    user_id: str
    plan_id: Optional[SubscriptionPlanId] = None
    status: Optional[SubscriptionStatus] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    
    # Usage tracking
    usage: Dict[str, Any] = {}
    
    # Stripe metadata
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    
    disclaimer: str

    class Config:
        from_attributes = True


class UsageStats(BaseModel):
    """Usage statistics for current billing period."""
    user_id: str
    billing_period_start: datetime
    billing_period_end: datetime
    
    # Usage metrics
    opportunities_viewed: int = 0
    predictions_requested: int = 0
    api_calls_made: int = 0
    alerts_triggered: int = 0
    
    # Limits based on plan
    opportunities_limit: Optional[int] = None
    predictions_limit: Optional[int] = None
    api_calls_limit: Optional[int] = None
    
    # Percentage used
    usage_percentage: Dict[str, float] = {}
    
    class Config:
        from_attributes = True


class BillingHistory(BaseModel):
    """Billing history record."""
    invoice_id: str
    user_id: str
    plan_id: SubscriptionPlanId
    amount: float
    currency: str = "USD"
    status: str  # paid, pending, failed
    invoice_date: datetime
    due_date: datetime
    paid_date: Optional[datetime] = None
    stripe_invoice_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class WebhookEvent(BaseModel):
    """Stripe webhook event."""
    event_id: str
    event_type: str
    user_id: Optional[str] = None
    subscription_id: Optional[str] = None
    data: Dict[str, Any]
    processed: bool = False
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
