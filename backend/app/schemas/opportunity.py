"""
Opportunity schemas for request/response validation.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, ConfigDict


class OpportunityBase(BaseModel):
    """Base opportunity schema with common fields."""
    property_id: uuid.UUID = Field(..., description="Associated property ID")
    opportunity_type: str = Field(default="arbitrage", max_length=50, description="Type of opportunity")
    arbitrage_score: Decimal = Field(..., ge=0, le=100, description="Arbitrage opportunity score (0-100)")
    potential_profit: Decimal = Field(..., description="Estimated potential profit")
    profit_margin: Decimal = Field(..., ge=0, le=1, description="Profit margin percentage (0-1)")
    investment_required: Decimal = Field(..., gt=0, description="Total investment required")
    time_to_profit_months: Optional[int] = Field(None, ge=1, description="Expected time to realize profit")
    risk_level: str = Field(default="medium", max_length=20, description="Risk assessment level")
    risk_factors: Optional[List[str]] = Field(None, description="Identified risk factors")
    opportunity_window_days: Optional[int] = Field(None, ge=1, description="Opportunity window in days")
    rationale: Optional[str] = Field(None, description="Detailed rationale for the opportunity")
    key_metrics: Optional[Dict[str, Any]] = Field(None, description="Key financial metrics")
    market_conditions: Optional[Dict[str, Any]] = Field(None, description="Relevant market conditions")
    recommended_actions: Optional[List[str]] = Field(None, description="Recommended next steps")
    is_active: bool = Field(default=True, description="Whether opportunity is still active")


class OpportunityCreate(OpportunityBase):
    """Opportunity creation schema."""
    pass


class OpportunityRead(OpportunityBase):
    """Opportunity read schema for API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Opportunity ID")
    created_at: datetime = Field(..., description="Opportunity creation timestamp")
    updated_at: datetime = Field(..., description="Opportunity last update timestamp")


class OpportunityUpdate(BaseModel):
    """Opportunity update schema."""
    opportunity_type: Optional[str] = Field(None, max_length=50, description="Type of opportunity")
    arbitrage_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Arbitrage opportunity score (0-100)")
    potential_profit: Optional[Decimal] = Field(None, description="Estimated potential profit")
    profit_margin: Optional[Decimal] = Field(None, ge=0, le=1, description="Profit margin percentage (0-1)")
    investment_required: Optional[Decimal] = Field(None, gt=0, description="Total investment required")
    time_to_profit_months: Optional[int] = Field(None, ge=1, description="Expected time to realize profit")
    risk_level: Optional[str] = Field(None, max_length=20, description="Risk assessment level")
    risk_factors: Optional[List[str]] = Field(None, description="Identified risk factors")
    opportunity_window_days: Optional[int] = Field(None, ge=1, description="Opportunity window in days")
    rationale: Optional[str] = Field(None, description="Detailed rationale for the opportunity")
    key_metrics: Optional[Dict[str, Any]] = Field(None, description="Key financial metrics")
    market_conditions: Optional[Dict[str, Any]] = Field(None, description="Relevant market conditions")
    recommended_actions: Optional[List[str]] = Field(None, description="Recommended next steps")
    is_active: Optional[bool] = Field(None, description="Whether opportunity is still active")


class OpportunityInDB(OpportunityBase):
    """Opportunity schema for database operations."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class OpportunitySummary(BaseModel):
    """Opportunity summary schema for list views."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Opportunity ID")
    property_id: uuid.UUID = Field(..., description="Associated property ID")
    opportunity_type: str = Field(..., description="Type of opportunity")
    arbitrage_score: Decimal = Field(..., description="Arbitrage opportunity score (0-100)")
    potential_profit: Decimal = Field(..., description="Estimated potential profit")
    profit_margin: Decimal = Field(..., description="Profit margin percentage (0-1)")
    investment_required: Decimal = Field(..., description="Total investment required")
    risk_level: str = Field(..., description="Risk assessment level")
    time_to_profit_months: Optional[int] = Field(None, description="Expected time to realize profit")
    is_active: bool = Field(..., description="Whether opportunity is still active")
    created_at: datetime = Field(..., description="Opportunity creation timestamp")


class OpportunityQuery(BaseModel):
    """Opportunity query schema for filtering."""
    property_id: Optional[uuid.UUID] = Field(None, description="Filter by property ID")
    opportunity_type: Optional[str] = Field(None, description="Filter by opportunity type")
    min_arbitrage_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Minimum arbitrage score")
    max_arbitrage_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Maximum arbitrage score")
    min_potential_profit: Optional[Decimal] = Field(None, description="Minimum potential profit")
    min_profit_margin: Optional[Decimal] = Field(None, ge=0, le=1, description="Minimum profit margin")
    risk_level: Optional[str] = Field(None, description="Filter by risk level")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    max_investment: Optional[Decimal] = Field(None, gt=0, description="Maximum investment required")
    max_time_to_profit: Optional[int] = Field(None, ge=1, description="Maximum time to profit")
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=10, ge=1, le=100, description="Number of records to return")


class OpportunityAnalysis(BaseModel):
    """Comprehensive opportunity analysis schema."""
    model_config = ConfigDict(from_attributes=True)
    
    opportunity: OpportunityRead = Field(..., description="Opportunity details")
    property_details: Dict[str, Any] = Field(..., description="Associated property information")
    market_analysis: Dict[str, Any] = Field(..., description="Market analysis data")
    financial_projections: Dict[str, Any] = Field(..., description="Financial projections")
    risk_assessment: Dict[str, Any] = Field(..., description="Detailed risk assessment")
    comparable_properties: Optional[List[Dict[str, Any]]] = Field(None, description="Comparable properties data")
    recommendation: Dict[str, Any] = Field(..., description="Investment recommendation")


class OpportunityAlert(BaseModel):
    """Opportunity alert schema for notifications."""
    id: uuid.UUID = Field(..., description="Alert ID")
    user_id: uuid.UUID = Field(..., description="User ID to notify")
    opportunity_id: uuid.UUID = Field(..., description="Opportunity ID")
    alert_type: str = Field(..., description="Type of alert")
    message: str = Field(..., description="Alert message")
    urgency: str = Field(default="medium", description="Alert urgency level")
    is_read: bool = Field(default=False, description="Whether alert has been read")
    created_at: datetime = Field(..., description="Alert creation timestamp")


class OpportunityStats(BaseModel):
    """Opportunity statistics schema."""
    total_opportunities: int = Field(..., description="Total number of opportunities")
    active_opportunities: int = Field(..., description="Number of active opportunities")
    avg_arbitrage_score: Decimal = Field(..., description="Average arbitrage score")
    total_potential_profit: Decimal = Field(..., description="Sum of all potential profits")
    opportunities_by_type: Dict[str, int] = Field(..., description="Count by opportunity type")
    opportunities_by_risk: Dict[str, int] = Field(..., description="Count by risk level")
    top_opportunities: List[OpportunitySummary] = Field(..., description="Top opportunities by score")
