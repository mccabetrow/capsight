"""
Opportunities API endpoints.
"""

import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.opportunity import (
    OpportunityCreate, OpportunityRead, OpportunityUpdate, OpportunityQuery,
    OpportunitySummary, OpportunityAnalysis, OpportunityStats
)
from app.services.opportunities import OpportunityService
from app.ml.services import get_inference_service, get_data_service
from app.ml.models import ArbitrageRequest

router = APIRouter()


@router.get("/", response_model=List[OpportunitySummary])
async def get_opportunities(
    query: OpportunityQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get opportunities with optional filtering.
    """
    # Return demo data if in demo mode
    if is_demo_mode():
        demo_properties = demo_generator.generate_demo_properties(30)
        demo_opportunities = demo_generator.generate_demo_opportunities(demo_properties, 15)
        
        # Convert to OpportunitySummary format and apply filters
        opportunities = []
        for opp in demo_opportunities:
            # Apply basic filtering
            if query.opportunity_type and opp["opportunity_type"] != query.opportunity_type:
                continue
            if query.min_confidence and opp["confidence_score"] < query.min_confidence:
                continue
            if query.max_investment and opp["investment_required"] > query.max_investment:
                continue
            if query.risk_level and opp["risk_level"] != query.risk_level:
                continue
                
            opportunities.append(OpportunitySummary(
                id=uuid.UUID(opp["id"]),
                property_id=uuid.UUID(opp["property_id"]),
                opportunity_type=opp["opportunity_type"],
                confidence_score=opp["confidence_score"],
                potential_profit=opp["potential_profit"],
                investment_required=opp["investment_required"],
                risk_level=opp["risk_level"],
                property_address=f"{opp['property']['address']}, {opp['property']['city']}, {opp['property']['state']}",
                created_at=opp["created_at"],
                expires_at=opp["expires_at"]
            ))
        
        # Apply pagination
        start = query.skip
        end = start + query.limit
        return opportunities[start:end]
    
    # Normal database operation
    opportunity_service = OpportunityService(db)
    opportunities = opportunity_service.get_opportunities(query, user_id=current_user.id)
    return opportunities


@router.get("/stats", response_model=OpportunityStats)
async def get_opportunity_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get opportunity statistics for the current user.
    """
    opportunity_service = OpportunityService(db)
    stats = opportunity_service.get_opportunity_stats(user_id=current_user.id)
    return stats


@router.get("/{opportunity_id}", response_model=OpportunityRead)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get a specific opportunity by ID.
    """
    opportunity_service = OpportunityService(db)
    opportunity = opportunity_service.get_opportunity_by_id(
        opportunity_id, user_id=current_user.id
    )
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    return opportunity


@router.get("/{opportunity_id}/analysis", response_model=OpportunityAnalysis)
async def get_opportunity_analysis(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get comprehensive analysis for a specific opportunity.
    """
    opportunity_service = OpportunityService(db)
    analysis = opportunity_service.get_opportunity_analysis(
        opportunity_id, user_id=current_user.id
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity analysis not found"
        )
    return analysis


@router.post("/", response_model=OpportunityRead, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    opportunity_data: OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a new opportunity.
    """
    opportunity_service = OpportunityService(db)
    opportunity = opportunity_service.create_opportunity(
        opportunity_data, user_id=current_user.id
    )
    return opportunity


@router.put("/{opportunity_id}", response_model=OpportunityRead)
async def update_opportunity(
    opportunity_id: uuid.UUID,
    opportunity_data: OpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update an existing opportunity.
    """
    opportunity_service = OpportunityService(db)
    opportunity = opportunity_service.update_opportunity(
        opportunity_id, opportunity_data, user_id=current_user.id
    )
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    return opportunity


@router.delete("/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete an opportunity.
    """
    opportunity_service = OpportunityService(db)
    success = opportunity_service.delete_opportunity(
        opportunity_id, user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    return {"message": "Opportunity deleted successfully"}


@router.post("/property/{property_id}/generate", response_model=OpportunityRead)
async def generate_opportunity_for_property(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate an opportunity analysis for a specific property.
    """
    opportunity_service = OpportunityService(db)
    opportunity = opportunity_service.generate_opportunity_for_property(
        property_id, user_id=current_user.id
    )
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to generate opportunity for this property"
        )
    return opportunity


@router.get("/property/{property_id}", response_model=List[OpportunitySummary])
async def get_opportunities_for_property(
    property_id: uuid.UUID,
    active_only: bool = Query(True, description="Return only active opportunities"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get all opportunities for a specific property.
    """
    opportunity_service = OpportunityService(db)
    opportunities = opportunity_service.get_opportunities_for_property(
        property_id, user_id=current_user.id, active_only=active_only
    )
    return opportunities


@router.post("/{opportunity_id}/deactivate")
async def deactivate_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Deactivate an opportunity (mark as inactive).
    """
    opportunity_service = OpportunityService(db)
    success = opportunity_service.deactivate_opportunity(
        opportunity_id, user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    return {"message": "Opportunity deactivated successfully"}


@router.post("/{opportunity_id}/reactivate")
async def reactivate_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Reactivate an opportunity (mark as active).
    """
    opportunity_service = OpportunityService(db)
    success = opportunity_service.reactivate_opportunity(
        opportunity_id, user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    return {"message": "Opportunity reactivated successfully"}


@router.post("/ml/discover", response_model=List[OpportunitySummary])
async def discover_ml_opportunities(
    property_ids: Optional[List[str]] = Query(None, description="Specific property IDs to analyze"),
    min_score: float = Query(70.0, description="Minimum arbitrage score"),
    max_results: int = Query(20, description="Maximum number of results"),
    hold_period_months: int = Query(60, description="Investment hold period in months"),
    risk_tolerance: str = Query("moderate", description="Risk tolerance: conservative, moderate, aggressive"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Discover arbitrage opportunities using ML pipeline.
    
    **Legal Disclaimer**: For informational purposes only. Not investment advice.
    CapSight does not guarantee outcomes.
    """
    try:
        # Get ML services
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # If no property IDs provided, get all available properties
        if not property_ids:
            # Load recent properties from database
            property_data = await data_service.load_property_data(limit=100)
            property_ids = list(set(p.property_id for p in property_data))
        
        # Create arbitrage request
        ml_request = ArbitrageRequest(
            property_ids=property_ids,
            hold_period_months=hold_period_months,
            min_expected_return=0.1,
            risk_tolerance=risk_tolerance
        )
        
        # Score arbitrage opportunities
        scores = await inference_service.score_arbitrage_opportunity(ml_request)
        
        # Filter by minimum score
        filtered_scores = [s for s in scores if s.score >= min_score]
        
        # Sort by score (highest first) and limit results
        filtered_scores.sort(key=lambda x: x.score, reverse=True)
        filtered_scores = filtered_scores[:max_results]
        
        # Convert to opportunity summaries
        opportunities = []
        for score in filtered_scores:
            # Get property details (would be from property service)
            opportunity = OpportunitySummary(
                id=uuid.uuid4(),  # Generated ID
                property_id=uuid.UUID(score.property_id) if score.property_id else uuid.uuid4(),
                opportunity_type="arbitrage",
                confidence_score=score.confidence,
                potential_profit=score.expected_return * 100000 if score.expected_return else None,  # Example calc
                investment_required=100000,  # Example value
                risk_level="low" if score.score > 80 else "medium" if score.score > 60 else "high",
                property_address=f"Property {score.property_id}",  # Would fetch real address
                created_at=score.created_at,
                expires_at=None
            )
            opportunities.append(opportunity)
        
        # Save discovered opportunities to database
        for score in filtered_scores:
            await data_service.save_arbitrage_score(score)
        
        return opportunities
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML opportunity discovery failed: {str(e)}"
        )


@router.get("/ml/scores/{property_id}")
async def get_ml_arbitrage_scores(
    property_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get ML-generated arbitrage scores for a specific property.
    """
    try:
        data_service = get_data_service(db)
        
        # Load arbitrage scores for the property
        scores = await data_service.load_arbitrage_scores(property_id=property_id)
        
        if not scores:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No arbitrage scores found for this property"
            )
        
        # Convert to response format
        response = {
            "property_id": property_id,
            "scores": [
                {
                    "score": score.score,
                    "confidence": score.confidence,
                    "expected_return": score.expected_return,
                    "risk_score": score.risk_score,
                    "factors": score.factors,
                    "hold_period_months": score.hold_period_months,
                    "created_at": score.created_at.isoformat() if score.created_at else None
                }
                for score in scores
            ],
            "latest_score": max(scores, key=lambda x: x.created_at).score if scores else None
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get arbitrage scores: {str(e)}"
        )


@router.post("/ml/refresh")
async def refresh_ml_opportunities(
    force_retrain: bool = Query(False, description="Force model retraining"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Refresh ML opportunities by rerunning scoring pipeline.
    """
    try:
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # If force retrain, retrain models first
        if force_retrain:
            await inference_service.retrain_model("ensemble")
        
        # Get all properties
        property_data = await data_service.load_property_data(limit=200)
        property_ids = list(set(p.property_id for p in property_data))
        
        # Run batch scoring
        ml_request = ArbitrageRequest(
            property_ids=property_ids,
            hold_period_months=60,
            risk_tolerance="moderate"
        )
        
        scores = await inference_service.score_arbitrage_opportunity(ml_request)
        
        # Save all scores
        saved_count = 0
        for score in scores:
            await data_service.save_arbitrage_score(score)
            saved_count += 1
        
        return {
            "message": "ML opportunities refreshed successfully",
            "processed_properties": len(property_ids),
            "generated_scores": len(scores),
            "saved_scores": saved_count,
            "retrained_models": force_retrain
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh ML opportunities: {str(e)}"
        )
