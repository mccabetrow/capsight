"""
Forecast database model.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.property import Property


class Forecast(Base):
    """Forecast database model for property predictions."""
    __tablename__ = "forecasts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True)
    
    # Forecast parameters
    horizon_months = Column(Integer, nullable=False)  # Forecast horizon in months
    
    # Predictions
    cap_rate_pred = Column(Numeric(5, 4), nullable=True)  # Predicted cap rate
    rate_pred = Column(Numeric(5, 4), nullable=True)  # Predicted interest rate
    rent_growth_pred = Column(Numeric(5, 4), nullable=True)  # Predicted rent growth rate
    
    # Model confidence and metadata
    confidence = Column(Numeric(3, 2), nullable=False)  # 0.0 to 1.0
    model_version = Column(String(50), nullable=True)  # Model version used
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)  # When this forecast expires
    
    # Relationships
    property = relationship("Property", back_populates="forecasts")
    
    def __repr__(self) -> str:
        return f"<Forecast(id={self.id}, property_id={self.property_id}, horizon={self.horizon_months}m)>"
    
    @property
    def is_expired(self) -> bool:
        """Check if forecast has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def confidence_display(self) -> str:
        """Get human-readable confidence level."""
        if self.confidence >= 0.8:
            return "High"
        elif self.confidence >= 0.6:
            return "Medium"
        else:
            return "Low"
