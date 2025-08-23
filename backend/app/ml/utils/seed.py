"""
Random seed utilities for reproducible ML experiments
"""

import random
import numpy as np
import os
from typing import Optional

def set_random_seed(seed: int = 42):
    """Set random seed for reproducible results"""
    # Python random
    random.seed(seed)
    
    # NumPy random
    np.random.seed(seed)
    
    # Environment variable for other libraries
    os.environ['PYTHONHASHSEED'] = str(seed)
    
    # Try to set seeds for ML libraries if available
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
    except ImportError:
        pass
    
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass

def get_random_state(seed: Optional[int] = None) -> np.random.RandomState:
    """Get a RandomState instance with optional seed"""
    return np.random.RandomState(seed)

# Set default seed on import
set_random_seed(42)
