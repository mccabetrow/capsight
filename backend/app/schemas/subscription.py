"""
Subscription schemas for request/response validation.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class SubscriptionBase(BaseModel):
    """Base subscription schema with common fields."""
    user_id: uuid.UUID = Field(..., description="Associated user ID")
    tier: str = Field(..., max_length=50, description="Subscription tier")
    status: str = Field(default="active", max_length=50, description="Subscription status")
    price_monthly: Decimal = Field(..., ge=0, description="Monthly price")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Yearly price (if applicable)")
    billing_cycle: str = Field(default="monthly", max_length=20, description="Billing cycle")
    features: Optional[Dict[str, Any]] = Field(None, description="Available features")
    usage_limits: Optional[Dict[str, Any]] = Field(None, description="Usage limits")
    stripe_customer_id: Optional[str] = Field(None, max_length=255, description="Stripe customer ID")
    stripe_subscription_id: Optional[str] = Field(None, max_length=255, description="Stripe subscription ID")
    stripe_price_id: Optional[str] = Field(None, max_length=255, description="Stripe price ID")
    current_period_start: Optional[datetime] = Field(None, description="Current billing period start")
    current_period_end: Optional[datetime] = Field(None, description="Current billing period end")
    trial_start: Optional[datetime] = Field(None, description="Trial period start")
    trial_end: Optional[datetime] = Field(None, description="Trial period end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    is_active: bool = Field(default=True, description="Whether subscription is active")


class SubscriptionCreate(BaseModel):
    """Subscription creation schema."""
    user_id: uuid.UUID = Field(..., description="Associated user ID")
    tier: str = Field(..., max_length=50, description="Subscription tier")
    billing_cycle: str = Field(default="monthly", max_length=20, description="Billing cycle")
    stripe_price_id: Optional[str] = Field(None, max_length=255, description="Stripe price ID")
    trial_days: Optional[int] = Field(None, ge=0, le=365, description="Trial period in days")


class SubscriptionRead(SubscriptionBase):
    """Subscription read schema for API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Subscription ID")
    created_at: datetime = Field(..., description="Subscription creation timestamp")
    updated_at: datetime = Field(..., description="Subscription last update timestamp")


class SubscriptionUpdate(BaseModel):
    """Subscription update schema."""
    tier: Optional[str] = Field(None, max_length=50, description="Subscription tier")
    status: Optional[str] = Field(None, max_length=50, description="Subscription status")
    price_monthly: Optional[Decimal] = Field(None, ge=0, description="Monthly price")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Yearly price")
    billing_cycle: Optional[str] = Field(None, max_length=20, description="Billing cycle")
    features: Optional[Dict[str, Any]] = Field(None, description="Available features")
    usage_limits: Optional[Dict[str, Any]] = Field(None, description="Usage limits")
    stripe_customer_id: Optional[str] = Field(None, max_length=255, description="Stripe customer ID")
    stripe_subscription_id: Optional[str] = Field(None, max_length=255, description="Stripe subscription ID")
    stripe_price_id: Optional[str] = Field(None, max_length=255, description="Stripe price ID")
    current_period_start: Optional[datetime] = Field(None, description="Current billing period start")
    current_period_end: Optional[datetime] = Field(None, description="Current billing period end")
    trial_start: Optional[datetime] = Field(None, description="Trial period start")
    trial_end: Optional[datetime] = Field(None, description="Trial period end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    is_active: Optional[bool] = Field(None, description="Whether subscription is active")


class SubscriptionInDB(SubscriptionBase):
    """Subscription schema for database operations."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SubscriptionSummary(BaseModel):
    """Subscription summary schema for list views."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Subscription ID")
    user_id: uuid.UUID = Field(..., description="Associated user ID")
    tier: str = Field(..., description="Subscription tier")
    status: str = Field(..., description="Subscription status")
    price_monthly: Decimal = Field(..., description="Monthly price")
    billing_cycle: str = Field(..., description="Billing cycle")
    current_period_end: Optional[datetime] = Field(None, description="Current billing period end")
    is_active: bool = Field(..., description="Whether subscription is active")
    created_at: datetime = Field(..., description="Subscription creation timestamp")


class SubscriptionTier(BaseModel):
    """Subscription tier definition schema."""
    name: str = Field(..., max_length=50, description="Tier name")
    display_name: str = Field(..., max_length=100, description="Display name")
    description: str = Field(..., description="Tier description")
    price_monthly: Decimal = Field(..., ge=0, description="Monthly price")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Yearly price")
    features: Dict[str, Any] = Field(..., description="Available features")
    usage_limits: Dict[str, Any] = Field(..., description="Usage limits")
    stripe_price_id_monthly: Optional[str] = Field(None, description="Stripe monthly price ID")
    stripe_price_id_yearly: Optional[str] = Field(None, description="Stripe yearly price ID")
    is_popular: bool = Field(default=False, description="Whether this is a popular tier")
    sort_order: int = Field(default=0, description="Display sort order")


class SubscriptionUsage(BaseModel):
    """Subscription usage tracking schema."""
    subscription_id: uuid.UUID = Field(..., description="Subscription ID")
    usage_period: str = Field(..., description="Usage period (e.g., '2024-01')")
    api_calls: int = Field(default=0, description="API calls made")
    properties_analyzed: int = Field(default=0, description="Properties analyzed")
    forecasts_generated: int = Field(default=0, description="Forecasts generated")
    opportunities_identified: int = Field(default=0, description="Opportunities identified")
    custom_metrics: Optional[Dict[str, int]] = Field(None, description="Custom usage metrics")
    created_at: datetime = Field(..., description="Usage record creation timestamp")
    updated_at: datetime = Field(..., description="Usage record last update timestamp")


class BillingEvent(BaseModel):
    """Billing event schema."""
    subscription_id: uuid.UUID = Field(..., description="Subscription ID")
    event_type: str = Field(..., max_length=100, description="Event type")
    amount: Decimal = Field(..., description="Amount charged/refunded")
    currency: str = Field(default="USD", max_length=3, description="Currency code")
    stripe_invoice_id: Optional[str] = Field(None, max_length=255, description="Stripe invoice ID")
    stripe_payment_intent_id: Optional[str] = Field(None, max_length=255, description="Stripe payment intent ID")
    status: str = Field(..., max_length=50, description="Event status")
    description: Optional[str] = Field(None, description="Event description")
    event_date: datetime = Field(..., description="Event timestamp")
    created_at: datetime = Field(..., description="Record creation timestamp")


class SubscriptionAnalytics(BaseModel):
    """Subscription analytics schema."""
    total_subscriptions: int = Field(..., description="Total number of subscriptions")
    active_subscriptions: int = Field(..., description="Number of active subscriptions")
    subscriptions_by_tier: Dict[str, int] = Field(..., description="Count by tier")
    subscriptions_by_status: Dict[str, int] = Field(..., description="Count by status")
    monthly_recurring_revenue: Decimal = Field(..., description="Monthly recurring revenue")
    annual_recurring_revenue: Decimal = Field(..., description="Annual recurring revenue")
    average_revenue_per_user: Decimal = Field(..., description="Average revenue per user")
    churn_rate: Decimal = Field(..., description="Monthly churn rate")
    trial_conversion_rate: Decimal = Field(..., description="Trial to paid conversion rate")
    created_at: datetime = Field(..., description="Analytics snapshot timestamp")
