"""
Interest Rates and Financing Rates Forecasting Pipeline
Uses Prophet and ARIMA for macro economic rate predictions
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
    warnings.warn("Prophet not available, using ARIMA only")

# ARIMA import
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.stattools import adfuller
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    warnings.warn("statsmodels not available, using naive forecasts")

from ..config import MLConfig, MODELS_PATH
from ..utils.seed import set_random_seed

logger = logging.getLogger(__name__)
set_random_seed(MLConfig.RANDOM_SEED)

class RatesForecastPipeline:
    """Forecast interest rates and financing costs"""
    
    def __init__(self, model_name: str = "rates_forecast"):
        self.model_name = model_name
        self.prophet_models = {}
        self.arima_models = {}
        self.is_fitted = False
        self.feature_columns = ['base_rate', 'mortgage_30y', 'corp_bbb_spread']
        self.forecast_cache = {}
        
    def _check_stationarity(self, series: pd.Series, alpha: float = 0.05) -> bool:
        """Check if time series is stationary using ADF test"""
        if not ARIMA_AVAILABLE:
            return True  # Assume stationary if can't test
            
        try:
            result = adfuller(series.dropna())
            return result[1] <= alpha  # p-value <= alpha means stationary
        except:
            return True  # Default to stationary if test fails
    
    def _make_stationary(self, series: pd.Series) -> Tuple[pd.Series, int]:
        """Make time series stationary through differencing"""
        if not ARIMA_AVAILABLE:
            return series, 0
            
        original_series = series.copy()
        diff_order = 0
        
        # Check original series
        if self._check_stationarity(series):
            return series, diff_order
        
        # Try first differencing
        series_diff = series.diff().dropna()
        if len(series_diff) > 10 and self._check_stationarity(series_diff):
            return series_diff, 1
        
        # Try second differencing
        series_diff2 = series_diff.diff().dropna()
        if len(series_diff2) > 10 and self._check_stationarity(series_diff2):
            return series_diff2, 2
        
        # If still not stationary, use second difference anyway
        return series_diff2 if len(series_diff2) > 5 else original_series, min(2, diff_order)
    
    def _fit_prophet_model(self, df: pd.DataFrame, target_col: str) -> Prophet:
        """Fit Prophet model for a single rate series"""
        if not PROPHET_AVAILABLE:
            return None
            
        # Prepare data for Prophet
        prophet_df = df[['date', target_col]].rename(columns={
            'date': 'ds', 
            target_col: 'y'
        }).dropna()
        
        if len(prophet_df) < MLConfig.MIN_TRAINING_SAMPLES:
            logger.warning(f"Insufficient data for {target_col} Prophet model: {len(prophet_df)} samples")
            return None
        
        try:
            # Configure Prophet model
            model = Prophet(
                changepoint_prior_scale=MLConfig.PROPHET_CHANGEPOINT_PRIOR,
                seasonality_prior_scale=MLConfig.PROPHET_SEASONALITY_PRIOR,
                holidays_prior_scale=MLConfig.PROPHET_HOLIDAYS_PRIOR,
                seasonality_mode=MLConfig.PROPHET_SEASONALITY_MODE,
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.80  # 80% confidence intervals
            )
            
            # Fit model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(prophet_df)
            
            logger.info(f"Prophet model fitted for {target_col}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to fit Prophet model for {target_col}: {e}")
            return None
    
    def _fit_arima_model(self, series: pd.Series, target_col: str) -> Dict:
        """Fit ARIMA model for a single rate series"""
        if not ARIMA_AVAILABLE:
            return None
            
        series_clean = series.dropna()
        if len(series_clean) < MLConfig.MIN_TRAINING_SAMPLES:
            logger.warning(f"Insufficient data for {target_col} ARIMA model: {len(series_clean)} samples")
            return None
        
        try:
            # Make series stationary
            stationary_series, diff_order = self._make_stationary(series_clean)
            
            # Auto-select ARIMA parameters (simple grid search)
            best_aic = float('inf')
            best_params = (1, diff_order, 1)
            
            for p in range(0, min(MLConfig.ARIMA_MAX_P + 1, 4)):
                for q in range(0, min(MLConfig.ARIMA_MAX_Q + 1, 4)):
                    try:
                        model = ARIMA(series_clean, order=(p, diff_order, q))
                        fitted_model = model.fit()
                        if fitted_model.aic < best_aic:
                            best_aic = fitted_model.aic
                            best_params = (p, diff_order, q)
                    except:
                        continue
            
            # Fit final model with best parameters
            final_model = ARIMA(series_clean, order=best_params)
            fitted_final = final_model.fit()
            
            logger.info(f"ARIMA{best_params} model fitted for {target_col}, AIC: {best_aic:.2f}")
            
            return {
                'model': fitted_final,
                'order': best_params,
                'aic': best_aic
            }
            
        except Exception as e:
            logger.error(f"Failed to fit ARIMA model for {target_col}: {e}")
            return None
    
    def fit(self, macro_df: pd.DataFrame) -> 'RatesForecastPipeline':
        """Fit rate forecasting models"""
        logger.info("Starting rates forecast pipeline training")
        
        # Ensure date column
        macro_df = macro_df.copy()
        macro_df['date'] = pd.to_datetime(macro_df['date'])
        macro_df = macro_df.sort_values('date')
        
        # Fit models for each rate type
        for target_col in self.feature_columns:
            if target_col not in macro_df.columns:
                logger.warning(f"Column {target_col} not found in data")
                continue
            
            logger.info(f"Fitting models for {target_col}")
            
            # Fit Prophet model
            if PROPHET_AVAILABLE:
                prophet_model = self._fit_prophet_model(macro_df, target_col)
                if prophet_model:
                    self.prophet_models[target_col] = prophet_model
            
            # Fit ARIMA model
            if ARIMA_AVAILABLE:
                arima_result = self._fit_arima_model(macro_df[target_col], target_col)
                if arima_result:
                    self.arima_models[target_col] = arima_result
        
        self.is_fitted = True
        logger.info("Rates forecast pipeline training completed")
        
        return self
    
    def predict(self, horizon_months: int = 6) -> Dict[str, Any]:
        """Generate rate forecasts"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        logger.info(f"Generating rate forecasts for {horizon_months} months")
        
        results = {}
        
        # Generate future dates
        last_date = datetime.now().replace(day=1)  # First of current month
        future_dates = pd.date_range(
            start=last_date + timedelta(days=32),  # Next month
            periods=horizon_months,
            freq='M'
        )
        
        for target_col in self.feature_columns:
            col_results = {
                'dates': future_dates.tolist(),
                'forecasts': [],
                'lower_bounds': [],
                'upper_bounds': [],
                'model_used': 'none'
            }
            
            # Try Prophet first
            if target_col in self.prophet_models:
                try:
                    prophet_model = self.prophet_models[target_col]
                    
                    # Create future dataframe
                    future_df = pd.DataFrame({'ds': future_dates})
                    
                    # Generate forecast
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        forecast = prophet_model.predict(future_df)
                    
                    col_results['forecasts'] = forecast['yhat'].tolist()
                    col_results['lower_bounds'] = forecast['yhat_lower'].tolist()
                    col_results['upper_bounds'] = forecast['yhat_upper'].tolist()
                    col_results['model_used'] = 'prophet'
                    
                    logger.info(f"Prophet forecast generated for {target_col}")
                    
                except Exception as e:
                    logger.error(f"Prophet prediction failed for {target_col}: {e}")
            
            # Fallback to ARIMA if Prophet failed or unavailable
            if col_results['model_used'] == 'none' and target_col in self.arima_models:
                try:
                    arima_result = self.arima_models[target_col]
                    arima_model = arima_result['model']
                    
                    # Generate forecast
                    forecast_result = arima_model.forecast(steps=horizon_months, alpha=0.2)  # 80% CI
                    forecasts = forecast_result
                    
                    # Get confidence intervals
                    conf_int = arima_model.get_forecast(steps=horizon_months, alpha=0.2).conf_int()
                    
                    col_results['forecasts'] = forecasts.tolist() if hasattr(forecasts, 'tolist') else [float(forecasts)]
                    col_results['lower_bounds'] = conf_int.iloc[:, 0].tolist() if hasattr(conf_int, 'iloc') else [float(forecasts) * 0.95]
                    col_results['upper_bounds'] = conf_int.iloc[:, 1].tolist() if hasattr(conf_int, 'iloc') else [float(forecasts) * 1.05]
                    col_results['model_used'] = 'arima'
                    
                    logger.info(f"ARIMA forecast generated for {target_col}")
                    
                except Exception as e:
                    logger.error(f"ARIMA prediction failed for {target_col}: {e}")
            
            # Final fallback: naive forecast (last value with trend)
            if col_results['model_used'] == 'none':
                # This would require historical data - for now, use reasonable defaults
                base_values = {
                    'base_rate': 0.035,
                    'mortgage_30y': 0.050,
                    'corp_bbb_spread': 0.025
                }
                
                base_value = base_values.get(target_col, 0.04)
                trend = 0.001  # Small upward trend per month
                
                naive_forecasts = [base_value + trend * i for i in range(1, horizon_months + 1)]
                
                col_results['forecasts'] = naive_forecasts
                col_results['lower_bounds'] = [f * 0.9 for f in naive_forecasts]
                col_results['upper_bounds'] = [f * 1.1 for f in naive_forecasts]
                col_results['model_used'] = 'naive'
                
                logger.warning(f"Using naive forecast for {target_col}")
            
            results[target_col] = col_results
        
        # Cache results
        cache_key = f"rates_forecast_{horizon_months}m_{datetime.now().strftime('%Y%m%d')}"
        self.forecast_cache[cache_key] = results
        
        return results
    
    def save_models(self, version: str = None) -> str:
        """Save trained models"""
        if not self.is_fitted:
            raise ValueError("No fitted models to save")
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_dir = MODELS_PATH / self.model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Prophet models
        for col, model in self.prophet_models.items():
            prophet_path = model_dir / f"prophet_{col}.pkl"
            with open(prophet_path, 'wb') as f:
                joblib.dump(model, f)
        
        # Save ARIMA models
        for col, model_data in self.arima_models.items():
            arima_path = model_dir / f"arima_{col}.pkl"
            with open(arima_path, 'wb') as f:
                joblib.dump(model_data, f)
        
        # Save metadata
        metadata = {
            'model_name': self.model_name,
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'feature_columns': self.feature_columns,
            'prophet_models': list(self.prophet_models.keys()),
            'arima_models': list(self.arima_models.keys())
        }
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            import json
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Rates forecast models saved to {model_dir}")
        
        return str(model_dir)
    
    def load_models(self, version: str = "latest") -> 'RatesForecastPipeline':
        """Load trained models"""
        if version == "latest":
            # Find latest version
            model_base_dir = MODELS_PATH / self.model_name
            if not model_base_dir.exists():
                raise FileNotFoundError(f"No models found for {self.model_name}")
            
            versions = [d.name for d in model_base_dir.iterdir() if d.is_dir()]
            if not versions:
                raise FileNotFoundError(f"No model versions found for {self.model_name}")
            
            version = sorted(versions)[-1]  # Latest by name
        
        model_dir = MODELS_PATH / self.model_name / version
        if not model_dir.exists():
            raise FileNotFoundError(f"Model version {version} not found")
        
        # Load metadata
        metadata_path = model_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                import json
                metadata = json.load(f)
                self.feature_columns = metadata.get('feature_columns', self.feature_columns)
        
        # Load Prophet models
        for col in self.feature_columns:
            prophet_path = model_dir / f"prophet_{col}.pkl"
            if prophet_path.exists():
                with open(prophet_path, 'rb') as f:
                    self.prophet_models[col] = joblib.load(f)
        
        # Load ARIMA models
        for col in self.feature_columns:
            arima_path = model_dir / f"arima_{col}.pkl"
            if arima_path.exists():
                with open(arima_path, 'rb') as f:
                    self.arima_models[col] = joblib.load(f)
        
        self.is_fitted = True
        logger.info(f"Rates forecast models loaded from {model_dir}")
        
        return self
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about fitted models"""
        if not self.is_fitted:
            return {"status": "not_fitted"}
        
        info = {
            "status": "fitted",
            "model_name": self.model_name,
            "feature_columns": self.feature_columns,
            "prophet_models": list(self.prophet_models.keys()),
            "arima_models": list(self.arima_models.keys()),
            "prophet_available": PROPHET_AVAILABLE,
            "arima_available": ARIMA_AVAILABLE
        }
        
        # Add ARIMA model details
        for col, model_data in self.arima_models.items():
            info[f"{col}_arima_order"] = model_data.get('order', 'unknown')
            info[f"{col}_arima_aic"] = model_data.get('aic', 'unknown')
        
        return info

__all__ = ['RatesForecastPipeline']
