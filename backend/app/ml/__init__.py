"""
CapSight ML Module
Production-ready machine learning pipeline for real estate arbitrage prediction
"""

__version__ = "1.0.0"
__author__ = "CapSight ML Team"

# Global ML configuration
ML_CONFIG = {
    "random_seed": 42,
    "default_horizon_months": 6,
    "min_series_length": 6,
    "confidence_threshold": 0.7,
    "batch_size": 1000,
    "model_version": "v1.0"
}

def get_version():
    """Return current ML module version"""
    return __version__

def get_config():
    """Return ML configuration dict"""
    return ML_CONFIG.copy()
