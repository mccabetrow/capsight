"""
ML model implementations for CapSight real estate arbitrage prediction
Includes ensemble models, conformal prediction, and SHAP explanations
"""

import asyncio
import json
import pickle
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..core.config import settings, MODEL_STAGES, ACCURACY_ALERTS
from ..core.utils import logger, METRICS, track_execution_time, PredictionResult
from .feature_store import FeatureStoreService, FeatureRequest

# Mock ML imports - will resolve when requirements installed
try:
    import numpy as np
    import pandas as pd
    from sklearn.base import BaseEstimator
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score
    import lightgbm as lgb
    import xgboost as xgb
    from prophet import Prophet
    import shap
    from mapie import MapieRegressor
    import mlflow
    import mlflow.sklearn
except ImportError:
    # Mock base classes for development
    class BaseEstimator:
        def fit(self, X, y): pass
        def predict(self, X): pass
    
    class RandomForestRegressor(BaseEstimator): pass
    class Prophet: pass


@dataclass
class ModelMetadata:
    """Model metadata and performance metrics"""
    model_name: str
    model_version: str
    model_stage: str
    training_date: datetime
    features_used: List[str]
    performance_metrics: Dict[str, float]
    shap_feature_importance: Dict[str, float]
    calibration_score: float
    data_freshness_threshold: float


class BaseModel(ABC):
    """Abstract base class for all CapSight models"""
    
    def __init__(self, model_name: str, model_version: str = "1.0"):
        self.model_name = model_name
        self.model_version = model_version
        self.model = None
        self.feature_columns = []
        self.metadata = None
        self.shap_explainer = None
    
    @abstractmethod
    async def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        """Train the model"""
        pass
    
    @abstractmethod
    async def predict(self, X: np.ndarray, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Make predictions with metadata"""
        pass
    
    async def explain_prediction(self, X: np.ndarray, max_features: int = 10) -> Dict[str, Any]:
        """Generate SHAP explanations for predictions"""
        if not self.shap_explainer:
            return {}
        
        try:
            shap_values = self.shap_explainer.shap_values(X)
            
            # Get feature importance
            if isinstance(shap_values, list):  # Multi-output
                shap_values = shap_values[0]
            
            feature_importance = {}
            for i, feature in enumerate(self.feature_columns[:max_features]):
                if i < len(shap_values[0]):
                    feature_importance[feature] = float(shap_values[0][i])
            
            return {
                "shap_values": feature_importance,
                "expected_value": float(self.shap_explainer.expected_value),
                "feature_contributions": sorted(
                    feature_importance.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:5]
            }
        except Exception as e:
            logger.error("SHAP explanation failed", error=str(e))
            return {}


class CapRatePredictor(BaseModel):
    """Ensemble model for cap rate prediction"""
    
    def __init__(self):
        super().__init__("caprate_predictor", "2.1")
        self.models = {
            "lightgbm": None,
            "xgboost": None, 
            "random_forest": None
        }
        self.weights = {"lightgbm": 0.4, "xgboost": 0.35, "random_forest": 0.25}
        self.conformal_predictor = None
    
    async def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        """Train ensemble cap rate prediction model"""
        logger.info("Training cap rate predictor ensemble", samples=len(X), features=X.shape[1])
        
        metrics = {}
        
        # Train LightGBM
        lgb_params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'verbose': -1
        }
        
        train_data = lgb.Dataset(X, label=y)
        self.models["lightgbm"] = lgb.train(
            lgb_params, 
            train_data, 
            num_boost_round=100,
            valid_sets=[train_data],
            callbacks=[lgb.early_stopping(10)]
        )
        
        # Train XGBoost
        self.models["xgboost"] = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.models["xgboost"].fit(X, y)
        
        # Train Random Forest
        self.models["random_forest"] = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.models["random_forest"].fit(X, y)
        
        # Train conformal predictor for uncertainty quantification
        base_model = self.models["lightgbm"]  # Use best model as base
        self.conformal_predictor = MapieRegressor(base_model, cv=5, method="plus")
        
        # Convert to format expected by Mapie (needs predict method)
        class LGBWrapper:
            def __init__(self, model):
                self.model = model
            def predict(self, X):
                return self.model.predict(X)
        
        wrapped_model = LGBWrapper(self.models["lightgbm"])
        self.conformal_predictor = MapieRegressor(wrapped_model, cv=5)
        
        # Calculate performance metrics
        ensemble_pred = await self._ensemble_predict(X)
        mae = np.mean(np.abs(ensemble_pred - y))
        rmse = np.sqrt(np.mean((ensemble_pred - y) ** 2))
        
        metrics = {
            "mae_bps": mae * 10000,  # Convert to basis points
            "rmse_bps": rmse * 10000,
            "r2_score": 1 - np.sum((y - ensemble_pred) ** 2) / np.sum((y - np.mean(y)) ** 2)
        }
        
        # Setup SHAP explainer
        self.shap_explainer = shap.TreeExplainer(self.models["lightgbm"])
        
        logger.info("Cap rate model training completed", **metrics)
        return metrics
    
    async def predict(self, X: np.ndarray, include_uncertainty: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Make cap rate predictions with uncertainty intervals"""
        
        # Ensemble prediction
        predictions = await self._ensemble_predict(X)
        
        metadata = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "ensemble_weights": self.weights
        }
        
        # Add uncertainty intervals if requested
        if include_uncertainty and self.conformal_predictor:
            try:
                # Predict with conformal intervals
                y_pred, y_intervals = self.conformal_predictor.predict(X, alpha=0.2)  # 80% confidence
                
                metadata["confidence_intervals"] = {
                    "lower": y_intervals[:, 0].tolist(),
                    "upper": y_intervals[:, 1].tolist(),
                    "confidence_level": 0.8
                }
            except Exception as e:
                logger.warning("Conformal prediction failed", error=str(e))
                metadata["confidence_intervals"] = None
        
        return predictions, metadata
    
    async def _ensemble_predict(self, X: np.ndarray) -> np.ndarray:
        """Make ensemble predictions from all models"""
        predictions = []
        
        # LightGBM prediction
        lgb_pred = self.models["lightgbm"].predict(X)
        predictions.append(lgb_pred * self.weights["lightgbm"])
        
        # XGBoost prediction  
        xgb_pred = self.models["xgboost"].predict(X)
        predictions.append(xgb_pred * self.weights["xgboost"])
        
        # Random Forest prediction
        rf_pred = self.models["random_forest"].predict(X)
        predictions.append(rf_pred * self.weights["random_forest"])
        
        # Weighted ensemble
        ensemble_pred = np.sum(predictions, axis=0)
        return ensemble_pred


class NOIGrowthForecaster(BaseModel):
    """Time series forecasting model for NOI growth"""
    
    def __init__(self):
        super().__init__("noi_growth_forecaster", "1.5")
        self.prophet_model = None
        self.feature_model = None  # Additional ML model for feature-based predictions
    
    async def train(self, time_series_data: pd.DataFrame, feature_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """Train NOI growth forecasting model"""
        logger.info("Training NOI growth forecaster", samples=len(time_series_data))
        
        # Train Prophet model for time series component
        prophet_data = time_series_data[['ds', 'y']].copy()  # Prophet format: ds (date), y (value)
        
        self.prophet_model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            holidays_prior_scale=10.0,
            daily_seasonality=False,
            yearly_seasonality=True,
            weekly_seasonality=False
        )
        
        # Add additional regressors if feature data provided
        if feature_data is not None:
            for col in feature_data.columns:
                if col not in ['ds', 'y']:
                    self.prophet_model.add_regressor(col)
            
            # Merge feature data
            prophet_data = prophet_data.merge(feature_data, on='ds', how='left')
        
        self.prophet_model.fit(prophet_data)
        
        # Calculate performance metrics
        future = self.prophet_model.make_future_dataframe(periods=0)
        if feature_data is not None:
            future = future.merge(feature_data, on='ds', how='left')
        
        forecast = self.prophet_model.predict(future)
        actual = prophet_data['y'].values
        predicted = forecast['yhat'].values
        
        mae = np.mean(np.abs(predicted - actual))
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        
        metrics = {
            "mae": mae,
            "mape_percent": mape,
            "rmse": np.sqrt(np.mean((predicted - actual) ** 2))
        }
        
        logger.info("NOI growth model training completed", **metrics)
        return metrics
    
    async def predict(self, future_periods: int = 12, future_features: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Forecast NOI growth for future periods"""
        
        # Create future dataframe
        future = self.prophet_model.make_future_dataframe(periods=future_periods, freq='M')
        
        # Add future features if provided
        if future_features is not None:
            future = future.merge(future_features, on='ds', how='left')
        
        # Generate forecast
        forecast = self.prophet_model.predict(future)
        
        # Extract predictions
        predictions_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(future_periods)
        
        metadata = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "forecast_periods": future_periods,
            "uncertainty_intervals": True
        }
        
        return predictions_df, metadata


class ArbitrageScorer(BaseModel):
    """Model to score arbitrage opportunities"""
    
    def __init__(self):
        super().__init__("arbitrage_scorer", "1.3")
        self.scoring_model = None
        self.percentile_thresholds = {}
    
    async def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        """Train arbitrage scoring model"""
        logger.info("Training arbitrage scoring model", samples=len(X))
        
        # Use gradient boosting for scoring
        self.scoring_model = lgb.LGBMRegressor(
            objective='regression',
            metric='mae',
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=50,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
            verbose=-1,
            random_state=42
        )
        
        self.scoring_model.fit(X, y)
        
        # Calculate percentile thresholds for scoring
        train_scores = self.scoring_model.predict(X)
        self.percentile_thresholds = {
            "90th": np.percentile(train_scores, 90),
            "75th": np.percentile(train_scores, 75),
            "50th": np.percentile(train_scores, 50),
            "25th": np.percentile(train_scores, 25)
        }
        
        # Performance metrics
        mae = np.mean(np.abs(train_scores - y))
        correlation = np.corrcoef(train_scores, y)[0, 1]
        
        # Calculate top-decile precision
        top_decile_threshold = np.percentile(y, 90)
        predicted_top_decile = train_scores >= np.percentile(train_scores, 90)
        actual_top_decile = y >= top_decile_threshold
        
        top_decile_precision = np.sum(predicted_top_decile & actual_top_decile) / np.sum(predicted_top_decile)
        
        metrics = {
            "mae": mae,
            "correlation": correlation,
            "top_decile_precision": top_decile_precision
        }
        
        # Setup SHAP explainer
        self.shap_explainer = shap.TreeExplainer(self.scoring_model)
        
        logger.info("Arbitrage scoring model training completed", **metrics)
        return metrics
    
    async def predict(self, X: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Score arbitrage opportunities"""
        
        raw_scores = self.scoring_model.predict(X)
        
        # Convert to percentiles
        percentile_scores = np.zeros_like(raw_scores)
        for i, score in enumerate(raw_scores):
            percentile = 0
            for threshold_name, threshold_val in self.percentile_thresholds.items():
                if score >= threshold_val:
                    percentile = int(threshold_name.replace("th", ""))
                    break
            percentile_scores[i] = percentile
        
        # Scale to 0-100
        scaled_scores = (raw_scores - np.min(raw_scores)) / (np.max(raw_scores) - np.min(raw_scores)) * 100
        
        metadata = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "percentile_thresholds": self.percentile_thresholds,
            "raw_scores": raw_scores.tolist(),
            "percentile_scores": percentile_scores.tolist()
        }
        
        return scaled_scores, metadata


class ModelRegistry:
    """MLflow-based model registry for model versioning and deployment"""
    
    def __init__(self):
        self.mlflow_client = None
        self.registered_models = {}
    
    async def initialize(self):
        """Initialize MLflow model registry"""
        try:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            self.mlflow_client = mlflow.tracking.MlflowClient()
            logger.info("Model registry initialized", tracking_uri=settings.mlflow_tracking_uri)
        except Exception as e:
            logger.error("Failed to initialize model registry", error=str(e))
            # Fallback to local file-based registry
            self.mlflow_client = None
    
    async def register_model(self, model: BaseModel, metrics: Dict[str, float], stage: str = "staging"):
        """Register trained model in MLflow"""
        try:
            # Create experiment run
            with mlflow.start_run(run_name=f"{model.model_name}_v{model.model_version}"):
                # Log metrics
                for metric_name, value in metrics.items():
                    mlflow.log_metric(metric_name, value)
                
                # Log model parameters
                mlflow.log_param("model_name", model.model_name)
                mlflow.log_param("model_version", model.model_version)
                mlflow.log_param("training_timestamp", datetime.now(timezone.utc).isoformat())
                
                # Log model artifact
                if hasattr(model, 'models') and model.models:
                    # Ensemble model
                    for sub_model_name, sub_model in model.models.items():
                        mlflow.sklearn.log_model(
                            sub_model, 
                            f"model_{sub_model_name}",
                            registered_model_name=f"{model.model_name}_{sub_model_name}"
                        )
                else:
                    # Single model
                    mlflow.sklearn.log_model(
                        model, 
                        "model",
                        registered_model_name=model.model_name
                    )
                
                # Create model metadata
                metadata = ModelMetadata(
                    model_name=model.model_name,
                    model_version=model.model_version,
                    model_stage=stage,
                    training_date=datetime.now(timezone.utc),
                    features_used=model.feature_columns,
                    performance_metrics=metrics,
                    shap_feature_importance={},
                    calibration_score=metrics.get("calibration_score", 0.0),
                    data_freshness_threshold=0.8
                )
                
                self.registered_models[model.model_name] = metadata
                
                logger.info("Model registered successfully", 
                          model_name=model.model_name, 
                          version=model.model_version,
                          stage=stage)
        
        except Exception as e:
            logger.error("Model registration failed", 
                        model_name=model.model_name, 
                        error=str(e))
            # Fallback to local storage
            await self._save_model_locally(model, metrics, stage)
    
    async def load_model(self, model_name: str, stage: str = "production") -> Optional[BaseModel]:
        """Load model from registry"""
        try:
            if self.mlflow_client:
                # Load from MLflow
                model_version = self.mlflow_client.get_latest_versions(
                    model_name, 
                    stages=[stage]
                )[0]
                
                model_uri = f"models:/{model_name}/{model_version.version}"
                loaded_model = mlflow.sklearn.load_model(model_uri)
                
                return loaded_model
            else:
                # Load from local storage
                return await self._load_model_locally(model_name, stage)
                
        except Exception as e:
            logger.error("Model loading failed", model_name=model_name, error=str(e))
            return None
    
    async def promote_model(self, model_name: str, from_stage: str, to_stage: str):
        """Promote model between stages"""
        try:
            if self.mlflow_client:
                latest_version = self.mlflow_client.get_latest_versions(
                    model_name, 
                    stages=[from_stage]
                )[0]
                
                self.mlflow_client.transition_model_version_stage(
                    name=model_name,
                    version=latest_version.version,
                    stage=to_stage
                )
                
                logger.info("Model promoted", 
                          model_name=model_name,
                          from_stage=from_stage,
                          to_stage=to_stage,
                          version=latest_version.version)
        
        except Exception as e:
            logger.error("Model promotion failed", error=str(e))
    
    async def _save_model_locally(self, model: BaseModel, metrics: Dict[str, float], stage: str):
        """Fallback: save model to local file"""
        import os
        model_dir = f"models/{model.model_name}"
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = f"{model_dir}/{model.model_version}_{stage}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        
        # Save metadata
        metadata_path = f"{model_dir}/{model.model_version}_{stage}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump({
                "model_name": model.model_name,
                "model_version": model.model_version,
                "stage": stage,
                "metrics": metrics,
                "training_date": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)
    
    async def _load_model_locally(self, model_name: str, stage: str) -> Optional[BaseModel]:
        """Fallback: load model from local file"""
        try:
            model_dir = f"models/{model_name}"
            # Find latest version for stage
            import os, glob
            pattern = f"{model_dir}/*_{stage}.pkl"
            model_files = glob.glob(pattern)
            
            if model_files:
                latest_file = max(model_files, key=os.path.getctime)
                with open(latest_file, "rb") as f:
                    return pickle.load(f)
            
            return None
        except Exception as e:
            logger.error("Local model loading failed", error=str(e))
            return None


# Export main classes
__all__ = [
    "BaseModel",
    "CapRatePredictor", 
    "NOIGrowthForecaster",
    "ArbitrageScorer",
    "ModelRegistry",
    "ModelMetadata"
]
