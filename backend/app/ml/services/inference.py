"""
ML Inference Service
High-level interface for ML predictions and forecasting
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from pathlib import Path

from ..models import (
    ForecastResult, ArbitrageScore, PropertyData, MacroData,
    ForecastRequest, ArbitrageRequest, BatchPredictRequest,
    get_registry
)
from ..pipelines.rates_forecast import RatesForecastPipeline
from ..pipelines.caprate_forecast import CapRateForecastPipeline  
from ..pipelines.noi_rent_forecast import NOIRentForecastPipeline
from ..pipelines.ensemble_score import EnsembleScorePipeline
from ..scoring import ArbitrageScorer
from ..backtest import BacktestEngine
from ..config import MLConfig
from ..utils.logging import get_ml_logger

logger = get_ml_logger(__name__)

class MLInferenceService:
    """High-level ML inference service"""
    
    def __init__(self):
        self.config = MLConfig()
        self.registry = get_registry()
        
        # Initialize pipelines
        self._pipelines = {
            'rates': RatesForecastPipeline(),
            'caprate': CapRateForecastPipeline(),
            'noi_rent': NOIRentForecastPipeline(),
            'ensemble': EnsembleScorePipeline()
        }
        
        # Initialize services
        self.scorer = ArbitrageScorer()
        self.backtester = BacktestEngine()
        
        logger.info("ML Inference Service initialized")
    
    async def generate_forecast(self, request: ForecastRequest) -> ForecastResult:
        """Generate a single forecast"""
        
        logger.info(f"Generating {request.forecast_type} forecast for property {request.property_id}")
        
        try:
            # Get appropriate pipeline
            pipeline = self._get_pipeline_for_forecast_type(request.forecast_type)
            
            # Load data (placeholder - would come from data service)
            property_data = await self._load_property_data(request.property_id, request.start_date)
            macro_data = await self._load_macro_data(request.start_date)
            
            # Generate forecast
            result = await pipeline.predict(
                property_data=property_data,
                macro_data=macro_data,
                horizon_months=request.horizon_months,
                include_confidence=request.include_confidence
            )
            
            # Convert to standard format
            forecast_result = ForecastResult(
                forecast_type=request.forecast_type,
                property_id=request.property_id,
                model_type=pipeline.model_type,
                predictions=result['predictions'],
                metrics=result.get('metrics', {}),
                metadata={
                    'horizon_months': request.horizon_months,
                    'model_version': result.get('model_version'),
                    'generated_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Generated forecast with {len(forecast_result.predictions)} predictions")
            
            return forecast_result
            
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            raise
    
    async def score_arbitrage_opportunity(self, request: ArbitrageRequest) -> List[ArbitrageScore]:
        """Score arbitrage opportunities for properties"""
        
        logger.info(f"Scoring arbitrage opportunities for {len(request.property_ids)} properties")
        
        try:
            scores = []
            
            for property_id in request.property_ids:
                # Generate required forecasts
                forecasts = await self._generate_all_forecasts(
                    property_id, 
                    request.hold_period_months
                )
                
                # Calculate arbitrage score
                score = await self.scorer.score_property(
                    property_id=property_id,
                    forecasts=forecasts,
                    hold_period_months=request.hold_period_months,
                    min_expected_return=request.min_expected_return,
                    risk_tolerance=request.risk_tolerance
                )
                
                scores.append(score)
            
            # Sort by score (highest first)
            scores.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Generated {len(scores)} arbitrage scores")
            
            return scores
            
        except Exception as e:
            logger.error(f"Error scoring arbitrage opportunities: {e}")
            raise
    
    async def batch_predict(self, request: BatchPredictRequest) -> Dict[str, Any]:
        """Run batch predictions across multiple properties"""
        
        logger.info(f"Running batch predictions for {len(request.properties)} properties")
        
        try:
            results = {
                'forecasts': {},
                'scores': [],
                'summary': {}
            }
            
            # Generate forecasts for each property and forecast type
            for property_data in request.properties:
                property_id = property_data['property_id']
                property_forecasts = {}
                
                for forecast_type in request.forecast_types:
                    forecast_request = ForecastRequest(
                        property_id=property_id,
                        forecast_type=forecast_type,
                        horizon_months=request.horizon_months
                    )
                    
                    forecast = await self.generate_forecast(forecast_request)
                    property_forecasts[forecast_type] = forecast
                
                results['forecasts'][property_id] = property_forecasts
                
                # Generate arbitrage scores if requested
                if request.include_scoring:
                    arbitrage_request = ArbitrageRequest(
                        property_ids=[property_id],
                        hold_period_months=request.horizon_months
                    )
                    
                    scores = await self.score_arbitrage_opportunity(arbitrage_request)
                    results['scores'].extend(scores)
            
            # Generate summary statistics
            results['summary'] = {
                'total_properties': len(request.properties),
                'forecast_types': request.forecast_types,
                'total_forecasts': len(results['forecasts']) * len(request.forecast_types),
                'total_scores': len(results['scores']),
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info(f"Batch prediction completed: {results['summary']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch prediction: {e}")
            raise
    
    async def run_backtest(self, model_name: str, start_date: datetime, 
                          end_date: datetime, **kwargs) -> Dict[str, Any]:
        """Run backtest for a specific model"""
        
        logger.info(f"Running backtest for {model_name} from {start_date} to {end_date}")
        
        try:
            # Get pipeline
            pipeline = self._get_pipeline_by_name(model_name)
            
            # Load historical data
            historical_data = await self._load_historical_data(start_date, end_date)
            
            # Run backtest
            result = await self.backtester.run_backtest(
                pipeline=pipeline,
                data=historical_data,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
            
            logger.info(f"Backtest completed with {len(result.predictions)} predictions")
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            raise
    
    async def retrain_model(self, model_name: str, 
                           training_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Retrain a specific model"""
        
        logger.info(f"Retraining model: {model_name}")
        
        try:
            # Get pipeline
            pipeline = self._get_pipeline_by_name(model_name)
            
            # Load training data if not provided
            if training_data is None:
                training_data = await self._load_training_data(model_name)
            
            # Train model
            result = await pipeline.train(training_data)
            
            # Save new model version
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = self.registry.save_model(
                model_name=model_name,
                model_obj=result['model'],
                version=version,
                metadata={
                    'training_samples': len(training_data),
                    'metrics': result.get('metrics', {}),
                    'retrained_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Model {model_name} retrained and saved to {model_path}")
            
            return {
                'model_name': model_name,
                'version': version,
                'model_path': model_path,
                'metrics': result.get('metrics', {}),
                'training_samples': len(training_data)
            }
            
        except Exception as e:
            logger.error(f"Error retraining model {model_name}: {e}")
            raise
    
    async def get_model_status(self, model_name: str = None) -> Dict[str, Any]:
        """Get status of models in the system"""
        
        try:
            if model_name:
                # Get status for specific model
                info = self.registry.get_model_info(model_name)
                return {model_name: info}
            else:
                # Get status for all models
                models = self.registry.list_models()
                status = {}
                
                for model_name, versions in models.items():
                    try:
                        latest_info = self.registry.get_model_info(model_name, "latest")
                        status[model_name] = {
                            'versions': versions,
                            'latest_version': latest_info.get('version'),
                            'latest_info': latest_info
                        }
                    except:
                        status[model_name] = {
                            'versions': versions,
                            'latest_version': None,
                            'latest_info': None
                        }
                
                return status
                
        except Exception as e:
            logger.error(f"Error getting model status: {e}")
            raise
    
    def _get_pipeline_for_forecast_type(self, forecast_type: str):
        """Get appropriate pipeline for forecast type"""
        
        type_mapping = {
            'interest_rate': 'rates',
            'cap_rate': 'caprate', 
            'noi': 'noi_rent',
            'rent': 'noi_rent',
            'occupancy': 'noi_rent'
        }
        
        pipeline_name = type_mapping.get(forecast_type)
        if not pipeline_name:
            raise ValueError(f"Unsupported forecast type: {forecast_type}")
        
        return self._pipelines[pipeline_name]
    
    def _get_pipeline_by_name(self, model_name: str):
        """Get pipeline by model name"""
        
        if model_name in self._pipelines:
            return self._pipelines[model_name]
        
        # Try to infer from model name
        for pipeline_name, pipeline in self._pipelines.items():
            if model_name.startswith(pipeline_name) or pipeline_name in model_name:
                return pipeline
        
        raise ValueError(f"Unknown model: {model_name}")
    
    async def _generate_all_forecasts(self, property_id: str, 
                                     horizon_months: int) -> Dict[str, ForecastResult]:
        """Generate all required forecasts for arbitrage scoring"""
        
        forecast_types = ['cap_rate', 'interest_rate', 'noi', 'rent']
        forecasts = {}
        
        for forecast_type in forecast_types:
            request = ForecastRequest(
                property_id=property_id,
                forecast_type=forecast_type,
                horizon_months=horizon_months
            )
            
            forecasts[forecast_type] = await self.generate_forecast(request)
        
        return forecasts
    
    async def _load_property_data(self, property_id: str, 
                                 start_date: datetime) -> List[PropertyData]:
        """Load property time series data"""
        
        # Placeholder - would integrate with data service
        # For now, return synthetic data
        from ..datasets import DatasetManager
        dataset_manager = DatasetManager()
        
        synthetic_data = dataset_manager.generate_synthetic_property_data(
            property_id=property_id,
            start_date=start_date - timedelta(days=365*2),  # 2 years of history
            end_date=start_date,
            frequency='M'
        )
        
        return [PropertyData(**row) for _, row in synthetic_data.iterrows()]
    
    async def _load_macro_data(self, start_date: datetime) -> List[MacroData]:
        """Load macro-economic data"""
        
        # Placeholder - would integrate with data service
        from ..datasets import DatasetManager
        dataset_manager = DatasetManager()
        
        macro_data = dataset_manager.load_macro_data(
            start_date=start_date - timedelta(days=365*2),
            end_date=start_date
        )
        
        return [MacroData(**row) for _, row in macro_data.iterrows()]
    
    async def _load_historical_data(self, start_date: datetime, 
                                   end_date: datetime) -> pd.DataFrame:
        """Load historical data for backtesting"""
        
        # Placeholder - would integrate with data service
        from ..datasets import DatasetManager
        dataset_manager = DatasetManager()
        
        return dataset_manager.generate_synthetic_property_data(
            property_id="backtest_data",
            start_date=start_date,
            end_date=end_date,
            frequency='M'
        )
    
    async def _load_training_data(self, model_name: str) -> pd.DataFrame:
        """Load training data for model retraining"""
        
        # Placeholder - would integrate with data service
        from ..datasets import DatasetManager
        dataset_manager = DatasetManager()
        
        # Load last 3 years of data for training
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*3)
        
        return dataset_manager.generate_synthetic_property_data(
            property_id="training_data", 
            start_date=start_date,
            end_date=end_date,
            frequency='M'
        )

# Global service instance
_inference_service = None

def get_inference_service() -> MLInferenceService:
    """Get global ML inference service instance"""
    global _inference_service
    
    if _inference_service is None:
        _inference_service = MLInferenceService()
    
    return _inference_service

__all__ = ['MLInferenceService', 'get_inference_service']
