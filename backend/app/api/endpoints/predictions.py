"""
Predictions endpoint for AI/ML model predictions and forecasting.
"""

from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.services.auth import AuthService
from app.services.predictions import PredictionService
from app.schemas.user import User
from app.schemas.predictions import PredictionRequest, PredictionResponse, ForecastRequest, ForecastResponse
from app.ml.services import get_inference_service, get_data_service
from app.ml.models import ForecastRequest as MLForecastRequest, ArbitrageRequest, BatchPredictRequest

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_arbitrage(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Generate arbitrage predictions for given property/market data.
    
    **Legal Disclaimer**: For informational purposes only. Not investment advice. 
    CapSight does not guarantee outcomes.
    """
    try:
        # Get ML services
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # Create arbitrage request
        ml_request = ArbitrageRequest(
            property_ids=request.property_ids,
            hold_period_months=getattr(request, 'hold_period_months', 60),
            min_expected_return=getattr(request, 'min_expected_return', 0.1),
            risk_tolerance=getattr(request, 'risk_tolerance', 'moderate')
        )
        
        # Generate arbitrage scores using ML pipeline
        scores = await inference_service.score_arbitrage_opportunity(ml_request)
        
        # Save scores to database
        for score in scores:
            await data_service.save_arbitrage_score(score)
        
        # Convert to response format
        prediction = PredictionResponse(
            arbitrage_score=max(score.score for score in scores) if scores else 0.0,
            confidence=max(score.confidence for score in scores) if scores else 0.0,
            factors={
                'property_scores': [
                    {
                        'property_id': score.property_id,
                        'score': score.score,
                        'factors': score.factors
                    } for score in scores
                ]
            },
            expected_return=max(score.expected_return for score in scores if score.expected_return) if scores else None,
            risk_score=max(score.risk_score for score in scores if score.risk_score) if scores else None,
            disclaimer=settings.LEGAL_DISCLAIMER
        )
        
        # Log prediction for audit trail
        prediction_service = PredictionService(db)
        await prediction_service.log_prediction(
            user_id=current_user.id,
            prediction=prediction,
            request_data=request
        )
        
        return prediction
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/forecast", response_model=ForecastResponse)
async def forecast_trends(
    request: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Generate forecasts for cap rates, property values, and interest rates.
    
    **Legal Disclaimer**: For informational purposes only. Not investment advice.
    CapSight does not guarantee outcomes.
    """
    try:
        # Get ML services
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # Create ML forecast request
        ml_request = MLForecastRequest(
            property_id=getattr(request, 'property_id', None),
            forecast_type=request.forecast_type,
            horizon_months=request.time_horizon,
            model_type=getattr(request, 'model_type', 'prophet'),
            include_confidence=True
        )
        
        # Generate forecast using ML pipeline
        forecast_result = await inference_service.generate_forecast(ml_request)
        
        # Save forecast to database
        await data_service.save_forecast(forecast_result)
        
        # Convert to response format
        forecast = ForecastResponse(
            forecast_type=forecast_result.forecast_type,
            predictions=[
                {
                    'date': pred.date.isoformat(),
                    'value': pred.value,
                    'lower_bound': pred.lower_bound,
                    'upper_bound': pred.upper_bound,
                    'confidence': pred.confidence
                }
                for pred in forecast_result.predictions
            ],
            metrics=forecast_result.metrics,
            model_info={
                'model_type': forecast_result.model_type,
                'version': forecast_result.metadata.get('model_version')
            },
            disclaimer=settings.LEGAL_DISCLAIMER
        )
        
        # Log forecast for audit trail
        prediction_service = PredictionService(db)
        await prediction_service.log_forecast(
            user_id=current_user.id,
            forecast=forecast,
            request_data=request
        )
        
        return forecast
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast failed: {str(e)}"
        )


@router.post("/batch", response_model=Dict[str, Any])
async def batch_predict(
    request: BatchPredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Run batch predictions across multiple properties.
    
    **Legal Disclaimer**: For informational purposes only. Not investment advice.
    """
    try:
        # Get ML services
        inference_service = get_inference_service()
        data_service = get_data_service(db)
        
        # Convert request to ML format
        ml_request = BatchPredictRequest(
            properties=request.properties,
            forecast_types=getattr(request, 'forecast_types', ['cap_rate', 'noi', 'rent']),
            horizon_months=getattr(request, 'horizon_months', 12),
            include_scoring=getattr(request, 'include_scoring', True)
        )
        
        # Run batch prediction
        results = await inference_service.batch_predict(ml_request)
        
        # Save results to database
        for property_id, forecasts in results['forecasts'].items():
            for forecast_type, forecast_result in forecasts.items():
                await data_service.save_forecast(forecast_result)
        
        for score in results['scores']:
            await data_service.save_arbitrage_score(score)
        
        # Add disclaimer
        results['disclaimer'] = settings.LEGAL_DISCLAIMER
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@router.get("/models/status")
async def get_model_status(
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get status of ML models."""
    try:
        inference_service = get_inference_service()
        model_status = await inference_service.get_model_status()
        
        return {
            "models": model_status,
            "disclaimer": settings.LEGAL_DISCLAIMER,
            "confidence_threshold": getattr(settings, 'MODEL_CONFIDENCE_THRESHOLD', 0.8)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model status: {str(e)}"
        )


@router.post("/models/retrain")
async def retrain_models(
    model_names: Optional[List[str]] = Query(None),
    current_user: User = Depends(AuthService.get_current_admin_user)
) -> Any:
    """Retrain ML models (admin only)."""
    try:
        inference_service = get_inference_service()
        
        # Get all models if none specified
        if not model_names:
            status = await inference_service.get_model_status()
            model_names = list(status.keys())
        
        # Retrain models
        results = {}
        for model_name in model_names:
            try:
                result = await inference_service.retrain_model(model_name)
                results[model_name] = result
            except Exception as e:
                results[model_name] = {'error': str(e)}
        
        return {
            "retrained_models": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model retraining failed: {str(e)}"
        )


@router.post("/models/backtest")
async def run_backtest(
    model_name: str,
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Run backtest for a specific model."""
    try:
        inference_service = get_inference_service()
        
        # Run backtest
        result = await inference_service.run_backtest(
            model_name=model_name,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "backtest_results": result,
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {str(e)}"
        )


@router.get("/prediction-history")
async def get_prediction_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get user's prediction history."""
    try:
        prediction_service = PredictionService(db)
        
        history = await prediction_service.get_user_prediction_history(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return {
            "predictions": history,
            "total": len(history),
            "disclaimer": settings.LEGAL_DISCLAIMER
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prediction history: {str(e)}"
        )
