"""
Property database model.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.forecast import Forecast
    from app.models.opportunity import Opportunity


class PropertyType(str):
    """Property type constants."""
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    COMMERCIAL = "commercial"
    RETAIL = "retail"
    OFFICE = "office"
    INDUSTRIAL = "industrial"


class Property(Base):
    """Property database model."""
    __tablename__ = "properties"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Location
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    zip_code = Column(String(20), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)  # lat
    longitude = Column(Numeric(11, 8), nullable=True)  # lon
    
    # Property details
    property_type = Column(String(50), nullable=False, index=True)
    units = Column(Integer, nullable=True)  # Number of units (for multi-family)
    square_feet = Column(Integer, nullable=True)  # sqft
    
    # Financial metrics
    current_rent = Column(Numeric(12, 2), nullable=True)  # Monthly rent
    net_operating_income = Column(Numeric(15, 2), nullable=True)  # NOI
    cap_rate = Column(Numeric(5, 4), nullable=True)  # Current cap rate
    
    # Data source and quality
    source = Column(String(50), nullable=False)  # zillow, redfin, manual, etc.
    source_id = Column(String(100), nullable=True)  # External ID from source
    data_quality_score = Column(Numeric(3, 2), nullable=True)  # 0.0 to 1.0
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    forecasts = relationship("Forecast", back_populates="property")
    opportunities = relationship("Opportunity", back_populates="property")
    
    def __repr__(self) -> str:
        return f"<Property(id={self.id}, address='{self.address}')>"
    
    @property
    def price_per_sqft(self) -> Decimal:
        """Calculate price per square foot if possible."""
        if self.current_rent and self.square_feet and self.square_feet > 0:
            monthly_psf = self.current_rent / self.square_feet
            return monthly_psf * 12  # Annual
        return Decimal('0')
    
    @property
    def location_display(self) -> str:
        """Get formatted location display."""
        return f"{self.city}, {self.state} {self.zip_code or ''}".strip()
