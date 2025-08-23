"""
NOI and Rent Forecasting Pipeline
Property-level forecasting for NOI and rental income
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import warnings
import joblib
from pathlib import Path

# Prophet import with error handling
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    warnings.warn("Prophet not available, using trend-based forecasts")

from ..config import MLConfig, MODELS_PATH
from ..utils.seed import set_random_seed

logger = logging.getLogger(__name__)
set_random_seed(MLConfig.RANDOM_SEED)

class NoiRentForecastPipeline:
    """Forecast NOI and rent at the property level"""
    
    def __init__(self, model_name: str = "noi_rent_forecast"):
        self.model_name = model_name
        self.property_models = {}  # property_id -> {noi_model, rent_model}
        self.market_models = {}    # market -> {noi_model, rent_model} for properties with insufficient data
        self.is_fitted = False
        self.target_columns = ['noi', 'rent']
        self.market_averages = {}
        
    def _prepare_property_series(self, df: pd.DataFrame, 
                                property_id: str, target_col: str) -> Optional[pd.DataFrame]:
        """Prepare time series for a single property and target"""
        prop_df = df[df['property_id'] == property_id].copy()
        
        if len(prop_df) < MLConfig.MIN_SERIES_LENGTH:
            return None
        
        if target_col not in prop_df.columns:
            return None
        
        # Sort by date and remove duplicates
        prop_df = prop_df.sort_values('date')
        prop_df = prop_df.drop_duplicates(subset=['date'])
        
        # Check for sufficient non-null values
        valid_data = prop_df[target_col].dropna()
        if len(valid_data) < MLConfig.MIN_SERIES_LENGTH:
            return None
        
        # Fill missing dates and interpolate
        prop_df['date'] = pd.to_datetime(prop_df['date'])
        prop_df = prop_df.set_index('date').resample('M').mean().reset_index()
        
        # Forward fill then backward fill
        prop_df[target_col] = prop_df[target_col].fillna(method='ffill').fillna(method='bfill')
        
        return prop_df[['date', target_col]].dropna()
    
    def _fit_prophet_property(self, series_df: pd.DataFrame, 
                             target_col: str, identifier: str) -> Optional[Prophet]:
        """Fit Prophet model for a single property series"""
        if not PROPHET_AVAILABLE:
            return None
        
        # Prepare for Prophet
        prophet_df = series_df.rename(columns={'date': 'ds', target_col: 'y'})
        
        if len(prophet_df) < MLConfig.MIN_TRAINING_SAMPLES:
            return None
        
        try:
            # Configure Prophet for property-level forecasting
            model = Prophet(
                changepoint_prior_scale=0.1,   # Moderate flexibility
                seasonality_prior_scale=10.0,  # Allow seasonal patterns
                holidays_prior_scale=5.0,
                seasonality_mode='multiplicative',  # Property income often has multiplicative seasonality
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.80,
                growth='linear'
            )
            
            # Add quarterly seasonality for real estate
            model.add_seasonality(name='quarterly', period=91.25, fourier_order=3)
            
            # Fit model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(prophet_df)
            
            logger.info(f"Prophet model fitted for {identifier} {target_col}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to fit Prophet model for {identifier} {target_col}: {e}")
            return None
    
    def _calculate_trend_forecast(self, series_df: pd.DataFrame, 
                                 target_col: str, horizon_months: int) -> Dict[str, List[float]]:
        """Calculate trend-based forecast as fallback"""
        values = series_df[target_col].dropna()
        
        if len(values) < 3:
            # Use last value with minimal growth
            last_value = values.iloc[-1] if len(values) > 0 else 1000
            growth_rate = 0.002  # 0.2% monthly growth
            
            forecasts = [last_value * (1 + growth_rate) ** i for i in range(1, horizon_months + 1)]
            lower_bounds = [f * 0.9 for f in forecasts]
            upper_bounds = [f * 1.1 for f in forecasts]
        else:
            # Linear trend
            dates = pd.to_datetime(series_df['date'])
            date_nums = (dates - dates.min()).dt.days
            
            # Simple linear regression
            coeffs = np.polyfit(date_nums, values, deg=1)
            trend_slope = coeffs[0]
            intercept = coeffs[1]
            
            # Forecast based on trend
            last_date_num = date_nums.iloc[-1]
            future_date_nums = [last_date_num + 30 * i for i in range(1, horizon_months + 1)]
            
            forecasts = [trend_slope * d + intercept for d in future_date_nums]
            
            # Add some uncertainty based on historical volatility
            volatility = values.std()
            lower_bounds = [f - 1.5 * volatility for f in forecasts]
            upper_bounds = [f + 1.5 * volatility for f in forecasts]
        
        return {
            'forecasts': forecasts,
            'lower_bounds': lower_bounds,
            'upper_bounds': upper_bounds
        }
    
    def fit(self, property_df: pd.DataFrame) -> 'NoiRentForecastPipeline':
        """Fit NOI and rent forecasting models"""
        logger.info("Starting NOI and rent forecast pipeline training")
        
        # Calculate market averages for fallback
        if 'market' in property_df.columns:
            for target_col in self.target_columns:
                if target_col in property_df.columns:
                    market_avgs = property_df.groupby('market')[target_col].mean().to_dict()
                    self.market_averages[target_col] = market_avgs
        
        # Get unique properties
        property_ids = property_df['property_id'].unique()
        logger.info(f"Training models for {len(property_ids)} properties")
        
        # Fit property-level models
        successful_fits = 0
        for prop_id in property_ids:
            logger.info(f"Processing property {prop_id}")
            
            prop_models = {}
            
            for target_col in self.target_columns:
                if target_col not in property_df.columns:
                    continue
                
                # Prepare series
                series_df = self._prepare_property_series(property_df, prop_id, target_col)
                if series_df is None:
                    continue
                
                # Fit Prophet model
                prophet_model = self._fit_prophet_property(
                    series_df, target_col, f"property_{prop_id}"
                )
                
                if prophet_model:
                    prop_models[target_col] = {
                        'type': 'prophet',
                        'model': prophet_model,
                        'last_value': series_df[target_col].iloc[-1],
                        'series_length': len(series_df)
                    }
                    successful_fits += 1
                else:
                    # Store trend info for fallback
                    prop_models[target_col] = {
                        'type': 'trend',
                        'last_value': series_df[target_col].iloc[-1],
                        'series_length': len(series_df),
                        'series_data': series_df  # Store for trend calculation
                    }
            
            if prop_models:
                self.property_models[prop_id] = prop_models
        
        # Fit market-level models for properties with insufficient data
        if 'market' in property_df.columns:
            markets = property_df['market'].unique()
            
            for market in markets:
                market_df = property_df[property_df['market'] == market]
                market_models = {}
                
                for target_col in self.target_columns:
                    if target_col not in market_df.columns:
                        continue
                    
                    # Aggregate to market level
                    market_series = market_df.groupby('date')[target_col].mean().reset_index()
                    
                    if len(market_series) >= MLConfig.MIN_TRAINING_SAMPLES:
                        market_model = self._fit_prophet_property(
                            market_series, target_col, f"market_{market}"
                        )
                        
                        if market_model:
                            market_models[target_col] = {
                                'type': 'prophet',
                                'model': market_model,
                                'last_value': market_series[target_col].iloc[-1]
                            }
                
                if market_models:
                    self.market_models[market] = market_models
        
        self.is_fitted = True
        logger.info(f"NOI/rent training completed. {successful_fits} successful Prophet fits, "
                   f"{len(self.property_models)} properties with models, "
                   f"{len(self.market_models)} market models")
        
        return self
    
    def predict(self, property_ids: List[str] = None,
                horizon_months: int = 6) -> Dict[str, Any]:
        """Generate NOI and rent forecasts"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        if property_ids is None:
            property_ids = list(self.property_models.keys())
        
        logger.info(f"Generating NOI/rent forecasts for {len(property_ids)} properties")
        
        results = {}
        
        # Generate future dates
        last_date = datetime.now().replace(day=1)
        future_dates = pd.date_range(
            start=last_date + timedelta(days=32),
            periods=horizon_months,
            freq='M'
        )
        
        for prop_id in property_ids:
            prop_result = {
                'property_id': prop_id,
                'dates': future_dates.tolist(),
                'forecasts': {},
                'model_info': {}
            }
            
            prop_models = self.property_models.get(prop_id, {})
            
            for target_col in self.target_columns:
                col_result = {
                    'forecasts': [],
                    'lower_bounds': [],
                    'upper_bounds': [],
                    'model_used': 'none'
                }
                
                if target_col in prop_models:
                    model_info = prop_models[target_col]
                    
                    if model_info['type'] == 'prophet':
                        try:
                            prophet_model = model_info['model']
                            future_df = pd.DataFrame({'ds': future_dates})
                            
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                forecast = prophet_model.predict(future_df)
                            
                            col_result['forecasts'] = forecast['yhat'].tolist()
                            col_result['lower_bounds'] = forecast['yhat_lower'].tolist()
                            col_result['upper_bounds'] = forecast['yhat_upper'].tolist()
                            col_result['model_used'] = 'prophet'
                            
                        except Exception as e:
                            logger.error(f"Prophet prediction failed for {prop_id} {target_col}: {e}")
                    
                    if col_result['model_used'] == 'none' and model_info['type'] == 'trend':
                        # Use trend-based forecast
                        trend_result = self._calculate_trend_forecast(
                            model_info['series_data'], target_col, horizon_months
                        )
                        col_result.update(trend_result)
                        col_result['model_used'] = 'trend'
                
                # Market-level fallback
                if col_result['model_used'] == 'none':
                    # Try to find market for this property (would need market info in predict)
                    # For now, use global average
                    base_value = self.market_averages.get(target_col, {}).get('default', 50000)
                    if target_col == 'rent':
                        base_value = 2500  # Default monthly rent
                    
                    growth_rate = 0.003  # 0.3% monthly growth
                    naive_forecasts = [base_value * (1 + growth_rate) ** i for i in range(1, horizon_months + 1)]
                    
                    col_result['forecasts'] = naive_forecasts
                    col_result['lower_bounds'] = [f * 0.85 for f in naive_forecasts]
                    col_result['upper_bounds'] = [f * 1.15 for f in naive_forecasts]
                    col_result['model_used'] = 'naive'
                
                prop_result['forecasts'][target_col] = col_result
                prop_result['model_info'][target_col] = {
                    'model_type': col_result['model_used'],
                    'last_value': prop_models.get(target_col, {}).get('last_value', 'unknown'),
                    'series_length': prop_models.get(target_col, {}).get('series_length', 0)
                }
            
            results[prop_id] = prop_result
        
        return results
    
    def save_models(self, version: str = None) -> str:
        """Save trained models"""
        if not self.is_fitted:
            raise ValueError("No fitted models to save")
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_dir = MODELS_PATH / self.model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save property models
        property_models_path = model_dir / "property_models.pkl"
        with open(property_models_path, 'wb') as f:
            joblib.dump(self.property_models, f)
        
        # Save market models
        market_models_path = model_dir / "market_models.pkl"
        with open(market_models_path, 'wb') as f:
            joblib.dump(self.market_models, f)
        
        # Save metadata
        metadata = {
            'model_name': self.model_name,
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'n_property_models': len(self.property_models),
            'n_market_models': len(self.market_models),
            'target_columns': self.target_columns,
            'market_averages': self.market_averages
        }
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            import json
            json.dump(metadata, f, indent=2)
        
        logger.info(f"NOI/rent models saved to {model_dir}")
        return str(model_dir)
    
    def load_models(self, version: str = "latest") -> 'NoiRentForecastPipeline':
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
                self.target_columns = metadata.get('target_columns', self.target_columns)
                self.market_averages = metadata.get('market_averages', {})
        
        # Load models
        property_models_path = model_dir / "property_models.pkl"
        if property_models_path.exists():
            with open(property_models_path, 'rb') as f:
                self.property_models = joblib.load(f)
        
        market_models_path = model_dir / "market_models.pkl"
        if market_models_path.exists():
            with open(market_models_path, 'rb') as f:
                self.market_models = joblib.load(f)
        
        self.is_fitted = True
        logger.info(f"NOI/rent models loaded from {model_dir}")
        return self
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about fitted models"""
        if not self.is_fitted:
            return {"status": "not_fitted"}
        
        # Count models by type
        prophet_count = 0
        trend_count = 0
        
        for prop_models in self.property_models.values():
            for model_info in prop_models.values():
                if model_info['type'] == 'prophet':
                    prophet_count += 1
                elif model_info['type'] == 'trend':
                    trend_count += 1
        
        info = {
            "status": "fitted",
            "model_name": self.model_name,
            "n_properties": len(self.property_models),
            "n_markets": len(self.market_models),
            "target_columns": self.target_columns,
            "prophet_models": prophet_count,
            "trend_models": trend_count,
            "market_averages": self.market_averages
        }
        
        return info

__all__ = ['NoiRentForecastPipeline']
