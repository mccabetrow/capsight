"""
Subscription database model.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionTier(str):
    """Subscription tier constants."""
    BASIC = "Basic"
    PRO = "Pro"
    ENTERPRISE = "Enterprise"


class SubscriptionStatus(str):
    """Subscription status constants."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"


class Subscription(Base):
    """Subscription database model for user billing."""
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Subscription details
    tier = Column(String(20), nullable=False, default=SubscriptionTier.BASIC)
    status = Column(String(20), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Stripe integration
    stripe_customer_id = Column(String(100), nullable=True, unique=True)
    stripe_subscription_id = Column(String(100), nullable=True, unique=True)
    
    # Billing dates
    renews_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    
    # Trial period
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, tier={self.tier})>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status == SubscriptionStatus.ACTIVE
    
    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period."""
        if not self.trial_start or not self.trial_end:
            return False
        
        now = datetime.utcnow()
        return self.trial_start <= now <= self.trial_end
    
    @property
    def days_until_renewal(self) -> int:
        """Get days until next renewal."""
        if not self.renews_at:
            return 0
        
        delta = self.renews_at - datetime.utcnow()
        return max(0, delta.days)
