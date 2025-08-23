"""
Forecasts API endpoints.
ML-powered forecasting for cap rates, NOI, rent, and market trends.
"""

from typing import Any, List, Dict, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.services.auth import AuthService
from app.schemas.user import User
from app.ml.services import get_inference_service, get_data_service
from app.ml.models import ForecastRequest, BatchPredictRequest, ForecastType, ModelType

router = APIRouter()


@router.post("/run")
async def run_forecast(
    property_id: Optional[str] = None,
    forecast_type: ForecastType = ForecastType.CAP_RATE,
    horizon_months: int = 12,
    model_type: ModelType = ModelType.PROPHET,
    include_confidence: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Run a single forecast for a property or market segment.
    
    **Legal Disclaimer**: For informational purposes only. Not investment advice.
    CapSight does not guarantee outcomes.
    """
    try:
        # Get ML services
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # Create forecast request
        ml_request = ForecastRequest(
            property_id=property_id,
            forecast_type=forecast_type,
            horizon_months=horizon_months,
            model_type=model_type,
            include_confidence=include_confidence
        )
        
        # Generate forecast
        forecast_result = await inference_service.generate_forecast(ml_request)
        
        # Save to database
        forecast_id = await data_service.save_forecast(forecast_result)
        
        # Return forecast with API response format
        response = {
            "forecast_id": forecast_id,
            "property_id": forecast_result.property_id,
            "forecast_type": forecast_result.forecast_type,
            "model_type": forecast_result.model_type,
            "horizon_months": horizon_months,
            "predictions": [
                {
                    "date": pred.date.isoformat(),
                    "value": pred.value,
                    "lower_bound": pred.lower_bound,
                    "upper_bound": pred.upper_bound,
                    "confidence": pred.confidence
                }
                for pred in forecast_result.predictions
            ],
            "metrics": forecast_result.metrics,
            "metadata": forecast_result.metadata,
            "created_at": forecast_result.created_at.isoformat(),
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast failed: {str(e)}"
        )


@router.post("/batch")
async def batch_forecast(
    property_ids: List[str],
    forecast_types: List[ForecastType] = [ForecastType.CAP_RATE, ForecastType.NOI, ForecastType.RENT],
    horizon_months: int = 12,
    model_type: ModelType = ModelType.PROPHET,
    include_scoring: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Run batch forecasts across multiple properties.
    
    **Legal Disclaimer**: For informational purposes only. Not investment advice.
    """
    try:
        # Get ML services
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # Convert property IDs to property data format
        properties = [{"property_id": pid} for pid in property_ids]
        
        # Create batch request
        ml_request = BatchPredictRequest(
            properties=properties,
            forecast_types=[ft.value for ft in forecast_types],
            horizon_months=horizon_months,
            include_scoring=include_scoring
        )
        
        # Run batch prediction
        results = await inference_service.batch_predict(ml_request)
        
        # Save forecasts to database
        saved_forecasts = {}
        for property_id, forecasts in results['forecasts'].items():
            saved_forecasts[property_id] = {}
            for forecast_type, forecast_result in forecasts.items():
                forecast_id = await data_service.save_forecast(forecast_result)
                saved_forecasts[property_id][forecast_type] = forecast_id
        
        # Save arbitrage scores if generated
        saved_scores = []
        for score in results.get('scores', []):
            score_id = await data_service.save_arbitrage_score(score)
            saved_scores.append(score_id)
        
        # Return batch results
        response = {
            "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "processed_properties": len(property_ids),
            "forecast_types": [ft.value for ft in forecast_types],
            "saved_forecasts": saved_forecasts,
            "saved_scores": saved_scores,
            "summary": results['summary'],
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch forecast failed: {str(e)}"
        )


@router.get("/history/{property_id}")
async def get_forecast_history(
    property_id: str,
    forecast_type: Optional[ForecastType] = None,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Get historical forecasts for a property.
    """
    try:
        data_service = get_data_service(db)
        
        # Load forecasts from database
        forecasts = await data_service.load_forecasts(
            property_id=property_id,
            forecast_type=forecast_type.value if forecast_type else None,
            limit=limit
        )
        
        if not forecasts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No forecasts found for this property"
            )
        
        # Convert to response format
        response = {
            "property_id": property_id,
            "forecast_type": forecast_type.value if forecast_type else "all",
            "total_forecasts": len(forecasts),
            "forecasts": [
                {
                    "forecast_type": f.forecast_type,
                    "model_type": f.model_type,
                    "prediction_count": len(f.predictions),
                    "metrics": f.metrics,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "predictions": [
                        {
                            "date": pred.date.isoformat(),
                            "value": pred.value,
                            "confidence": pred.confidence
                        }
                        for pred in f.predictions[:5]  # Only return first 5 predictions
                    ]
                }
                for f in forecasts
            ]
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get forecast history: {str(e)}"
        )


@router.get("/trends/market")
async def get_market_trends(
    forecast_type: ForecastType = ForecastType.CAP_RATE,
    region: Optional[str] = None,
    property_type: Optional[str] = None,
    horizon_months: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Get market-wide forecast trends.
    """
    try:
        # Get ML services
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # Load market data (aggregated across properties)
        property_data = await data_service.load_property_data(limit=50)
        
        if not property_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No market data available"
            )
        
        # Get unique property IDs
        property_ids = list(set(p.property_id for p in property_data))[:10]  # Sample
        
        # Run market-level forecast
        properties = [{"property_id": pid} for pid in property_ids]
        ml_request = BatchPredictRequest(
            properties=properties,
            forecast_types=[forecast_type.value],
            horizon_months=horizon_months,
            include_scoring=False
        )
        
        results = await inference_service.batch_predict(ml_request)
        
        # Aggregate forecasts for market trends
        all_predictions = []
        for property_id, forecasts in results['forecasts'].items():
            if forecast_type.value in forecasts:
                forecast_result = forecasts[forecast_type.value]
                all_predictions.extend([
                    {"date": pred.date, "value": pred.value} 
                    for pred in forecast_result.predictions
                ])
        
        # Calculate market averages by date
        from collections import defaultdict
        date_values = defaultdict(list)
        for pred in all_predictions:
            date_values[pred["date"]].append(pred["value"])
        
        market_trends = []
        for date, values in sorted(date_values.items()):
            avg_value = sum(values) / len(values)
            market_trends.append({
                "date": date.isoformat(),
                "market_average": avg_value,
                "property_count": len(values),
                "min_value": min(values),
                "max_value": max(values)
            })
        
        response = {
            "forecast_type": forecast_type.value,
            "region": region or "all",
            "property_type": property_type or "all", 
            "horizon_months": horizon_months,
            "sample_properties": len(property_ids),
            "trends": market_trends,
            "summary": {
                "trend_direction": "up" if len(market_trends) >= 2 and market_trends[-1]["market_average"] > market_trends[0]["market_average"] else "down",
                "volatility": max(t["max_value"] - t["min_value"] for t in market_trends) if market_trends else 0
            },
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market trends: {str(e)}"
        )


@router.get("/models/performance")
async def get_model_performance(
    model_name: Optional[str] = None,
    forecast_type: Optional[ForecastType] = None,
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Get model performance metrics and statistics.
    """
    try:
        inference_service = get_inference_service()
        
        # Get model status and performance
        model_status = await inference_service.get_model_status(model_name)
        
        # Format response
        if model_name:
            # Single model performance
            if model_name not in model_status:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model '{model_name}' not found"
                )
            
            model_info = model_status[model_name]
            response = {
                "model_name": model_name,
                "performance": model_info,
                "forecast_types": forecast_type.value if forecast_type else "all"
            }
        else:
            # All models performance
            response = {
                "models": model_status,
                "total_models": len(model_status)
            }
        
        response["disclaimer"] = settings.LEGAL_DISCLAIMER
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model performance: {str(e)}"
        )


@router.post("/models/{model_name}/backtest")
async def run_model_backtest(
    model_name: str,
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Run backtest for a specific forecasting model.
    """
    try:
        inference_service = get_inference_service()
        
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        if (end_date - start_date).days > 365 * 2:  # Max 2 years
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 2 years"
            )
        
        # Run backtest
        result = await inference_service.run_backtest(
            model_name=model_name,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "backtest_results": result,
            "model_name": model_name,
            "test_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_days": (end_date - start_date).days
            },
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {str(e)}"
        )
