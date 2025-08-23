"""
Subscription service for managing user subscriptions and billing.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.schemas.subscription import (
    SubscriptionCreate, SubscriptionRead, SubscriptionUpdate,
    BillingEvent, SubscriptionAnalytics, SubscriptionUsage
)


class SubscriptionService:
    """Service for managing user subscriptions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_subscription(self, user_id: uuid.UUID) -> Optional[SubscriptionRead]:
        """Get active subscription for a user."""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        ).first()
        
        if subscription:
            return self._to_read(subscription)
        return None
    
    def create_subscription(
        self, 
        subscription_data: SubscriptionCreate, 
        user_id: uuid.UUID
    ) -> SubscriptionRead:
        """Create a new subscription."""
        # Get tier pricing (mock data)
        tier_pricing = self._get_tier_pricing(subscription_data.tier)
        
        db_subscription = Subscription(
            user_id=user_id,
            tier=subscription_data.tier,
            status="active",
            price_monthly=tier_pricing["monthly"],
            price_yearly=tier_pricing.get("yearly"),
            billing_cycle=subscription_data.billing_cycle,
            features=tier_pricing.get("features", {}),
            usage_limits=tier_pricing.get("usage_limits", {}),
            stripe_price_id=subscription_data.stripe_price_id,
            current_period_start=datetime.utcnow(),
            current_period_end=self._calculate_period_end(subscription_data.billing_cycle),
            is_active=True
        )
        
        # Set trial period if specified
        if subscription_data.trial_days and subscription_data.trial_days > 0:
            db_subscription.trial_start = datetime.utcnow()
            db_subscription.trial_end = datetime.utcnow() + timedelta(days=subscription_data.trial_days)
        
        self.db.add(db_subscription)
        self.db.commit()
        self.db.refresh(db_subscription)
        
        return self._to_read(db_subscription)
    
    def update_user_subscription(
        self, 
        user_id: uuid.UUID, 
        subscription_update: SubscriptionUpdate
    ) -> Optional[SubscriptionRead]:
        """Update user's subscription."""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        ).first()
        
        if not subscription:
            return None
        
        # Update fields
        update_data = subscription_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(subscription, field) and value is not None:
                setattr(subscription, field, value)
        
        subscription.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(subscription)
        
        return self._to_read(subscription)
    
    def cancel_user_subscription(self, user_id: uuid.UUID) -> bool:
        """Cancel user's subscription."""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        ).first()
        
        if subscription:
            subscription.status = "cancelled"
            subscription.canceled_at = datetime.utcnow()
            subscription.is_active = False
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    def reactivate_user_subscription(self, user_id: uuid.UUID) -> Optional[SubscriptionRead]:
        """Reactivate user's subscription."""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "cancelled"
        ).first()
        
        if subscription:
            subscription.status = "active"
            subscription.canceled_at = None
            subscription.is_active = True
            subscription.updated_at = datetime.utcnow()
            # Extend current period
            subscription.current_period_end = self._calculate_period_end(subscription.billing_cycle)
            self.db.commit()
            self.db.refresh(subscription)
            return self._to_read(subscription)
        
        return None
    
    def get_billing_history(self, user_id: uuid.UUID, limit: int = 10) -> List[BillingEvent]:
        """Get billing history for a user (mock implementation)."""
        # In production, this would fetch from actual billing events table
        return []
    
    def create_billing_portal_session(self, user_id: uuid.UUID) -> Optional[str]:
        """Create Stripe billing portal session (stub implementation)."""
        # In production, this would integrate with Stripe's billing portal
        return "https://billing.stripe.com/session/mock_session_id"
    
    def create_checkout_session(
        self, 
        user_id: uuid.UUID, 
        tier: str, 
        billing_cycle: str
    ) -> Optional[str]:
        """Create Stripe checkout session (stub implementation)."""
        # In production, this would create an actual Stripe checkout session
        return f"https://checkout.stripe.com/pay/mock_checkout_session?tier={tier}&cycle={billing_cycle}"
    
    def get_usage_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        # Mock usage data - in production, this would come from actual usage tracking
        return {
            "current_period": "2024-01-01 to 2024-02-01",
            "api_calls": 150,
            "properties_analyzed": 25,
            "forecasts_generated": 8,
            "opportunities_identified": 12,
            "limits": {
                "api_calls_per_month": 1000,
                "properties_per_month": 100,
                "forecasts_per_month": 25,
                "opportunities_per_month": 50
            },
            "usage_percentage": {
                "api_calls": 15.0,
                "properties": 25.0,
                "forecasts": 32.0,
                "opportunities": 24.0
            }
        }
    
    def get_all_subscriptions(self, skip: int = 0, limit: int = 100) -> List[SubscriptionRead]:
        """Get all subscriptions (admin only)."""
        subscriptions = self.db.query(Subscription).offset(skip).limit(limit).all()
        return [self._to_read(sub) for sub in subscriptions]
    
    def get_subscription_analytics(self) -> SubscriptionAnalytics:
        """Get subscription analytics (admin only)."""
        total_subscriptions = self.db.query(Subscription).count()
        active_subscriptions = self.db.query(Subscription).filter(
            Subscription.is_active == True
        ).count()
        
        # Subscriptions by tier
        tier_counts = {}
        tiers = self.db.query(
            Subscription.tier, 
            self.db.func.count(Subscription.id)
        ).group_by(Subscription.tier).all()
        
        for tier, count in tiers:
            tier_counts[tier] = count
        
        # Subscriptions by status
        status_counts = {}
        statuses = self.db.query(
            Subscription.status, 
            self.db.func.count(Subscription.id)
        ).group_by(Subscription.status).all()
        
        for status, count in statuses:
            status_counts[status] = count
        
        # Calculate MRR (Monthly Recurring Revenue)
        active_subs = self.db.query(Subscription).filter(
            Subscription.is_active == True
        ).all()
        
        mrr = sum(float(sub.price_monthly) for sub in active_subs if sub.price_monthly)
        arr = mrr * 12  # Annual Recurring Revenue
        arpu = mrr / active_subscriptions if active_subscriptions > 0 else 0
        
        return SubscriptionAnalytics(
            total_subscriptions=total_subscriptions,
            active_subscriptions=active_subscriptions,
            subscriptions_by_tier=tier_counts,
            subscriptions_by_status=status_counts,
            monthly_recurring_revenue=Decimal(str(mrr)),
            annual_recurring_revenue=Decimal(str(arr)),
            average_revenue_per_user=Decimal(str(arpu)),
            churn_rate=Decimal('0.05'),  # Mock 5% churn rate
            trial_conversion_rate=Decimal('0.25'),  # Mock 25% trial conversion
            created_at=datetime.utcnow()
        )
    
    def _get_tier_pricing(self, tier: str) -> Dict[str, Any]:
        """Get pricing and features for a subscription tier."""
        pricing = {
            "free": {
                "monthly": Decimal('0'),
                "yearly": Decimal('0'),
                "features": {"api_calls": 100, "properties": 10},
                "usage_limits": {"max_saved": 25}
            },
            "basic": {
                "monthly": Decimal('29.99'),
                "yearly": Decimal('299.99'),
                "features": {"api_calls": 1000, "properties": 100},
                "usage_limits": {"max_saved": 500}
            },
            "pro": {
                "monthly": Decimal('99.99'),
                "yearly": Decimal('999.99'),
                "features": {"api_calls": 10000, "properties": "unlimited"},
                "usage_limits": {"max_saved": "unlimited"}
            }
        }
        
        return pricing.get(tier, pricing["free"])
    
    def _calculate_period_end(self, billing_cycle: str) -> datetime:
        """Calculate the end of billing period."""
        now = datetime.utcnow()
        
        if billing_cycle == "monthly":
            return now + timedelta(days=30)
        elif billing_cycle == "yearly":
            return now + timedelta(days=365)
        else:
            return now + timedelta(days=30)  # Default to monthly
    
    def _to_read(self, subscription: Subscription) -> SubscriptionRead:
        """Convert Subscription model to SubscriptionRead schema."""
        return SubscriptionRead(
            id=subscription.id,
            user_id=subscription.user_id,
            tier=subscription.tier,
            status=subscription.status,
            price_monthly=subscription.price_monthly,
            price_yearly=subscription.price_yearly,
            billing_cycle=subscription.billing_cycle,
            features=subscription.features,
            usage_limits=subscription.usage_limits,
            stripe_customer_id=subscription.stripe_customer_id,
            stripe_subscription_id=subscription.stripe_subscription_id,
            stripe_price_id=subscription.stripe_price_id,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_start=subscription.trial_start,
            trial_end=subscription.trial_end,
            canceled_at=subscription.canceled_at,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at
        )
