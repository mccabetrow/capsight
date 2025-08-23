"""
ML Configuration and Settings
"""

import os
from typing import Dict, List, Any
from pathlib import Path

# Base paths
ML_BASE_PATH = Path(__file__).parent
ARTIFACTS_PATH = ML_BASE_PATH / "artifacts"
MODELS_PATH = ARTIFACTS_PATH / "models"
PLOTS_PATH = ARTIFACTS_PATH / "plots"
METRICS_PATH = ARTIFACTS_PATH / "metrics"

# Create directories
for path in [ARTIFACTS_PATH, MODELS_PATH, PLOTS_PATH, METRICS_PATH]:
    path.mkdir(parents=True, exist_ok=True)

# Global ML Settings
class MLConfig:
    # Random seed for reproducibility
    RANDOM_SEED = 42
    
    # Forecasting horizons (months)
    DEFAULT_HORIZON = 6
    MIN_HORIZON = 3
    MAX_HORIZON = 24
    
    # Data requirements
    MIN_SERIES_LENGTH = 6  # months
    MIN_TRAINING_SAMPLES = 12
    
    # Model thresholds
    CONFIDENCE_THRESHOLD = 0.7
    SCORE_SCALE = 100  # 0-100 scale
    
    # Prophet settings
    PROPHET_CHANGEPOINT_PRIOR = 0.05
    PROPHET_SEASONALITY_PRIOR = 10.0
    PROPHET_HOLIDAYS_PRIOR = 10.0
    PROPHET_SEASONALITY_MODE = 'additive'
    
    # XGBoost settings
    XGBOOST_N_ESTIMATORS = 100
    XGBOOST_MAX_DEPTH = 6
    XGBOOST_LEARNING_RATE = 0.1
    XGBOOST_RANDOM_STATE = RANDOM_SEED
    
    # ARIMA settings
    ARIMA_MAX_P = 3
    ARIMA_MAX_D = 2
    ARIMA_MAX_Q = 3
    
    # Scoring weights
    SCORING_WEIGHTS = {
        'cap_rate_compression': 0.4,
        'noi_growth': 0.3,
        'rate_environment': 0.2,
        'momentum': 0.1
    }
    
    # Markets and asset types
    MARKETS = ['austin', 'dallas', 'houston', 'san_antonio', 'denver', 'phoenix', 'atlanta', 'nashville', 'tampa', 'miami']
    ASSET_TYPES = ['single_family', 'multi_family', 'commercial']
    
    # Feature engineering
    MOMENTUM_WINDOWS = [3, 6, 12]  # months
    GROWTH_WINDOWS = [1, 3, 12]   # months for growth calculations
    
    # API settings
    BATCH_SIZE = 1000
    MAX_CONCURRENT_FORECASTS = 10
    CACHE_TTL_SECONDS = 3600  # 1 hour
    
    # Database table names
    FORECAST_TABLE = 'forecasts'
    OPPORTUNITY_TABLE = 'opportunities'
    PROPERTY_SERIES_TABLE = 'property_series'
    MACRO_SERIES_TABLE = 'macro_series'

# Environment overrides
def load_env_overrides():
    """Load configuration overrides from environment variables"""
    env_overrides = {}
    
    if os.getenv('ML_RANDOM_SEED'):
        env_overrides['RANDOM_SEED'] = int(os.getenv('ML_RANDOM_SEED'))
    
    if os.getenv('ML_DEFAULT_HORIZON'):
        env_overrides['DEFAULT_HORIZON'] = int(os.getenv('ML_DEFAULT_HORIZON'))
    
    if os.getenv('ML_CONFIDENCE_THRESHOLD'):
        env_overrides['CONFIDENCE_THRESHOLD'] = float(os.getenv('ML_CONFIDENCE_THRESHOLD'))
    
    return env_overrides

# Apply environment overrides
_env_overrides = load_env_overrides()
for key, value in _env_overrides.items():
    if hasattr(MLConfig, key):
        setattr(MLConfig, key, value)

# Export paths for easy import
__all__ = [
    'MLConfig',
    'ML_BASE_PATH',
    'ARTIFACTS_PATH',
    'MODELS_PATH', 
    'PLOTS_PATH',
    'METRICS_PATH'
]
