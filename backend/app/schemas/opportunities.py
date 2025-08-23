"""
Opportunity-related schemas.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from app.schemas.user import SubscriptionTier


class OpportunityType(str, Enum):
    """Types of arbitrage opportunities."""
    CAP_RATE_COMPRESSION = "cap_rate_compression"
    FINANCING_ADVANTAGE = "financing_advantage"
    MARKET_INEFFICIENCY = "market_inefficiency"
    UNDERVALUED_PROPERTY = "undervalued_property"
    DEVELOPMENT_OPPORTUNITY = "development_opportunity"


class PropertyType(str, Enum):
    """Property types."""
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    COMMERCIAL = "commercial"
    RETAIL = "retail"
    OFFICE = "office"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"


class OpportunityResponse(BaseModel):
    """Arbitrage opportunity response."""
    opportunity_id: str
    property_id: Optional[str] = None
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    
    # Opportunity metrics
    arbitrage_score: float = Field(..., ge=0.0, le=1.0)
    expected_return: float
    risk_score: float = Field(..., ge=0.0, le=1.0)
    confidence_interval: Optional[Tuple[float, float]] = None
    
    # Property details
    property_type: PropertyType
    square_footage: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    year_built: Optional[int] = None
    lot_size: Optional[float] = None
    
    # Financial metrics
    list_price: float
    estimated_value: Optional[float] = None
    price_per_sqft: Optional[float] = None
    current_cap_rate: Optional[float] = None
    projected_cap_rate: Optional[float] = None
    gross_rental_yield: Optional[float] = None
    net_rental_yield: Optional[float] = None
    
    # Opportunity details
    opportunity_type: OpportunityType
    key_factors: List[str]
    investment_thesis: str
    time_sensitivity: str  # low, medium, high, urgent
    
    # Market context
    market_trends: Dict[str, Any]
    comparable_sales: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    discovered_at: datetime
    last_updated: datetime
    expires_at: Optional[datetime] = None
    disclaimer: str
    subscription_tier_required: SubscriptionTier = SubscriptionTier.BASIC
    
    class Config:
        from_attributes = True


class OpportunityFilter(BaseModel):
    """Filter criteria for opportunities."""
    min_score: float = 0.0
    max_score: float = 1.0
    location: Optional[str] = None
    property_type: Optional[PropertyType] = None
    opportunity_type: Optional[OpportunityType] = None
    min_expected_return: Optional[float] = None
    max_risk_score: Optional[float] = None
    price_range: Optional[Tuple[float, float]] = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    time_sensitivity: Optional[List[str]] = None


class OpportunityRanking(BaseModel):
    """Market opportunity rankings."""
    location: str
    time_period: str
    total_opportunities: int
    average_score: float
    top_opportunity_types: List[Dict[str, Any]]
    market_insights: Dict[str, Any]
    trend_analysis: Dict[str, float]
    disclaimer: str
    generated_at: datetime
    
    class Config:
        from_attributes = True


class OpportunityAlert(BaseModel):
    """Opportunity alert configuration."""
    alert_id: str
    user_id: str
    name: str
    filter_criteria: OpportunityFilter
    notification_methods: List[str]  # email, sms, webhook
    is_active: bool = True
    created_at: datetime
    last_triggered: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OpportunityInsight(BaseModel):
    """Detailed opportunity insights."""
    opportunity_id: str
    insights: Dict[str, Any]
    risk_factors: List[str]
    mitigation_strategies: List[str]
    similar_opportunities: List[str]
    market_context: Dict[str, Any]
    generated_at: datetime
    disclaimer: str
    
    class Config:
        from_attributes = True
