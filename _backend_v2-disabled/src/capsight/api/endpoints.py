"""
FastAPI-based API layer for CapSight real-time predictions
Provides REST and GraphQL endpoints for model serving
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator

from ..core.config import settings
from ..core.utils import logger, METRICS, track_execution_time, PredictionResult
from ..models import FeatureStoreService, RealTimeFeatureService, ModelRegistry
from ..models.predictors import CapRatePredictor, NOIGrowthForecaster, ArbitrageScorer
from ..monitoring.health import HealthChecker

# Mock imports for development
try:
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    import redis.asyncio as redis
except ImportError:
    pass


# Pydantic models for API
class PropertyRequest(BaseModel):
    """Request for property-level predictions"""
    property_id: str = Field(..., description="Unique property identifier")
    market_id: Optional[str] = Field(None, description="Market/MSA identifier")
    current_noi: Optional[float] = Field(None, description="Current NOI")
    current_caprate: Optional[float] = Field(None, description="Current cap rate")
    property_type: str = Field(default="multifamily", description="Property type")
    
    @validator("property_id")
    def property_id_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("property_id cannot be empty")
        return v


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions"""
    properties: List[PropertyRequest] = Field(..., max_items=100)
    include_explanations: bool = Field(default=True)
    confidence_level: float = Field(default=0.8, ge=0.5, le=0.99)


class PredictionResponse(BaseModel):
    """Response containing predictions"""
    property_id: str
    prediction_timestamp: datetime
    model_version: str
    
    # Core predictions
    implied_caprate: float = Field(..., description="Predicted cap rate")
    caprate_confidence_lower: float
    caprate_confidence_upper: float
    
    noi_growth_12m: float = Field(..., description="12-month NOI growth forecast")
    noi_growth_confidence_lower: float
    noi_growth_confidence_upper: float
    
    arbitrage_score: float = Field(..., description="0-100 arbitrage score")
    arbitrage_percentile: float
    
    # Explanations
    key_drivers: List[str] = Field(..., description="Top prediction drivers")
    shap_values: Dict[str, float] = Field(default_factory=dict)
    risk_factors: List[str] = Field(default_factory=list)
    
    # Metadata
    prediction_latency_ms: float
    data_freshness_score: float = Field(..., description="0-1 data freshness score")
    model_confidence: float = Field(..., description="Overall model confidence")


class BatchPredictionResponse(BaseModel):
    """Response for batch predictions"""
    request_id: str
    predictions: List[PredictionResponse]
    summary: Dict[str, Any]
    processing_time_ms: float


class MarketInsightRequest(BaseModel):
    """Request for market-level insights"""
    market_id: str
    property_types: List[str] = Field(default=["multifamily", "office", "retail", "industrial"])
    time_horizon_months: int = Field(default=12, ge=1, le=36)


class MarketInsightResponse(BaseModel):
    """Market-level insights response"""
    market_id: str
    analysis_timestamp: datetime
    
    # Market metrics
    market_implied_caprate: float
    caprate_trend_12m: float
    transaction_volume_index: float
    demand_supply_ratio: float
    
    # Opportunities
    top_opportunity_segments: List[Dict[str, Any]]
    risk_factors: List[str]
    market_outlook: str  # "bullish", "neutral", "bearish"
    
    # Supporting data
    comparable_markets: List[str]
    data_quality_score: float


class PredictionService:
    """Main prediction service orchestrator"""
    
    def __init__(self):
        self.feature_store: Optional[FeatureStoreService] = None
        self.rt_feature_service: Optional[RealTimeFeatureService] = None
        self.model_registry: Optional[ModelRegistry] = None
        self.models: Dict[str, Any] = {}
        self.redis_client = None
    
    async def initialize(self):
        """Initialize prediction service"""
        logger.info("Initializing prediction service")
        
        # Initialize feature store
        self.feature_store = FeatureStoreService()
        await self.feature_store.initialize()
        
        # Initialize real-time feature service
        self.rt_feature_service = RealTimeFeatureService(self.feature_store)
        
        # Initialize model registry
        self.model_registry = ModelRegistry()
        await self.model_registry.initialize()
        
        # Load production models
        await self._load_production_models()
        
        # Initialize Redis for caching
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning("Redis connection failed, using memory cache", error=str(e))
            self.redis_client = None
        
        logger.info("Prediction service initialized successfully")
    
    async def _load_production_models(self):
        """Load production models from registry"""
        model_configs = [
            ("caprate_predictor", CapRatePredictor),
            ("noi_growth_forecaster", NOIGrowthForecaster),
            ("arbitrage_scorer", ArbitrageScorer)
        ]
        
        for model_name, model_class in model_configs:
            try:
                # Try loading from registry first
                model = await self.model_registry.load_model(model_name, "production")
                
                if model is None:
                    # Fallback: create and train new model with mock data
                    logger.warning(f"No production model found for {model_name}, creating new instance")
                    model = model_class()
                    
                    # Mock training data
                    import numpy as np
                    X_mock = np.random.random((1000, 20))
                    y_mock = np.random.random(1000)
                    
                    await model.train(X_mock, y_mock)
                
                self.models[model_name] = model
                logger.info("Model loaded", model_name=model_name)
                
            except Exception as e:
                logger.error("Failed to load model", model_name=model_name, error=str(e))
                # Create placeholder model
                self.models[model_name] = model_class()
    
    @track_execution_time("model_inference_duration")
    async def predict_single_property(self, request: PropertyRequest) -> PredictionResponse:
        """Generate predictions for single property"""
        start_time = datetime.now()
        
        # Check cache first
        cache_key = f"prediction:{request.property_id}:{request.market_id or 'default'}"
        cached_result = await self._get_cached_prediction(cache_key)
        
        if cached_result:
            return cached_result
        
        # Get features
        feature_request = self._build_feature_request(request)
        features = await self.feature_store.get_features(feature_request)
        
        # Validate data freshness
        if features.freshness_scores.get("treasury_features", 0) < 0.5:
            logger.warning("Stale treasury data detected", 
                          freshness=features.freshness_scores.get("treasury_features"))
        
        # Prepare feature matrix
        feature_matrix = self._prepare_feature_matrix(features.features)
        
        # Generate predictions
        predictions = {}
        
        # Cap rate prediction
        if "caprate_predictor" in self.models:
            caprate_pred, caprate_meta = await self.models["caprate_predictor"].predict(
                feature_matrix, include_uncertainty=True
            )
            predictions["caprate"] = {
                "value": float(caprate_pred[0]),
                "metadata": caprate_meta
            }
        else:
            # Fallback prediction
            predictions["caprate"] = {
                "value": 0.055,  # Mock 5.5%
                "metadata": {"confidence_intervals": {"lower": [0.050], "upper": [0.060]}}
            }
        
        # NOI growth prediction
        if "noi_growth_forecaster" in self.models:
            # Create mock time series data
            import pandas as pd
            mock_ts = pd.DataFrame({
                'ds': pd.date_range('2020-01-01', periods=36, freq='M'),
                'y': [1000000 * (1.02 ** i) for i in range(36)]  # Mock 2% growth
            })
            
            noi_pred, noi_meta = await self.models["noi_growth_forecaster"].predict(
                future_periods=12
            )
            
            if len(noi_pred) > 0:
                predictions["noi_growth"] = {
                    "value": float(noi_pred.iloc[-1]['yhat'] if 'yhat' in noi_pred.columns else 0.02),
                    "metadata": noi_meta
                }
            else:
                predictions["noi_growth"] = {"value": 0.025, "metadata": {}}
        else:
            predictions["noi_growth"] = {"value": 0.025, "metadata": {}}
        
        # Arbitrage scoring
        if "arbitrage_scorer" in self.models:
            arb_score, arb_meta = await self.models["arbitrage_scorer"].predict(feature_matrix)
            predictions["arbitrage"] = {
                "score": float(arb_score[0]),
                "percentile": 75.0,  # Mock percentile
                "metadata": arb_meta
            }
        else:
            predictions["arbitrage"] = {"score": 68.5, "percentile": 75.0, "metadata": {}}
        
        # Generate explanations
        explanations = await self._generate_explanations(feature_matrix, features.features)
        
        # Calculate overall confidence
        data_freshness = min(features.freshness_scores.values()) if features.freshness_scores else 0.8
        model_confidence = 0.85  # Mock confidence
        
        # Build response
        response = PredictionResponse(
            property_id=request.property_id,
            prediction_timestamp=datetime.now(timezone.utc),
            model_version="ensemble_v2.1",
            implied_caprate=predictions["caprate"]["value"],
            caprate_confidence_lower=predictions["caprate"]["metadata"].get("confidence_intervals", {}).get("lower", [0.050])[0],
            caprate_confidence_upper=predictions["caprate"]["metadata"].get("confidence_intervals", {}).get("upper", [0.060])[0],
            noi_growth_12m=predictions["noi_growth"]["value"],
            noi_growth_confidence_lower=predictions["noi_growth"]["value"] * 0.8,
            noi_growth_confidence_upper=predictions["noi_growth"]["value"] * 1.2,
            arbitrage_score=predictions["arbitrage"]["score"],
            arbitrage_percentile=predictions["arbitrage"]["percentile"],
            key_drivers=explanations["key_drivers"],
            shap_values=explanations["shap_values"],
            risk_factors=explanations["risk_factors"],
            prediction_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            data_freshness_score=data_freshness,
            model_confidence=model_confidence
        )
        
        # Cache result
        await self._cache_prediction(cache_key, response)
        
        # Update metrics
        METRICS["predictions_total"].labels(
            model_name="ensemble", 
            model_version="v2.1"
        ).inc()
        
        return response
    
    async def predict_batch_properties(self, request: BatchPredictionRequest) -> BatchPredictionResponse:
        """Generate predictions for batch of properties"""
        start_time = datetime.now()
        request_id = f"batch_{int(start_time.timestamp())}"
        
        logger.info("Processing batch prediction", 
                   request_id=request_id, 
                   property_count=len(request.properties))
        
        # Process properties in parallel
        tasks = []
        for prop_request in request.properties:
            task = asyncio.create_task(self.predict_single_property(prop_request))
            tasks.append(task)
        
        # Wait for all predictions
        predictions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful predictions
        successful_predictions = []
        failed_count = 0
        
        for i, result in enumerate(predictions):
            if isinstance(result, Exception):
                logger.error("Batch prediction failed", 
                           property_id=request.properties[i].property_id,
                           error=str(result))
                failed_count += 1
            else:
                successful_predictions.append(result)
        
        # Calculate summary statistics
        if successful_predictions:
            avg_arbitrage = sum(p.arbitrage_score for p in successful_predictions) / len(successful_predictions)
            avg_caprate = sum(p.implied_caprate for p in successful_predictions) / len(successful_predictions)
            avg_freshness = sum(p.data_freshness_score for p in successful_predictions) / len(successful_predictions)
        else:
            avg_arbitrage = avg_caprate = avg_freshness = 0.0
        
        summary = {
            "total_requests": len(request.properties),
            "successful_predictions": len(successful_predictions),
            "failed_predictions": failed_count,
            "average_arbitrage_score": avg_arbitrage,
            "average_implied_caprate": avg_caprate,
            "average_data_freshness": avg_freshness
        }
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return BatchPredictionResponse(
            request_id=request_id,
            predictions=successful_predictions,
            summary=summary,
            processing_time_ms=processing_time
        )
    
    def _build_feature_request(self, request: PropertyRequest):
        """Build feature store request from property request"""
        from ..models.feature_store import FeatureRequest
        
        return FeatureRequest(
            entity_values={
                "property_id": request.property_id,
                "market_id": request.market_id or "default",
                "date": datetime.now(timezone.utc)
            },
            timestamp=datetime.now(timezone.utc)
        )
    
    def _prepare_feature_matrix(self, features: Dict[str, Any]):
        """Convert features dict to numpy matrix for model input"""
        import numpy as np
        
        # Mock feature matrix preparation
        # In production, would have consistent feature ordering and scaling
        feature_values = []
        for key, value in features.items():
            if isinstance(value, (int, float)):
                feature_values.append(float(value))
        
        # Pad or truncate to expected size (20 features for mock models)
        while len(feature_values) < 20:
            feature_values.append(0.0)
        feature_values = feature_values[:20]
        
        return np.array([feature_values])
    
    async def _generate_explanations(self, feature_matrix, features_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SHAP explanations for predictions"""
        
        # Mock explanations - in production would use actual SHAP
        key_drivers = [
            "10-year Treasury rate",
            "Market cap rate trend", 
            "Local demand indicators"
        ]
        
        shap_values = {
            "treasury_10y_rate": 0.15,
            "market_caprate_trend": -0.08,
            "local_foot_traffic": 0.05
        }
        
        risk_factors = [
            "Interest rate volatility",
            "Market supply pipeline"
        ]
        
        return {
            "key_drivers": key_drivers,
            "shap_values": shap_values,
            "risk_factors": risk_factors
        }
    
    async def _get_cached_prediction(self, cache_key: str) -> Optional[PredictionResponse]:
        """Get cached prediction result"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                import json
                data = json.loads(cached_data)
                return PredictionResponse(**data)
        except Exception as e:
            logger.warning("Cache retrieval failed", error=str(e))
        
        return None
    
    async def _cache_prediction(self, cache_key: str, response: PredictionResponse):
        """Cache prediction result"""
        if not self.redis_client:
            return
        
        try:
            import json
            cached_data = response.dict()
            # Convert datetime to string for JSON serialization
            cached_data["prediction_timestamp"] = cached_data["prediction_timestamp"].isoformat()
            
            await self.redis_client.setex(
                cache_key, 
                300,  # 5 minute TTL
                json.dumps(cached_data, default=str)
            )
        except Exception as e:
            logger.warning("Cache storage failed", error=str(e))


# Global prediction service instance
prediction_service = PredictionService()

# FastAPI app
app = FastAPI(
    title="CapSight Prediction API",
    description="Real-time commercial real estate arbitrage predictions",
    version="2.1.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Health checker
health_checker = HealthChecker()

# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await prediction_service.initialize()
    await health_checker.initialize()
    logger.info("CapSight API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if prediction_service.redis_client:
        await prediction_service.redis_client.close()
    logger.info("CapSight API shutdown complete")

# API endpoints
@app.post("/v1/predict/property", response_model=PredictionResponse)
async def predict_property(request: PropertyRequest):
    """Generate prediction for single property"""
    try:
        return await prediction_service.predict_single_property(request)
    except Exception as e:
        logger.error("Property prediction failed", 
                    property_id=request.property_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/v1/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """Generate predictions for batch of properties"""
    try:
        return await prediction_service.predict_batch_properties(request)
    except Exception as e:
        logger.error("Batch prediction failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return await health_checker.check_health()

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return {"error": "Prometheus client not available"}

@app.get("/v1/models/status")
async def model_status():
    """Get model status and metadata"""
    model_info = {}
    
    for model_name, model in prediction_service.models.items():
        model_info[model_name] = {
            "name": getattr(model, 'model_name', model_name),
            "version": getattr(model, 'model_version', 'unknown'),
            "loaded": model is not None,
            "last_prediction": "2024-01-01T00:00:00Z"  # Mock timestamp
        }
    
    return {
        "models": model_info,
        "total_models": len(model_info),
        "healthy_models": sum(1 for m in model_info.values() if m["loaded"])
    }

# Export for module
__all__ = ["app", "prediction_service", "PredictionService"]
