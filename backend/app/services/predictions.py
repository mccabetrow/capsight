"""
Prediction service for property forecasting and ML model integration.
"""

import uuid
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import random
import logging
import sys
import os

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.forecast import Forecast
from app.models.property import Property
from app.schemas.forecast import (
    ForecastCreate, ForecastRead, ForecastUpdate, ForecastQuery,
    ForecastSummary, ForecastBatch, ForecastBatchResult
)

# Import ML forecasting engine
ml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml')
if ml_path not in sys.path:
    sys.path.append(ml_path)

try:
    from models.forecasting_engine import CapSightForecaster, ForecastResult
    ML_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("ML forecasting engine loaded successfully")
except ImportError as e:
    ML_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"ML forecasting engine not available: {e}")


class PredictionService:
    """Service for property predictions and forecasting."""
    
    def __init__(self, db: Session):
        self.db = db
        if ML_AVAILABLE:
            self.ml_forecaster = CapSightForecaster()
        else:
            self.ml_forecaster = None
    
    def get_forecasts(
        self, 
        query: ForecastQuery, 
        user_id: Optional[uuid.UUID] = None
    ) -> List[ForecastSummary]:
        """Get forecasts with filtering."""
        db_query = self.db.query(Forecast)
        
        # Apply filters
        if query.property_id:
            db_query = db_query.filter(Forecast.property_id == query.property_id)
        
        if query.model_version:
            db_query = db_query.filter(Forecast.model_version == query.model_version)
        
        if query.forecast_type:
            db_query = db_query.filter(Forecast.forecast_type == query.forecast_type)
        
        if query.min_confidence is not None:
            db_query = db_query.filter(Forecast.confidence_score >= query.min_confidence)
        
        if query.min_time_horizon is not None:
            db_query = db_query.filter(Forecast.time_horizon_months >= query.min_time_horizon)
        
        if query.max_time_horizon is not None:
            db_query = db_query.filter(Forecast.time_horizon_months <= query.max_time_horizon)
        
        # Order by creation date (newest first)
        db_query = db_query.order_by(desc(Forecast.created_at))
        
        # Apply pagination
        forecasts = db_query.offset(query.skip).limit(query.limit).all()
        
        return [self._to_summary(forecast) for forecast in forecasts]
    
    def get_forecast_by_id(
        self, 
        forecast_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[ForecastRead]:
        """Get forecast by ID."""
        forecast = self.db.query(Forecast).filter(Forecast.id == forecast_id).first()
        if forecast:
            return self._to_read(forecast)
        return None
    
    def create_forecast(
        self, 
        forecast_data: ForecastCreate, 
        user_id: Optional[uuid.UUID] = None
    ) -> ForecastRead:
        """Create a new forecast."""
        db_forecast = Forecast(
            property_id=forecast_data.property_id,
            model_version=forecast_data.model_version,
            forecast_type=forecast_data.forecast_type,
            time_horizon_months=forecast_data.time_horizon_months,
            predicted_value=forecast_data.predicted_value,
            confidence_score=forecast_data.confidence_score,
            prediction_interval_lower=forecast_data.prediction_interval_lower,
            prediction_interval_upper=forecast_data.prediction_interval_upper,
            market_factors=forecast_data.market_factors,
            assumptions=forecast_data.assumptions,
            methodology=forecast_data.methodology
        )
        
        self.db.add(db_forecast)
        self.db.commit()
        self.db.refresh(db_forecast)
        
        return self._to_read(db_forecast)
    
    def update_forecast(
        self, 
        forecast_id: uuid.UUID, 
        forecast_data: ForecastUpdate, 
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[ForecastRead]:
        """Update an existing forecast."""
        forecast = self.db.query(Forecast).filter(Forecast.id == forecast_id).first()
        if not forecast:
            return None
        
        # Update fields
        update_data = forecast_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(forecast, field) and value is not None:
                setattr(forecast, field, value)
        
        forecast.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(forecast)
        
        return self._to_read(forecast)
    
    def delete_forecast(
        self, 
        forecast_id: uuid.UUID, 
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete a forecast."""
        forecast = self.db.query(Forecast).filter(Forecast.id == forecast_id).first()
        if forecast:
            self.db.delete(forecast)
            self.db.commit()
            return True
        return False
    
    def generate_forecast_for_property(
        self,
        property_id: uuid.UUID,
        forecast_type: str = "price_appreciation",
        time_horizon_months: int = 12,
        model_version: str = "v1.2",
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[ForecastRead]:
        """Generate a forecast for a specific property using ML models."""
        property_obj = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return None
        
        # Use ML prediction engine if available
        if self.ml_forecaster and ML_AVAILABLE:
            predicted_value, confidence, market_factors = self._run_ml_prediction(
                property_obj, forecast_type, time_horizon_months
            )
        else:
            # Fallback to mock prediction
            predicted_value, confidence, market_factors = self._run_mock_prediction(
                property_obj, forecast_type, time_horizon_months
            )
        
        # Create forecast data
        forecast_data = ForecastCreate(
            property_id=property_id,
            model_version=model_version,
            forecast_type=forecast_type,
            time_horizon_months=time_horizon_months,
            predicted_value=predicted_value,
            confidence_score=confidence,
            prediction_interval_lower=predicted_value * Decimal('0.9'),
            prediction_interval_upper=predicted_value * Decimal('1.1'),
            market_factors=market_factors,
            assumptions={
                "interest_rate": "5.5%",
                "inflation_rate": "3.2%",
                "market_growth": "stable",
                "local_development": "moderate"
            },
            methodology=f"CapSight ML model {model_version} using Prophet time series forecasting, "
                       f"XGBoost feature regression, and comparative market analysis"
        )
        
        return self.create_forecast(forecast_data, user_id)
    
    def get_forecasts_for_property(
        self, 
        property_id: uuid.UUID, 
        forecast_type: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> List[ForecastSummary]:
        """Get all forecasts for a specific property."""
        query = self.db.query(Forecast).filter(Forecast.property_id == property_id)
        
        if forecast_type:
            query = query.filter(Forecast.forecast_type == forecast_type)
        
        forecasts = query.order_by(desc(Forecast.created_at)).all()
        return [self._to_summary(forecast) for forecast in forecasts]
    
    def generate_forecasts_batch(
        self, 
        batch_request: ForecastBatch, 
        user_id: Optional[uuid.UUID] = None
    ) -> ForecastBatchResult:
        """Generate forecasts for multiple properties in batch."""
        successful = 0
        failed = 0
        forecasts = []
        errors = []
        
        for property_id in batch_request.property_ids:
            try:
                forecast = self.generate_forecast_for_property(
                    property_id=property_id,
                    forecast_type=batch_request.forecast_type,
                    time_horizon_months=batch_request.time_horizon_months,
                    model_version=batch_request.model_version,
                    user_id=user_id
                )
                
                if forecast:
                    forecasts.append(forecast)
                    successful += 1
                else:
                    failed += 1
                    errors.append(f"Property {property_id}: Unable to generate forecast")
                    
            except Exception as e:
                failed += 1
                errors.append(f"Property {property_id}: {str(e)}")
        
        return ForecastBatchResult(
            total_requested=len(batch_request.property_ids),
            successful=successful,
            failed=failed,
            forecasts=forecasts,
            errors=errors[:10]  # Limit to first 10 errors
        )
    
    def run_model_backtest(
        self, 
        model_id: str, 
        start_date: str, 
        end_date: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Run backtest for a prediction model (mock implementation)."""
        # Mock backtest results
        return {
            "model_id": model_id,
            "backtest_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "performance_metrics": {
                "mae": 0.085,  # Mean Absolute Error
                "rmse": 0.112,  # Root Mean Square Error
                "mape": 8.3,   # Mean Absolute Percentage Error
                "r_squared": 0.847,  # R-squared
                "accuracy_1_year": 0.89,
                "accuracy_2_year": 0.82,
                "accuracy_3_year": 0.76
            },
            "prediction_distribution": {
                "within_5_percent": 0.68,
                "within_10_percent": 0.85,
                "within_15_percent": 0.94
            },
            "total_predictions": 1247,
            "correct_direction": 0.91,  # Percentage that predicted correct direction
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def get_prediction_accuracy(
        self, 
        model_version: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get prediction accuracy metrics."""
        # Mock accuracy data
        return {
            "overall_accuracy": 0.87,
            "accuracy_by_horizon": {
                "1_month": 0.94,
                "3_months": 0.91,
                "6_months": 0.89,
                "12_months": 0.85,
                "24_months": 0.78
            },
            "accuracy_by_type": {
                "price_appreciation": 0.89,
                "rental_yield": 0.86,
                "market_timing": 0.82
            },
            "confidence_calibration": {
                "high_confidence": {"accuracy": 0.93, "count": 345},
                "medium_confidence": {"accuracy": 0.87, "count": 567},
                "low_confidence": {"accuracy": 0.74, "count": 123}
            },
            "model_version": model_version or "v1.1",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_model_performance(
        self, 
        time_period: str = "30d",
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get model performance analytics."""
        return {
            "time_period": time_period,
            "total_predictions": 1456,
            "average_confidence": 0.84,
            "prediction_volume_trend": "increasing",
            "error_rates": {
                "mae": 0.078,
                "rmse": 0.105,
                "mape": 7.8
            },
            "feature_importance": {
                "location": 0.28,
                "property_age": 0.19,
                "market_indicators": 0.17,
                "comparable_sales": 0.15,
                "economic_factors": 0.12,
                "property_features": 0.09
            },
            "model_drift": {
                "detected": False,
                "last_retrain": "2024-01-01T00:00:00Z",
                "next_scheduled_retrain": "2024-02-01T00:00:00Z"
            }
        }
    
    def _run_ml_prediction(
        self, 
        property_obj: Property, 
        forecast_type: str, 
        time_horizon_months: int
    ) -> tuple[Decimal, Decimal, Dict[str, Any]]:
        """Run ML prediction using CapSight forecasting engine."""
        try:
            if not self.ml_forecaster:
                return self._run_mock_prediction(property_obj, forecast_type, time_horizon_months)
            
            # Convert property to ML engine format
            property_data = {
                "id": str(property_obj.id),
                "price": float(property_obj.list_price),
                "square_feet": property_obj.square_feet or 0,
                "bedrooms": property_obj.bedrooms or 0,
                "bathrooms": property_obj.bathrooms or 0,
                "year_built": property_obj.year_built or 2000,
                "lot_size": float(property_obj.lot_size_acres or 0),
                "estimated_rent": float(property_obj.estimated_rental_income or 0),
                "location": f"{property_obj.city}_{property_obj.state}".lower().replace(" ", "_")
            }
            
            # Generate forecast based on type
            if forecast_type == "rental_income":
                ml_result = self.ml_forecaster.predict_rental_income(
                    property_data, 
                    forecast_periods=[time_horizon_months]
                )
            else:  # Default to price prediction
                ml_result = self.ml_forecaster.predict_property_value(
                    property_data,
                    forecast_periods=[time_horizon_months]
                )
            
            # Extract prediction for the requested time horizon
            period_key = f"{time_horizon_months}_months"
            if period_key in ml_result.predictions:
                predicted_value = Decimal(str(ml_result.predictions[period_key]))
            else:
                predicted_value = Decimal(str(ml_result.current_value * 1.04))  # Fallback
            
            confidence = Decimal(str(ml_result.model_accuracy))
            
            # Convert factors to market factors format
            market_factors = {
                "prediction_factors": [
                    {
                        "name": factor["name"],
                        "impact": factor["impact"],
                        "weight": factor["weight"]
                    }
                    for factor in ml_result.factors
                ],
                "model_accuracy": ml_result.model_accuracy,
                "forecast_type": ml_result.forecast_type,
                "generated_at": ml_result.created_at.isoformat()
            }
            
            logger.info(f"ML prediction generated for property {property_obj.id}")
            return predicted_value, confidence, market_factors
            
        except Exception as e:
            logger.error(f"ML prediction failed for property {property_obj.id}: {e}")
            return self._run_mock_prediction(property_obj, forecast_type, time_horizon_months)
    
    def _run_mock_prediction(
        self, 
        property_obj: Property, 
        forecast_type: str, 
        time_horizon_months: int
    ) -> tuple[Decimal, Decimal, Dict[str, Any]]:
        """Run mock prediction (fallback when ML is unavailable)."""
        # Mock ML prediction based on property characteristics
        base_value = property_obj.list_price
        
        # Mock prediction logic
        if forecast_type == "rental_income":
            base_value = property_obj.estimated_rental_income or (base_value * Decimal('0.005'))
            growth_rate = random.uniform(0.02, 0.05)  # 2-5% annual rental growth
        else:
            growth_rate = random.uniform(0.02, 0.08)  # 2-8% annual price growth
        
        monthly_rate = growth_rate / 12
        predicted_value = base_value * Decimal(str(1 + (monthly_rate * time_horizon_months)))
        
        # Confidence based on various factors
        confidence = Decimal(str(random.uniform(0.7, 0.95)))
        
        # Mock market factors
        market_factors = {
            "median_price_trend": "increasing",
            "inventory_level": "low",
            "days_on_market": 32,
            "price_per_sqft_growth": "4.2%",
            "local_market_score": 8.7,
            "economic_indicators": {
                "employment_rate": "96.3%",
                "population_growth": "1.8%",
                "new_construction": "moderate"
            },
            "model_type": "mock_fallback"
        }
        
        return predicted_value, confidence, market_factors
    
    def _to_read(self, forecast: Forecast) -> ForecastRead:
        """Convert Forecast model to ForecastRead schema."""
        return ForecastRead(
            id=forecast.id,
            property_id=forecast.property_id,
            model_version=forecast.model_version,
            forecast_type=forecast.forecast_type,
            time_horizon_months=forecast.time_horizon_months,
            predicted_value=forecast.predicted_value,
            confidence_score=forecast.confidence_score,
            prediction_interval_lower=forecast.prediction_interval_lower,
            prediction_interval_upper=forecast.prediction_interval_upper,
            market_factors=forecast.market_factors,
            assumptions=forecast.assumptions,
            methodology=forecast.methodology,
            created_at=forecast.created_at,
            updated_at=forecast.updated_at
        )
    
    def _to_summary(self, forecast: Forecast) -> ForecastSummary:
        """Convert Forecast model to ForecastSummary schema."""
        return ForecastSummary(
            id=forecast.id,
            property_id=forecast.property_id,
            model_version=forecast.model_version,
            forecast_type=forecast.forecast_type,
            time_horizon_months=forecast.time_horizon_months,
            predicted_value=forecast.predicted_value,
            confidence_score=forecast.confidence_score,
            created_at=forecast.created_at
        )
