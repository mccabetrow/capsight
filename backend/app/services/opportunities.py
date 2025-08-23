"""
Opportunity service for managing arbitrage opportunities.
"""

import uuid
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.models.opportunity import Opportunity
from app.models.property import Property
from app.schemas.opportunity import (
    OpportunityCreate, OpportunityRead, OpportunityUpdate, OpportunityQuery,
    OpportunitySummary, OpportunityAnalysis, OpportunityStats
)


class OpportunityService:
    """Service for managing arbitrage opportunities."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_opportunities(
        self, 
        query: OpportunityQuery, 
        user_id: Optional[uuid.UUID] = None
    ) -> List[OpportunitySummary]:
        """Get opportunities with filtering."""
        db_query = self.db.query(Opportunity)
        
        # Apply filters
        if query.property_id:
            db_query = db_query.filter(Opportunity.property_id == query.property_id)
        
        if query.opportunity_type:
            db_query = db_query.filter(Opportunity.opportunity_type == query.opportunity_type)
        
        if query.min_arbitrage_score is not None:
            db_query = db_query.filter(Opportunity.arbitrage_score >= query.min_arbitrage_score)
        
        if query.max_arbitrage_score is not None:
            db_query = db_query.filter(Opportunity.arbitrage_score <= query.max_arbitrage_score)
        
        if query.min_potential_profit is not None:
            db_query = db_query.filter(Opportunity.potential_profit >= query.min_potential_profit)
        
        if query.min_profit_margin is not None:
            db_query = db_query.filter(Opportunity.profit_margin >= query.min_profit_margin)
        
        if query.risk_level:
            db_query = db_query.filter(Opportunity.risk_level == query.risk_level)
        
        if query.is_active is not None:
            db_query = db_query.filter(Opportunity.is_active == query.is_active)
        
        if query.max_investment is not None:
            db_query = db_query.filter(Opportunity.investment_required <= query.max_investment)
        
        if query.max_time_to_profit is not None:
            db_query = db_query.filter(Opportunity.time_to_profit_months <= query.max_time_to_profit)
        
        # Order by arbitrage score (highest first)
        db_query = db_query.order_by(desc(Opportunity.arbitrage_score))
        
        # Apply pagination
        opportunities = db_query.offset(query.skip).limit(query.limit).all()
        
        return [self._to_summary(opp) for opp in opportunities]
    
    def get_opportunity_by_id(
        self, 
        opportunity_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[OpportunityRead]:
        """Get opportunity by ID."""
        opportunity = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if opportunity:
            return self._to_read(opportunity)
        return None
    
    def create_opportunity(
        self, 
        opportunity_data: OpportunityCreate, 
        user_id: Optional[uuid.UUID] = None
    ) -> OpportunityRead:
        """Create a new opportunity."""
        db_opportunity = Opportunity(
            property_id=opportunity_data.property_id,
            opportunity_type=opportunity_data.opportunity_type,
            arbitrage_score=opportunity_data.arbitrage_score,
            potential_profit=opportunity_data.potential_profit,
            profit_margin=opportunity_data.profit_margin,
            investment_required=opportunity_data.investment_required,
            time_to_profit_months=opportunity_data.time_to_profit_months,
            risk_level=opportunity_data.risk_level,
            risk_factors=opportunity_data.risk_factors,
            opportunity_window_days=opportunity_data.opportunity_window_days,
            rationale=opportunity_data.rationale,
            key_metrics=opportunity_data.key_metrics,
            market_conditions=opportunity_data.market_conditions,
            recommended_actions=opportunity_data.recommended_actions,
            is_active=opportunity_data.is_active
        )
        
        self.db.add(db_opportunity)
        self.db.commit()
        self.db.refresh(db_opportunity)
        
        return self._to_read(db_opportunity)
    
    def update_opportunity(
        self, 
        opportunity_id: uuid.UUID, 
        opportunity_data: OpportunityUpdate, 
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[OpportunityRead]:
        """Update an existing opportunity."""
        opportunity = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opportunity:
            return None
        
        # Update fields
        update_data = opportunity_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(opportunity, field, value)
        
        opportunity.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(opportunity)
        
        return self._to_read(opportunity)
    
    def delete_opportunity(
        self, 
        opportunity_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete an opportunity."""
        opportunity = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if opportunity:
            self.db.delete(opportunity)
            self.db.commit()
            return True
        return False
    
    def get_opportunity_stats(self, user_id: Optional[uuid.UUID] = None) -> OpportunityStats:
        """Get opportunity statistics."""
        total_opportunities = self.db.query(Opportunity).count()
        active_opportunities = self.db.query(Opportunity).filter(Opportunity.is_active == True).count()
        
        avg_score = self.db.query(Opportunity.arbitrage_score).filter(
            Opportunity.is_active == True
        ).all()
        avg_arbitrage_score = sum(score[0] for score in avg_score) / len(avg_score) if avg_score else Decimal('0')
        
        total_profit = self.db.query(Opportunity.potential_profit).filter(
            Opportunity.is_active == True
        ).all()
        total_potential_profit = sum(profit[0] for profit in total_profit)
        
        # Opportunities by type
        type_counts = {}
        types = self.db.query(Opportunity.opportunity_type, self.db.func.count(Opportunity.id)).group_by(Opportunity.opportunity_type).all()
        for opp_type, count in types:
            type_counts[opp_type] = count
        
        # Opportunities by risk
        risk_counts = {}
        risks = self.db.query(Opportunity.risk_level, self.db.func.count(Opportunity.id)).group_by(Opportunity.risk_level).all()
        for risk_level, count in risks:
            risk_counts[risk_level] = count
        
        # Top opportunities
        top_opps = self.db.query(Opportunity).filter(
            Opportunity.is_active == True
        ).order_by(desc(Opportunity.arbitrage_score)).limit(5).all()
        
        return OpportunityStats(
            total_opportunities=total_opportunities,
            active_opportunities=active_opportunities,
            avg_arbitrage_score=avg_arbitrage_score,
            total_potential_profit=total_potential_profit,
            opportunities_by_type=type_counts,
            opportunities_by_risk=risk_counts,
            top_opportunities=[self._to_summary(opp) for opp in top_opps]
        )
    
    def get_opportunity_analysis(
        self, 
        opportunity_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[OpportunityAnalysis]:
        """Get comprehensive opportunity analysis."""
        opportunity = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opportunity:
            return None
        
        # Get associated property
        property_details = self.db.query(Property).filter(Property.id == opportunity.property_id).first()
        
        # Create analysis
        analysis = OpportunityAnalysis(
            opportunity=self._to_read(opportunity),
            property_details=self._property_to_dict(property_details) if property_details else {},
            market_analysis=opportunity.market_conditions or {},
            financial_projections=opportunity.key_metrics or {},
            risk_assessment={"risk_level": opportunity.risk_level, "factors": opportunity.risk_factors or []},
            comparable_properties=[],  # Would be populated with actual data
            recommendation={
                "actions": opportunity.recommended_actions or [],
                "rationale": opportunity.rationale
            }
        )
        
        return analysis
    
    def generate_opportunity_for_property(
        self, 
        property_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[OpportunityRead]:
        """Generate an opportunity analysis for a property."""
        property_obj = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return None
        
        # Mock opportunity generation (would use ML models in production)
        opportunity_data = OpportunityCreate(
            property_id=property_id,
            opportunity_type="arbitrage",
            arbitrage_score=Decimal('75.5'),
            potential_profit=Decimal('50000'),
            profit_margin=Decimal('0.15'),
            investment_required=property_obj.list_price,
            time_to_profit_months=12,
            risk_level="medium",
            risk_factors=["Market volatility", "Interest rate changes"],
            opportunity_window_days=30,
            rationale="Property is undervalued based on comparable sales",
            key_metrics={
                "cap_rate": "8.5%",
                "roi": "15.2%",
                "cash_on_cash": "12.8%"
            },
            market_conditions={
                "median_price": float(property_obj.estimated_value or 0),
                "days_on_market": 45,
                "inventory_level": "low"
            },
            recommended_actions=[
                "Schedule property inspection",
                "Obtain financing pre-approval",
                "Submit offer within 7 days"
            ]
        )
        
        return self.create_opportunity(opportunity_data, user_id)
    
    def get_opportunities_for_property(
        self, 
        property_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None,
        active_only: bool = True
    ) -> List[OpportunitySummary]:
        """Get all opportunities for a specific property."""
        query = self.db.query(Opportunity).filter(Opportunity.property_id == property_id)
        
        if active_only:
            query = query.filter(Opportunity.is_active == True)
        
        opportunities = query.order_by(desc(Opportunity.arbitrage_score)).all()
        return [self._to_summary(opp) for opp in opportunities]
    
    def deactivate_opportunity(
        self, 
        opportunity_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Deactivate an opportunity."""
        opportunity = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if opportunity:
            opportunity.is_active = False
            opportunity.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def reactivate_opportunity(
        self, 
        opportunity_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Reactivate an opportunity."""
        opportunity = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if opportunity:
            opportunity.is_active = True
            opportunity.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def _to_read(self, opportunity: Opportunity) -> OpportunityRead:
        """Convert Opportunity model to OpportunityRead schema."""
        return OpportunityRead(
            id=opportunity.id,
            property_id=opportunity.property_id,
            opportunity_type=opportunity.opportunity_type,
            arbitrage_score=opportunity.arbitrage_score,
            potential_profit=opportunity.potential_profit,
            profit_margin=opportunity.profit_margin,
            investment_required=opportunity.investment_required,
            time_to_profit_months=opportunity.time_to_profit_months,
            risk_level=opportunity.risk_level,
            risk_factors=opportunity.risk_factors,
            opportunity_window_days=opportunity.opportunity_window_days,
            rationale=opportunity.rationale,
            key_metrics=opportunity.key_metrics,
            market_conditions=opportunity.market_conditions,
            recommended_actions=opportunity.recommended_actions,
            is_active=opportunity.is_active,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at
        )
    
    def _to_summary(self, opportunity: Opportunity) -> OpportunitySummary:
        """Convert Opportunity model to OpportunitySummary schema."""
        return OpportunitySummary(
            id=opportunity.id,
            property_id=opportunity.property_id,
            opportunity_type=opportunity.opportunity_type,
            arbitrage_score=opportunity.arbitrage_score,
            potential_profit=opportunity.potential_profit,
            profit_margin=opportunity.profit_margin,
            investment_required=opportunity.investment_required,
            risk_level=opportunity.risk_level,
            time_to_profit_months=opportunity.time_to_profit_months,
            is_active=opportunity.is_active,
            created_at=opportunity.created_at
        )
    
    def _property_to_dict(self, property_obj: Property) -> Dict[str, Any]:
        """Convert Property model to dictionary."""
        return {
            "id": str(property_obj.id),
            "title": property_obj.title,
            "address": property_obj.address,
            "city": property_obj.city,
            "state": property_obj.state,
            "property_type": property_obj.property_type,
            "list_price": float(property_obj.list_price),
            "estimated_value": float(property_obj.estimated_value) if property_obj.estimated_value else None,
            "bedrooms": property_obj.bedrooms,
            "bathrooms": float(property_obj.bathrooms) if property_obj.bathrooms else None,
            "square_feet": property_obj.square_feet
        }
