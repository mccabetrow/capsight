"""
Feature Engineering for CapSight ML Pipeline
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
import logging

from .config import MLConfig
from .utils.seed import set_random_seed

logger = logging.getLogger(__name__)
set_random_seed(MLConfig.RANDOM_SEED)

class FeatureEngineer:
    """Feature engineering pipeline for real estate ML models"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.onehot_encoders = {}
        self.feature_names = []
        self.is_fitted = False
    
    def engineer_time_features(self, df: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
        """Add time-based features"""
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Time features
        df['year'] = df[date_col].dt.year
        df['month'] = df[date_col].dt.month
        df['quarter'] = df[date_col].dt.quarter
        df['day_of_year'] = df[date_col].dt.dayofyear
        
        # Cyclical encoding for month
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        return df
    
    def engineer_growth_features(self, df: pd.DataFrame, 
                                value_cols: List[str],
                                group_cols: List[str] = None,
                                windows: List[int] = None) -> pd.DataFrame:
        """Add growth rate features"""
        df = df.copy()
        if windows is None:
            windows = MLConfig.GROWTH_WINDOWS
        if group_cols is None:
            group_cols = ['property_id']
        
        for col in value_cols:
            if col not in df.columns:
                continue
                
            for window in windows:
                # Period-over-period growth
                if group_cols:
                    df[f'{col}_growth_{window}m'] = df.groupby(group_cols)[col].pct_change(periods=window)
                else:
                    df[f'{col}_growth_{window}m'] = df[col].pct_change(periods=window)
                
                # Year-over-year growth (if we have enough data)
                if window >= 12:
                    if group_cols:
                        df[f'{col}_yoy_growth'] = df.groupby(group_cols)[col].pct_change(periods=12)
                    else:
                        df[f'{col}_yoy_growth'] = df[col].pct_change(periods=12)
        
        return df
    
    def engineer_momentum_features(self, df: pd.DataFrame,
                                  value_cols: List[str],
                                  group_cols: List[str] = None,
                                  windows: List[int] = None) -> pd.DataFrame:
        """Add momentum features (rolling statistics)"""
        df = df.copy()
        if windows is None:
            windows = MLConfig.MOMENTUM_WINDOWS
        if group_cols is None:
            group_cols = ['property_id']
        
        for col in value_cols:
            if col not in df.columns:
                continue
                
            for window in windows:
                if group_cols:
                    grouped = df.groupby(group_cols)[col]
                else:
                    grouped = df[col]
                
                # Rolling mean
                df[f'{col}_ma_{window}m'] = grouped.rolling(window=window, min_periods=1).mean()
                
                # Rolling standard deviation
                df[f'{col}_std_{window}m'] = grouped.rolling(window=window, min_periods=1).std()
                
                # Rolling z-score (current vs rolling mean)
                rolling_mean = grouped.rolling(window=window, min_periods=1).mean()
                rolling_std = grouped.rolling(window=window, min_periods=1).std()
                df[f'{col}_zscore_{window}m'] = (df[col] - rolling_mean) / (rolling_std + 1e-8)
                
                # Momentum (current vs rolling mean)
                df[f'{col}_momentum_{window}m'] = (df[col] - rolling_mean) / (rolling_mean + 1e-8)
        
        return df
    
    def engineer_cap_rate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer cap rate specific features"""
        df = df.copy()
        
        # Calculate cap rate if we have NOI and price
        if 'noi' in df.columns and 'price' in df.columns:
            df['cap_rate_calculated'] = df['noi'] / (df['price'] + 1e-8)
            
            # Use observed cap rate if available, otherwise calculated
            if 'cap_rate_observed' not in df.columns:
                df['cap_rate_observed'] = df['cap_rate_calculated']
            else:
                df['cap_rate_observed'] = df['cap_rate_observed'].fillna(df['cap_rate_calculated'])
        
        # Cap rate spread vs market average
        if 'cap_rate_observed' in df.columns and 'market' in df.columns:
            market_avg = df.groupby('market')['cap_rate_observed'].transform('mean')
            df['cap_rate_vs_market'] = df['cap_rate_observed'] - market_avg
        
        # Cap rate percentile within market/asset type
        if 'cap_rate_observed' in df.columns:
            group_cols = ['market', 'asset_type'] if 'asset_type' in df.columns else ['market']
            df['cap_rate_percentile'] = df.groupby(group_cols)['cap_rate_observed'].rank(pct=True)
        
        return df
    
    def engineer_macro_features(self, property_df: pd.DataFrame, 
                              macro_df: pd.DataFrame) -> pd.DataFrame:
        """Join and engineer macro economic features"""
        property_df = property_df.copy()
        macro_df = macro_df.copy()
        
        # Ensure date columns are datetime
        property_df['date'] = pd.to_datetime(property_df['date'])
        macro_df['date'] = pd.to_datetime(macro_df['date'])
        
        # Join macro data
        df = property_df.merge(macro_df, on='date', how='left')
        
        # Forward fill missing macro data
        macro_cols = ['base_rate', 'mortgage_30y', 'corp_bbb_spread']
        for col in macro_cols:
            if col in df.columns:
                df[col] = df[col].fillna(method='ffill')
        
        # Engineer macro features
        if 'base_rate' in df.columns:
            df['base_rate_change_1m'] = df['base_rate'].diff()
            df['base_rate_change_3m'] = df['base_rate'].diff(periods=3)
            df['base_rate_change_12m'] = df['base_rate'].diff(periods=12)
        
        if 'mortgage_30y' in df.columns:
            df['mortgage_change_1m'] = df['mortgage_30y'].diff()
            df['mortgage_change_3m'] = df['mortgage_30y'].diff(periods=3)
            df['mortgage_change_12m'] = df['mortgage_30y'].diff(periods=12)
        
        if 'base_rate' in df.columns and 'mortgage_30y' in df.columns:
            df['rate_spread'] = df['mortgage_30y'] - df['base_rate']
            df['rate_spread_change'] = df['rate_spread'].diff()
        
        return df
    
    def encode_categorical_features(self, df: pd.DataFrame, 
                                  categorical_cols: List[str] = None,
                                  use_onehot: bool = True) -> pd.DataFrame:
        """Encode categorical features"""
        df = df.copy()
        
        if categorical_cols is None:
            categorical_cols = ['market', 'asset_type', 'state']
        
        # Filter to existing columns
        categorical_cols = [col for col in categorical_cols if col in df.columns]
        
        for col in categorical_cols:
            if use_onehot:
                # One-hot encoding
                if col not in self.onehot_encoders:
                    self.onehot_encoders[col] = OneHotEncoder(sparse_output=False, drop='first', handle_unknown='ignore')
                    encoded = self.onehot_encoders[col].fit_transform(df[[col]])
                else:
                    encoded = self.onehot_encoders[col].transform(df[[col]])
                
                # Create column names
                categories = self.onehot_encoders[col].categories_[0]
                if len(categories) > 1:  # Only if we have multiple categories
                    col_names = [f'{col}_{cat}' for cat in categories[1:]]  # Skip first (dropped)
                    encoded_df = pd.DataFrame(encoded, columns=col_names, index=df.index)
                    df = pd.concat([df, encoded_df], axis=1)
            else:
                # Label encoding
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df[col].astype(str))
                else:
                    df[f'{col}_encoded'] = self.label_encoders[col].transform(df[col].astype(str))
        
        return df
    
    def create_target_features(self, df: pd.DataFrame, 
                              horizon_months: int = 6) -> pd.DataFrame:
        """Create forward-looking target features for training"""
        df = df.copy()
        df = df.sort_values(['property_id', 'date'])
        
        # Forward returns
        if 'cap_rate_observed' in df.columns:
            df['cap_rate_future'] = df.groupby('property_id')['cap_rate_observed'].shift(-horizon_months)
            df['cap_rate_return'] = (df['cap_rate_future'] - df['cap_rate_observed']) / (df['cap_rate_observed'] + 1e-8)
        
        if 'noi' in df.columns:
            df['noi_future'] = df.groupby('property_id')['noi'].shift(-horizon_months)
            df['noi_return'] = (df['noi_future'] - df['noi']) / (df['noi'] + 1e-8)
        
        if 'rent' in df.columns:
            df['rent_future'] = df.groupby('property_id')['rent'].shift(-horizon_months)
            df['rent_return'] = (df['rent_future'] - df['rent']) / (df['rent'] + 1e-8)
        
        # Combined arbitrage signal (simplified)
        if all(col in df.columns for col in ['cap_rate_return', 'noi_return']):
            weights = MLConfig.SCORING_WEIGHTS
            df['arbitrage_signal'] = (
                weights['cap_rate_compression'] * (-df['cap_rate_return']) +  # Negative because lower cap rate is better
                weights['noi_growth'] * df['noi_return']
            )
        
        return df
    
    def fit_transform(self, df: pd.DataFrame, 
                     macro_df: Optional[pd.DataFrame] = None,
                     target_horizon: int = 6) -> pd.DataFrame:
        """Fit feature engineering pipeline and transform data"""
        logger.info(f"Starting feature engineering for {len(df)} records")
        
        # Make a copy to avoid modifying input
        df_processed = df.copy()
        
        # Time features
        df_processed = self.engineer_time_features(df_processed)
        
        # Growth features
        value_cols = ['noi', 'rent', 'occupancy', 'cap_rate_observed']
        df_processed = self.engineer_growth_features(df_processed, value_cols)
        
        # Momentum features
        df_processed = self.engineer_momentum_features(df_processed, value_cols)
        
        # Cap rate specific features
        df_processed = self.engineer_cap_rate_features(df_processed)
        
        # Macro features
        if macro_df is not None:
            df_processed = self.engineer_macro_features(df_processed, macro_df)
        
        # Categorical encoding
        df_processed = self.encode_categorical_features(df_processed)
        
        # Target features (for training)
        df_processed = self.create_target_features(df_processed, target_horizon)
        
        # Store feature names
        self.feature_names = df_processed.columns.tolist()
        self.is_fitted = True
        
        logger.info(f"Feature engineering complete. Generated {len(df_processed.columns)} features")
        
        return df_processed
    
    def transform(self, df: pd.DataFrame, 
                  macro_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Transform data using fitted pipeline (for inference)"""
        if not self.is_fitted:
            raise ValueError("FeatureEngineer must be fitted before transform")
        
        # Same processing as fit_transform but without creating targets
        df_processed = df.copy()
        
        df_processed = self.engineer_time_features(df_processed)
        
        value_cols = ['noi', 'rent', 'occupancy', 'cap_rate_observed']
        df_processed = self.engineer_growth_features(df_processed, value_cols)
        df_processed = self.engineer_momentum_features(df_processed, value_cols)
        df_processed = self.engineer_cap_rate_features(df_processed)
        
        if macro_df is not None:
            df_processed = self.engineer_macro_features(df_processed, macro_df)
        
        df_processed = self.encode_categorical_features(df_processed)
        
        return df_processed
    
    def get_feature_importance_names(self) -> List[str]:
        """Get meaningful names for feature importance plotting"""
        feature_mappings = {
            '_growth_': ' Growth ',
            '_momentum_': ' Momentum ',
            '_zscore_': ' Z-Score ',
            '_ma_': ' Moving Avg ',
            '_std_': ' Std Dev ',
            'cap_rate': 'Cap Rate',
            'noi': 'NOI',
            'rent': 'Rent',
            'occupancy': 'Occupancy',
            'base_rate': 'Base Rate',
            'mortgage': 'Mortgage Rate',
            '_1m': ' (1M)',
            '_3m': ' (3M)',
            '_6m': ' (6M)',
            '_12m': ' (12M)',
            '_change_': ' Change '
        }
        
        readable_names = []
        for name in self.feature_names:
            readable = name
            for old, new in feature_mappings.items():
                readable = readable.replace(old, new)
            readable_names.append(readable.title())
        
        return readable_names

def create_feature_matrix(df: pd.DataFrame, 
                         feature_cols: List[str] = None,
                         fill_na: str = 'median') -> Tuple[np.ndarray, List[str]]:
    """Create clean feature matrix for ML models"""
    if feature_cols is None:
        # Exclude non-feature columns
        exclude_cols = ['property_id', 'date', 'id', 'created_at', 'updated_at']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    # Select features
    X = df[feature_cols].copy()
    
    # Handle missing values
    if fill_na == 'median':
        X = X.fillna(X.median())
    elif fill_na == 'mean':
        X = X.fillna(X.mean())
    elif fill_na == 'zero':
        X = X.fillna(0)
    else:
        X = X.fillna(0)  # Default fallback
    
    # Replace inf with large finite values
    X = X.replace([np.inf, -np.inf], [1e10, -1e10])
    
    return X.values, feature_cols

__all__ = [
    'FeatureEngineer',
    'create_feature_matrix'
]
