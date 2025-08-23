"""
Cap Rate Forecasting Pipeline
Uses Prophet for market-segment specific cap rate predictions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import warnings
import joblib
from pathlib import Path
from itertools import product

# Prophet import with error handling
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    warnings.warn("Prophet not available, using naive forecasts")

# ARIMA fallback
try:
    from statsmodels.tsa.arima.model import ARIMA
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False

from ..config import MLConfig, MODELS_PATH
from ..utils.seed import set_random_seed

logger = logging.getLogger(__name__)
set_random_seed(MLConfig.RANDOM_SEED)

class CapRateForecastPipeline:
    """Forecast cap rates by market and asset type segments"""
    
    def __init__(self, model_name: str = "caprate_forecast"):
        self.model_name = model_name
        self.segment_models = {}  # (market, asset_type) -> model
        self.fallback_models = {}  # ARIMA models for segments that fail Prophet
        self.is_fitted = False
        self.segments = []
        self.global_averages = {}
        
    def _create_segments(self, df: pd.DataFrame) -> List[Tuple[str, str]]:
        """Create market-asset_type segments"""
        if 'market' in df.columns and 'asset_type' in df.columns:
            segments = list(df.groupby(['market', 'asset_type']).groups.keys())
        elif 'market' in df.columns:
            segments = [(market, 'all') for market in df['market'].unique()]
        else:
            segments = [('all', 'all')]
        
        logger.info(f"Created {len(segments)} cap rate segments: {segments}")
        return segments
    
    def _prepare_segment_data(self, df: pd.DataFrame, 
                             market: str, asset_type: str) -> pd.DataFrame:
        """Prepare data for a specific market-asset segment"""
        if market == 'all' and asset_type == 'all':
            segment_df = df.copy()
        elif market == 'all':
            segment_df = df[df['asset_type'] == asset_type].copy()
        elif asset_type == 'all':
            segment_df = df[df['market'] == market].copy()
        else:
            segment_df = df[(df['market'] == market) & (df['asset_type'] == asset_type)].copy()
        
        if len(segment_df) == 0:
            return None
        
        # Aggregate to monthly averages
        segment_df['date'] = pd.to_datetime(segment_df['date'])
        monthly_avg = segment_df.groupby('date')['cap_rate_observed'].agg(['mean', 'count']).reset_index()
        monthly_avg = monthly_avg.rename(columns={'mean': 'cap_rate_avg'})
        
        # Filter out months with very few observations
        monthly_avg = monthly_avg[monthly_avg['count'] >= 1]
        
        if len(monthly_avg) < MLConfig.MIN_TRAINING_SAMPLES:
            return None
        
        return monthly_avg[['date', 'cap_rate_avg']]
    
    def _fit_prophet_segment(self, segment_df: pd.DataFrame, 
                           segment_name: str) -> Optional[Prophet]:
        """Fit Prophet model for a single segment"""
        if not PROPHET_AVAILABLE or segment_df is None:
            return None
        
        # Prepare for Prophet
        prophet_df = segment_df.rename(columns={'date': 'ds', 'cap_rate_avg': 'y'})
        prophet_df = prophet_df.dropna()
        
        if len(prophet_df) < MLConfig.MIN_TRAINING_SAMPLES:
            logger.warning(f"Insufficient data for segment {segment_name}: {len(prophet_df)} samples")
            return None
        
        try:
            # Configure Prophet with cap rate specific settings
            model = Prophet(
                changepoint_prior_scale=0.001,  # Lower for cap rates (less volatile)
                seasonality_prior_scale=5.0,   # Moderate seasonality
                holidays_prior_scale=5.0,
                seasonality_mode='additive',
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.80,
                growth='linear'  # Cap rates tend to have linear trends
            )
            
            # Add custom seasonality for real estate cycles (quarterly)
            model.add_seasonality(name='quarterly', period=91.25, fourier_order=2)
            
            # Fit model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(prophet_df)
            
            logger.info(f"Prophet model fitted for segment {segment_name}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to fit Prophet model for {segment_name}: {e}")
            return None
    
    def _fit_arima_segment(self, segment_df: pd.DataFrame,
                          segment_name: str) -> Optional[Dict]:
        """Fit ARIMA model as fallback for a segment"""
        if not ARIMA_AVAILABLE or segment_df is None:
            return None
        
        series = segment_df['cap_rate_avg'].dropna()
        if len(series) < MLConfig.MIN_TRAINING_SAMPLES:
            return None
        
        try:
            # Simple ARIMA model selection
            best_aic = float('inf')
            best_model = None
            best_order = None
            
            # Try a few simple configurations
            orders = [(1, 1, 1), (2, 1, 1), (1, 1, 2), (0, 1, 1), (1, 0, 1)]
            
            for order in orders:
                try:
                    model = ARIMA(series, order=order)
                    fitted = model.fit()
                    if fitted.aic < best_aic:
                        best_aic = fitted.aic
                        best_model = fitted
                        best_order = order
                except:
                    continue
            
            if best_model is not None:
                logger.info(f"ARIMA{best_order} fitted for segment {segment_name}, AIC: {best_aic:.2f}")
                return {
                    'model': best_model,
                    'order': best_order,
                    'aic': best_aic
                }
            
        except Exception as e:
            logger.error(f"Failed to fit ARIMA for {segment_name}: {e}")
        
        return None
    
    def fit(self, property_df: pd.DataFrame) -> 'CapRateForecastPipeline':
        """Fit cap rate forecasting models by segment"""
        logger.info("Starting cap rate forecast pipeline training")
        
        if 'cap_rate_observed' not in property_df.columns:
            raise ValueError("cap_rate_observed column required for training")
        
        # Create segments
        self.segments = self._create_segments(property_df)
        
        # Calculate global averages for fallback
        if 'market' in property_df.columns:
            self.global_averages = property_df.groupby('market')['cap_rate_observed'].mean().to_dict()
        else:
            self.global_averages = {'all': property_df['cap_rate_observed'].mean()}
        
        # Fit models for each segment
        for market, asset_type in self.segments:
            segment_name = f"{market}_{asset_type}"
            logger.info(f"Fitting models for segment: {segment_name}")
            
            # Prepare segment data
            segment_df = self._prepare_segment_data(property_df, market, asset_type)
            
            if segment_df is None:
                logger.warning(f"No data available for segment {segment_name}")
                continue
            
            # Try Prophet first
            prophet_model = self._fit_prophet_segment(segment_df, segment_name)
            if prophet_model:
                self.segment_models[(market, asset_type)] = {
                    'type': 'prophet',
                    'model': prophet_model
                }
            else:
                # Fallback to ARIMA
                arima_model = self._fit_arima_segment(segment_df, segment_name)
                if arima_model:
                    self.segment_models[(market, asset_type)] = {
                        'type': 'arima',
                        'model': arima_model
                    }
                else:
                    logger.warning(f"No model could be fitted for segment {segment_name}")
        
        self.is_fitted = True
        logger.info(f"Cap rate forecasting completed. Fitted {len(self.segment_models)} models")
        
        return self
    
    def predict(self, markets: List[str] = None, 
                asset_types: List[str] = None,
                horizon_months: int = 6) -> Dict[str, Any]:
        """Generate cap rate forecasts by segment"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        if markets is None:
            markets = list(set([seg[0] for seg in self.segments]))
        if asset_types is None:
            asset_types = list(set([seg[1] for seg in self.segments]))
        
        logger.info(f"Generating cap rate forecasts for {len(markets)} markets, {len(asset_types)} asset types")
        
        results = {}
        
        # Generate future dates
        last_date = datetime.now().replace(day=1)
        future_dates = pd.date_range(
            start=last_date + timedelta(days=32),
            periods=horizon_months,
            freq='M'
        )
        
        for market in markets:
            for asset_type in asset_types:
                segment_key = (market, asset_type)
                segment_name = f"{market}_{asset_type}"
                
                # Initialize result structure
                result = {
                    'market': market,
                    'asset_type': asset_type,
                    'dates': future_dates.tolist(),
                    'forecasts': [],
                    'lower_bounds': [],
                    'upper_bounds': [],
                    'model_used': 'none'
                }
                
                # Try to get model for this segment
                model_info = self.segment_models.get(segment_key)
                
                if model_info:
                    if model_info['type'] == 'prophet':
                        try:
                            prophet_model = model_info['model']
                            future_df = pd.DataFrame({'ds': future_dates})
                            
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                forecast = prophet_model.predict(future_df)
                            
                            result['forecasts'] = forecast['yhat'].tolist()
                            result['lower_bounds'] = forecast['yhat_lower'].tolist()
                            result['upper_bounds'] = forecast['yhat_upper'].tolist()
                            result['model_used'] = 'prophet'
                            
                        except Exception as e:
                            logger.error(f"Prophet prediction failed for {segment_name}: {e}")
                    
                    elif model_info['type'] == 'arima':
                        try:
                            arima_model = model_info['model']['model']
                            forecast_result = arima_model.forecast(steps=horizon_months, alpha=0.2)
                            conf_int = arima_model.get_forecast(steps=horizon_months, alpha=0.2).conf_int()
                            
                            result['forecasts'] = forecast_result.tolist() if hasattr(forecast_result, 'tolist') else [float(forecast_result)]
                            result['lower_bounds'] = conf_int.iloc[:, 0].tolist() if hasattr(conf_int, 'iloc') else [float(forecast_result) * 0.95]
                            result['upper_bounds'] = conf_int.iloc[:, 1].tolist() if hasattr(conf_int, 'iloc') else [float(forecast_result) * 1.05]
                            result['model_used'] = 'arima'
                            
                        except Exception as e:
                            logger.error(f"ARIMA prediction failed for {segment_name}: {e}")
                
                # Fallback: use global average with slight trend
                if result['model_used'] == 'none':
                    base_cap_rate = self.global_averages.get(market, 0.065)  # 6.5% default
                    trend = -0.0002  # Slight downward trend (cap rate compression)
                    
                    naive_forecasts = [base_cap_rate + trend * i for i in range(1, horizon_months + 1)]
                    
                    result['forecasts'] = naive_forecasts
                    result['lower_bounds'] = [f * 0.85 for f in naive_forecasts]  # ±15% confidence
                    result['upper_bounds'] = [f * 1.15 for f in naive_forecasts]
                    result['model_used'] = 'naive'
                    
                    logger.warning(f"Using naive forecast for {segment_name}")
                
                results[segment_name] = result
        
        return results
    
    def save_models(self, version: str = None) -> str:
        """Save trained models"""
        if not self.is_fitted:
            raise ValueError("No fitted models to save")
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_dir = MODELS_PATH / self.model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save segment models
        for (market, asset_type), model_info in self.segment_models.items():
            segment_name = f"{market}_{asset_type}"
            model_path = model_dir / f"{segment_name}_{model_info['type']}.pkl"
            
            with open(model_path, 'wb') as f:
                joblib.dump(model_info, f)
        
        # Save metadata
        metadata = {
            'model_name': self.model_name,
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'segments': [(m, a) for m, a in self.segments],
            'global_averages': self.global_averages,
            'n_models': len(self.segment_models)
        }
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            import json
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Cap rate models saved to {model_dir}")
        return str(model_dir)
    
    def load_models(self, version: str = "latest") -> 'CapRateForecastPipeline':
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
                self.segments = [tuple(seg) for seg in metadata.get('segments', [])]
                self.global_averages = metadata.get('global_averages', {})
        
        # Load segment models
        self.segment_models = {}
        for model_file in model_dir.glob("*.pkl"):
            if "metadata" not in model_file.name:
                with open(model_file, 'rb') as f:
                    model_info = joblib.load(f)
                
                # Extract segment from filename
                filename = model_file.stem
                parts = filename.split('_')
                if len(parts) >= 3:
                    market = parts[0]
                    asset_type = parts[1]
                    segment_key = (market, asset_type)
                    self.segment_models[segment_key] = model_info
        
        self.is_fitted = True
        logger.info(f"Cap rate models loaded from {model_dir}")
        return self
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about fitted models"""
        if not self.is_fitted:
            return {"status": "not_fitted"}
        
        info = {
            "status": "fitted",
            "model_name": self.model_name,
            "n_segments": len(self.segments),
            "n_fitted_models": len(self.segment_models),
            "segments": self.segments,
            "global_averages": self.global_averages
        }
        
        # Model type breakdown
        model_types = {}
        for model_info in self.segment_models.values():
            model_type = model_info['type']
            model_types[model_type] = model_types.get(model_type, 0) + 1
        
        info["model_types"] = model_types
        
        return info

__all__ = ['CapRateForecastPipeline']
