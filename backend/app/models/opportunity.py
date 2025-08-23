"""
Opportunity database model.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.property import Property


class Opportunity(Base):
    """Opportunity database model for arbitrage opportunities."""
    __tablename__ = "opportunities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True)
    
    # Opportunity scoring
    arbitrage_score = Column(Numeric(5, 4), nullable=False, index=True)  # 0.0 to 1.0
    
    # Analysis
    rationale = Column(Text, nullable=True)  # Why this is an opportunity
    key_factors = Column(String(1000), nullable=True)  # JSON string of key factors
    
    # Time window
    window_start = Column(DateTime, nullable=True)  # Opportunity window start
    window_end = Column(DateTime, nullable=True)  # Opportunity window end
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    property = relationship("Property", back_populates="opportunities")
    
    def __repr__(self) -> str:
        return f"<Opportunity(id={self.id}, property_id={self.property_id}, score={self.arbitrage_score})>"
    
    @property
    def score_grade(self) -> str:
        """Get letter grade for arbitrage score."""
        if self.arbitrage_score >= 0.8:
            return "A"
        elif self.arbitrage_score >= 0.7:
            return "B"
        elif self.arbitrage_score >= 0.6:
            return "C"
        elif self.arbitrage_score >= 0.5:
            return "D"
        else:
            return "F"
    
    @property
    def is_active(self) -> bool:
        """Check if opportunity is currently active."""
        now = datetime.utcnow()
        
        if self.window_start and now < self.window_start:
            return False
        
        if self.window_end and now > self.window_end:
            return False
        
        return True
