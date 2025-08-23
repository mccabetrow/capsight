"""
Ensemble Scoring Pipeline
XGBoost-based arbitrage scoring combining forecast signals
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import warnings
import joblib
from pathlib import Path

# XGBoost import
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    warnings.warn("XGBoost not available, using linear scoring")

# Scikit-learn imports
try:
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("Scikit-learn not available, using basic scoring")

from ..config import MLConfig, MODELS_PATH
from ..features import FeatureEngineer, create_feature_matrix
from ..utils.seed import set_random_seed

logger = logging.getLogger(__name__)
set_random_seed(MLConfig.RANDOM_SEED)

class EnsembleScoringPipeline:
    """Ensemble model for arbitrage opportunity scoring"""
    
    def __init__(self, model_name: str = "ensemble_score"):
        self.model_name = model_name
        self.model = None
        self.fallback_model = None
        self.feature_engineer = FeatureEngineer()
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.is_fitted = False
        self.feature_names = []
        self.feature_importance = {}
        self.model_performance = {}
        
    def _prepare_training_features(self, property_df: pd.DataFrame,
                                  rates_forecasts: Dict = None,
                                  caprate_forecasts: Dict = None,
                                  noi_rent_forecasts: Dict = None) -> pd.DataFrame:
        """Prepare feature matrix with forecast signals"""
        
        # Start with base property features
        feature_df = self.feature_engineer.fit_transform(property_df, target_horizon=6)
        
        # Add forecast signals as features
        if rates_forecasts:
            for rate_type, forecast_data in rates_forecasts.items():
                if 'forecasts' in forecast_data and forecast_data['forecasts']:
                    # Use first forecast period (next month)
                    next_rate = forecast_data['forecasts'][0]
                    feature_df[f'forecast_{rate_type}'] = next_rate
                    
                    # Rate change signal
                    current_rate = feature_df.get(rate_type, next_rate)
                    feature_df[f'forecast_{rate_type}_change'] = next_rate - current_rate
        
        if caprate_forecasts:
            # Join cap rate forecasts by market/asset_type
            for segment_name, forecast_data in caprate_forecasts.items():
                if 'forecasts' in forecast_data and forecast_data['forecasts']:
                    market = forecast_data.get('market', 'unknown')
                    asset_type = forecast_data.get('asset_type', 'unknown')
                    
                    # Create segment match
                    segment_mask = True
                    if 'market' in feature_df.columns and market != 'unknown':
                        segment_mask &= (feature_df['market'] == market)
                    if 'asset_type' in feature_df.columns and asset_type != 'unknown':
                        segment_mask &= (feature_df['asset_type'] == asset_type)
                    
                    if segment_mask.any():
                        next_caprate = forecast_data['forecasts'][0]
                        feature_df.loc[segment_mask, 'forecast_cap_rate'] = next_caprate
                        
                        # Cap rate compression signal (negative change is good)
                        current_caprate = feature_df.loc[segment_mask, 'cap_rate_observed'].fillna(next_caprate)
                        feature_df.loc[segment_mask, 'forecast_cap_rate_compression'] = current_caprate - next_caprate
        
        if noi_rent_forecasts:
            # Join NOI/rent forecasts by property_id
            for prop_id, forecast_data in noi_rent_forecasts.items():
                prop_mask = feature_df['property_id'] == prop_id
                
                if prop_mask.any() and 'forecasts' in forecast_data:
                    for target_col in ['noi', 'rent']:
                        if target_col in forecast_data['forecasts']:
                            col_forecasts = forecast_data['forecasts'][target_col]
                            if 'forecasts' in col_forecasts and col_forecasts['forecasts']:
                                next_value = col_forecasts['forecasts'][0]
                                feature_df.loc[prop_mask, f'forecast_{target_col}'] = next_value
                                
                                # Growth signal
                                current_value = feature_df.loc[prop_mask, target_col].fillna(next_value)
                                feature_df.loc[prop_mask, f'forecast_{target_col}_growth'] = (
                                    (next_value - current_value) / (current_value + 1e-8)
                                )
        
        return feature_df
    
    def _create_arbitrage_target(self, feature_df: pd.DataFrame, 
                                horizon_months: int = 6) -> np.ndarray:
        """Create arbitrage target variable"""
        
        # Use existing target features if available
        if 'arbitrage_signal' in feature_df.columns:
            return feature_df['arbitrage_signal'].fillna(0).values
        
        # Create synthetic arbitrage target based on forward returns
        target = np.zeros(len(feature_df))
        
        # Cap rate compression component (lower future cap rate is better)
        if 'cap_rate_return' in feature_df.columns:
            cap_rate_component = -feature_df['cap_rate_return'].fillna(0) * MLConfig.SCORING_WEIGHTS['cap_rate_compression']
            target += cap_rate_component
        
        # NOI growth component
        if 'noi_return' in feature_df.columns:
            noi_component = feature_df['noi_return'].fillna(0) * MLConfig.SCORING_WEIGHTS['noi_growth']
            target += noi_component
        
        # Rate environment component (lower rates help valuations)
        if 'base_rate_change_3m' in feature_df.columns:
            rate_component = -feature_df['base_rate_change_3m'].fillna(0) * MLConfig.SCORING_WEIGHTS['rate_environment']
            target += rate_component
        
        # Momentum component
        momentum_cols = [col for col in feature_df.columns if 'momentum_' in col and 'noi' in col]
        if momentum_cols:
            momentum_avg = feature_df[momentum_cols].mean(axis=1).fillna(0)
            momentum_component = momentum_avg * MLConfig.SCORING_WEIGHTS['momentum']
            target += momentum_component
        
        return target
    
    def fit(self, property_df: pd.DataFrame,
           rates_forecasts: Dict = None,
           caprate_forecasts: Dict = None, 
           noi_rent_forecasts: Dict = None) -> 'EnsembleScoringPipeline':
        """Train ensemble scoring model"""
        logger.info("Starting ensemble scoring pipeline training")
        
        # Prepare features
        feature_df = self._prepare_training_features(
            property_df, rates_forecasts, caprate_forecasts, noi_rent_forecasts
        )
        
        # Create target
        y = self._create_arbitrage_target(feature_df)
        
        # Create feature matrix
        X, feature_names = create_feature_matrix(feature_df)
        self.feature_names = feature_names
        
        logger.info(f"Training with {X.shape[0]} samples, {X.shape[1]} features")
        
        # Train/validation split
        if SKLEARN_AVAILABLE:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=MLConfig.RANDOM_SEED
            )
        else:
            # Simple split without sklearn
            split_idx = int(0.8 * len(X))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Scale features
        if self.scaler:
            X_train = self.scaler.fit_transform(X_train)
            X_val = self.scaler.transform(X_val)
        
        # Train XGBoost model
        if XGBOOST_AVAILABLE:
            try:
                self.model = xgb.XGBRegressor(
                    n_estimators=MLConfig.XGBOOST_N_ESTIMATORS,
                    max_depth=MLConfig.XGBOOST_MAX_DEPTH,
                    learning_rate=MLConfig.XGBOOST_LEARNING_RATE,
                    random_state=MLConfig.XGBOOST_RANDOM_STATE,
                    objective='reg:squarederror',
                    verbosity=0
                )
                
                self.model.fit(X_train, y_train)
                
                # Evaluate
                train_pred = self.model.predict(X_train)
                val_pred = self.model.predict(X_val)
                
                self.model_performance = {
                    'train_mse': mean_squared_error(y_train, train_pred) if SKLEARN_AVAILABLE else 0,
                    'val_mse': mean_squared_error(y_val, val_pred) if SKLEARN_AVAILABLE else 0,
                    'train_r2': r2_score(y_train, train_pred) if SKLEARN_AVAILABLE else 0,
                    'val_r2': r2_score(y_val, val_pred) if SKLEARN_AVAILABLE else 0
                }
                
                # Feature importance
                self.feature_importance = dict(zip(feature_names, self.model.feature_importances_))
                
                logger.info(f"XGBoost model trained. Val R2: {self.model_performance.get('val_r2', 0):.3f}")
                
            except Exception as e:
                logger.error(f"XGBoost training failed: {e}")
                self.model = None
        
        # Train fallback model (Random Forest or linear)
        if SKLEARN_AVAILABLE and not self.model:
            try:
                self.fallback_model = RandomForestRegressor(
                    n_estimators=50,
                    random_state=MLConfig.RANDOM_SEED
                )
                
                self.fallback_model.fit(X_train, y_train)
                
                val_pred = self.fallback_model.predict(X_val)
                self.model_performance = {
                    'val_mse': mean_squared_error(y_val, val_pred),
                    'val_r2': r2_score(y_val, val_pred)
                }
                
                self.feature_importance = dict(zip(feature_names, self.fallback_model.feature_importances_))
                
                logger.info(f"Random Forest fallback trained. Val R2: {self.model_performance.get('val_r2', 0):.3f}")
                
            except Exception as e:
                logger.error(f"Fallback model training failed: {e}")
                self.fallback_model = None
        
        self.is_fitted = True
        logger.info("Ensemble scoring training completed")
        
        return self
    
    def predict(self, property_df: pd.DataFrame,
                rates_forecasts: Dict = None,
                caprate_forecasts: Dict = None,
                noi_rent_forecasts: Dict = None) -> Dict[str, Any]:
        """Generate arbitrage scores"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        logger.info(f"Generating arbitrage scores for {len(property_df)} properties")
        
        # Prepare features (use transform, not fit_transform)
        feature_df = self.feature_engineer.transform(property_df)
        
        # Add forecast signals (same as training)
        if rates_forecasts:
            for rate_type, forecast_data in rates_forecasts.items():
                if 'forecasts' in forecast_data and forecast_data['forecasts']:
                    next_rate = forecast_data['forecasts'][0]
                    feature_df[f'forecast_{rate_type}'] = next_rate
                    current_rate = feature_df.get(rate_type, next_rate)
                    feature_df[f'forecast_{rate_type}_change'] = next_rate - current_rate
        
        # Add cap rate and NOI/rent forecasts (similar to training)
        # [Implementation same as in _prepare_training_features]
        
        # Create feature matrix
        X, _ = create_feature_matrix(feature_df, self.feature_names)
        
        # Scale features
        if self.scaler:
            X = self.scaler.transform(X)
        
        # Generate predictions
        if self.model:
            raw_scores = self.model.predict(X)
            model_used = 'xgboost'
        elif self.fallback_model:
            raw_scores = self.fallback_model.predict(X)
            model_used = 'random_forest'
        else:
            # Final fallback: rule-based scoring
            raw_scores = self._rule_based_scoring(feature_df)
            model_used = 'rules'
        
        # Scale to 0-100
        scores = self._scale_scores(raw_scores)
        
        # Calculate confidence based on feature coverage and model uncertainty
        confidence = self._calculate_confidence(feature_df, raw_scores)
        
        # Create results
        results = []
        for i, (_, row) in enumerate(property_df.iterrows()):
            result = {
                'property_id': row.get('property_id', f'prop_{i}'),
                'score': float(scores[i]),
                'confidence': float(confidence[i]),
                'model_used': model_used,
                'rationale': self._generate_rationale(feature_df.iloc[i], scores[i])
            }
            results.append(result)
        
        return {
            'scores': results,
            'model_info': {
                'model_used': model_used,
                'feature_count': len(self.feature_names),
                'performance': self.model_performance
            }
        }
    
    def _rule_based_scoring(self, feature_df: pd.DataFrame) -> np.ndarray:
        """Fallback rule-based scoring"""
        scores = np.zeros(len(feature_df))
        
        # Simple weighted scoring
        weights = MLConfig.SCORING_WEIGHTS
        
        # Cap rate component
        if 'cap_rate_observed' in feature_df.columns:
            # Higher cap rates are better (normalize to 0-1)
            cap_rates = feature_df['cap_rate_observed'].fillna(0.065)
            normalized_cap_rates = (cap_rates - 0.03) / 0.05  # 3-8% range
            scores += weights['cap_rate_compression'] * normalized_cap_rates
        
        # NOI growth component
        if 'noi_growth_3m' in feature_df.columns:
            noi_growth = feature_df['noi_growth_3m'].fillna(0)
            scores += weights['noi_growth'] * noi_growth * 10  # Scale up
        
        # Rate environment (lower rates better)
        if 'base_rate' in feature_df.columns:
            rates = feature_df['base_rate'].fillna(0.035)
            rate_component = (0.08 - rates) / 0.05  # Lower rates = higher score
            scores += weights['rate_environment'] * rate_component
        
        return scores
    
    def _scale_scores(self, raw_scores: np.ndarray) -> np.ndarray:
        """Scale raw scores to 0-100 range"""
        if len(raw_scores) == 0:
            return raw_scores
        
        # Robust scaling using percentiles
        p25, p75 = np.percentile(raw_scores, [25, 75])
        
        if p75 > p25:
            # Scale so that 25th percentile = 20, 75th percentile = 80
            scaled = 50 + (raw_scores - np.median(raw_scores)) / (p75 - p25) * 30
        else:
            # If no variation, center around 50
            scaled = np.full_like(raw_scores, 50)
        
        # Clip to 0-100 range
        scaled = np.clip(scaled, 0, 100)
        
        return scaled
    
    def _calculate_confidence(self, feature_df: pd.DataFrame, 
                            raw_scores: np.ndarray) -> np.ndarray:
        """Calculate prediction confidence"""
        confidence = np.ones(len(feature_df)) * 0.5  # Base confidence
        
        # Increase confidence based on feature coverage
        feature_coverage = feature_df.notna().mean(axis=1)
        confidence += (feature_coverage - 0.5) * 0.3  # Up to 30% boost
        
        # Decrease confidence for extreme scores (model less certain)
        score_extremity = np.abs(raw_scores - np.median(raw_scores)) / (np.std(raw_scores) + 1e-8)
        confidence -= np.clip(score_extremity * 0.1, 0, 0.2)
        
        # Clip to reasonable range
        confidence = np.clip(confidence, 0.1, 0.95)
        
        return confidence
    
    def _generate_rationale(self, feature_row: pd.Series, score: float) -> str:
        """Generate human-readable rationale for score"""
        rationale_parts = []
        
        # Check key factors
        if 'cap_rate_observed' in feature_row:
            cap_rate = feature_row['cap_rate_observed']
            if not pd.isna(cap_rate) and cap_rate > 0.06:
                rationale_parts.append(f"Strong cap rate of {cap_rate:.1%}")
        
        if 'noi_growth_3m' in feature_row:
            noi_growth = feature_row['noi_growth_3m']
            if not pd.isna(noi_growth) and noi_growth > 0.02:
                rationale_parts.append(f"NOI growth of {noi_growth:.1%}")
        
        if 'forecast_base_rate_change' in feature_row:
            rate_change = feature_row['forecast_base_rate_change']
            if not pd.isna(rate_change) and rate_change < -0.005:
                rationale_parts.append("Favorable rate environment")
        
        # Score-based rationale
        if score >= 75:
            rationale_parts.append("Excellent opportunity metrics")
        elif score >= 60:
            rationale_parts.append("Good opportunity potential")
        elif score <= 25:
            rationale_parts.append("Limited upside potential")
        
        if not rationale_parts:
            rationale_parts = ["Mixed market indicators"]
        
        return "; ".join(rationale_parts[:3])  # Limit to top 3 factors
    
    def save_models(self, version: str = None) -> str:
        """Save trained models"""
        if not self.is_fitted:
            raise ValueError("No fitted models to save")
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_dir = MODELS_PATH / self.model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save main model
        if self.model:
            main_model_path = model_dir / "xgboost_model.pkl"
            with open(main_model_path, 'wb') as f:
                joblib.dump(self.model, f)
        
        # Save fallback model
        if self.fallback_model:
            fallback_path = model_dir / "fallback_model.pkl"
            with open(fallback_path, 'wb') as f:
                joblib.dump(self.fallback_model, f)
        
        # Save feature engineer and scaler
        feature_eng_path = model_dir / "feature_engineer.pkl"
        with open(feature_eng_path, 'wb') as f:
            joblib.dump(self.feature_engineer, f)
        
        if self.scaler:
            scaler_path = model_dir / "scaler.pkl"
            with open(scaler_path, 'wb') as f:
                joblib.dump(self.scaler, f)
        
        # Save metadata
        metadata = {
            'model_name': self.model_name,
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance,
            'model_performance': self.model_performance,
            'has_main_model': self.model is not None,
            'has_fallback_model': self.fallback_model is not None
        }
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            import json
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Ensemble scoring models saved to {model_dir}")
        return str(model_dir)
    
    def load_models(self, version: str = "latest") -> 'EnsembleScoringPipeline':
        """Load trained models"""
        if version == "latest":
            model_base_dir = MODELS_PATH / self.model_name
            if not model_base_dir.exists():
                raise FileNotFoundError(f"No models found for {self.model_name}")
            
            versions = [d.name for d in model_base_dir.iterdir() if d.is_dir()]
            if not versions:
                raise FileNotFoundError(f"No model versions found for {self.model_name}")
            
            version = sorted(versions)[-1]
        
        model_dir = MODELS_PATH / self.model_name / version
        if not model_dir.exists():
            raise FileNotFoundError(f"Model version {version} not found")
        
        # Load metadata
        metadata_path = model_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                import json
                metadata = json.load(f)
                self.feature_names = metadata.get('feature_names', [])
                self.feature_importance = metadata.get('feature_importance', {})
                self.model_performance = metadata.get('model_performance', {})
        
        # Load models
        main_model_path = model_dir / "xgboost_model.pkl"
        if main_model_path.exists():
            with open(main_model_path, 'rb') as f:
                self.model = joblib.load(f)
        
        fallback_path = model_dir / "fallback_model.pkl"
        if fallback_path.exists():
            with open(fallback_path, 'rb') as f:
                self.fallback_model = joblib.load(f)
        
        # Load feature engineer and scaler
        feature_eng_path = model_dir / "feature_engineer.pkl"
        if feature_eng_path.exists():
            with open(feature_eng_path, 'rb') as f:
                self.feature_engineer = joblib.load(f)
        
        scaler_path = model_dir / "scaler.pkl"
        if scaler_path.exists():
            with open(scaler_path, 'wb') as f:
                self.scaler = joblib.load(f)
        
        self.is_fitted = True
        logger.info(f"Ensemble scoring models loaded from {model_dir}")
        return self
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about fitted models"""
        if not self.is_fitted:
            return {"status": "not_fitted"}
        
        info = {
            "status": "fitted",
            "model_name": self.model_name,
            "has_main_model": self.model is not None,
            "has_fallback_model": self.fallback_model is not None,
            "feature_count": len(self.feature_names),
            "performance": self.model_performance,
            "top_features": dict(sorted(self.feature_importance.items(), 
                                      key=lambda x: x[1], reverse=True)[:10])
        }
        
        return info

__all__ = ['EnsembleScoringPipeline']
