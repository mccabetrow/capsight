"""
Dataset loading and synthetic data generation for CapSight ML
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import random
import json
import logging
from pathlib import Path

from .config import MLConfig, ARTIFACTS_PATH
from .utils.seed import set_random_seed

logger = logging.getLogger(__name__)
set_random_seed(MLConfig.RANDOM_SEED)

class SyntheticDataGenerator:
    """Generate realistic synthetic real estate data for training and testing"""
    
    def __init__(self):
        self.markets = MLConfig.MARKETS
        self.asset_types = MLConfig.ASSET_TYPES
        
        # Market characteristics (growth rates, volatility, base values)
        self.market_params = {
            'austin': {'growth': 0.08, 'volatility': 0.15, 'base_cap_rate': 0.055},
            'dallas': {'growth': 0.06, 'volatility': 0.12, 'base_cap_rate': 0.065},
            'houston': {'growth': 0.05, 'volatility': 0.14, 'base_cap_rate': 0.070},
            'san_antonio': {'growth': 0.04, 'volatility': 0.11, 'base_cap_rate': 0.075},
            'denver': {'growth': 0.07, 'volatility': 0.16, 'base_cap_rate': 0.050},
            'phoenix': {'growth': 0.06, 'volatility': 0.13, 'base_cap_rate': 0.060},
            'atlanta': {'growth': 0.05, 'volatility': 0.12, 'base_cap_rate': 0.065},
            'nashville': {'growth': 0.09, 'volatility': 0.17, 'base_cap_rate': 0.055},
            'tampa': {'growth': 0.07, 'volatility': 0.14, 'base_cap_rate': 0.060},
            'miami': {'growth': 0.06, 'volatility': 0.18, 'base_cap_rate': 0.050}
        }
        
        # Asset type multipliers
        self.asset_multipliers = {
            'single_family': {'cap_rate': 1.0, 'volatility': 1.0, 'noi_base': 24000},
            'multi_family': {'cap_rate': 0.9, 'volatility': 0.8, 'noi_base': 120000},
            'commercial': {'cap_rate': 0.85, 'volatility': 0.7, 'noi_base': 250000}
        }
    
    def generate_macro_series(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate synthetic macro economic time series"""
        date_range = pd.date_range(start=start_date, end=end_date, freq='M')
        n_periods = len(date_range)
        
        # Base rates with trend and noise
        base_rate_trend = np.linspace(0.025, 0.045, n_periods)  # 2.5% to 4.5%
        base_rate_noise = np.random.normal(0, 0.003, n_periods)
        base_rate = base_rate_trend + base_rate_noise
        base_rate = np.clip(base_rate, 0.01, 0.08)  # Reasonable bounds
        
        # Mortgage rates (typically higher than base rate)
        mortgage_spread = np.random.normal(0.015, 0.002, n_periods)  # ~150bps spread
        mortgage_30y = base_rate + mortgage_spread
        mortgage_30y = np.clip(mortgage_30y, 0.02, 0.12)
        
        # Corporate BBB spread
        corp_spread_base = 0.02  # 200bps base
        corp_spread_volatility = np.random.normal(0, 0.003, n_periods)
        corp_bbb_spread = corp_spread_base + corp_spread_volatility
        corp_bbb_spread = np.clip(corp_bbb_spread, 0.01, 0.05)
        
        macro_df = pd.DataFrame({
            'date': date_range,
            'base_rate': base_rate,
            'mortgage_30y': mortgage_30y,
            'corp_bbb_spread': corp_bbb_spread
        })
        
        # Add some autocorrelation to make it more realistic
        for col in ['base_rate', 'mortgage_30y', 'corp_bbb_spread']:
            for i in range(1, len(macro_df)):
                # Add autocorrelation (previous period influence)
                autocorr = 0.7
                macro_df.loc[i, col] = (
                    autocorr * macro_df.loc[i-1, col] + 
                    (1 - autocorr) * macro_df.loc[i, col]
                )
        
        return macro_df
    
    def generate_property_series(self, property_ids: List[str], 
                               markets: List[str], asset_types: List[str],
                               start_date: datetime, end_date: datetime,
                               macro_df: pd.DataFrame) -> pd.DataFrame:
        """Generate synthetic property time series data"""
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='M')
        n_periods = len(date_range)
        
        property_data = []
        
        for prop_id in property_ids:
            # Assign random market and asset type
            market = random.choice(markets)
            asset_type = random.choice(asset_types)
            state = self._get_state_for_market(market)
            
            # Get market parameters
            market_params = self.market_params[market]
            asset_params = self.asset_multipliers[asset_type]
            
            # Base values
            base_noi = asset_params['noi_base'] * random.uniform(0.7, 1.3)
            base_cap_rate = market_params['base_cap_rate'] * asset_params['cap_rate']
            base_rent = base_noi / 12  # Monthly rent approximation
            base_occupancy = random.uniform(0.85, 0.98)
            
            # Generate time series with trends and seasonality
            noi_series = []
            rent_series = []
            occupancy_series = []
            cap_rate_series = []
            
            for i, date in enumerate(date_range):
                # Growth trend
                time_factor = i / 12  # Years
                growth_factor = (1 + market_params['growth']) ** time_factor
                
                # Seasonal effects (peak in summer months)
                seasonal_factor = 1 + 0.05 * np.sin(2 * np.pi * (date.month - 6) / 12)
                
                # Macro economic effects (from rates)
                macro_date = macro_df[macro_df['date'] <= date].iloc[-1] if len(macro_df[macro_df['date'] <= date]) > 0 else macro_df.iloc[0]
                rate_effect = 1 - 0.5 * (macro_date['base_rate'] - 0.03)  # Lower rates boost valuations
                
                # Random noise
                noise_factor = 1 + np.random.normal(0, market_params['volatility'] * asset_params['volatility'] / 4)
                
                # Calculate values
                noi = base_noi * growth_factor * seasonal_factor * rate_effect * noise_factor
                rent = base_rent * growth_factor * seasonal_factor * noise_factor
                occupancy = np.clip(base_occupancy * (1 + np.random.normal(0, 0.05)), 0.6, 1.0)
                
                # Cap rate inversely related to growth and rates
                cap_rate_base_adj = base_cap_rate * (1 + 0.3 * (macro_date['base_rate'] - 0.03))
                cap_rate = cap_rate_base_adj / growth_factor * (1 + np.random.normal(0, 0.1))
                cap_rate = np.clip(cap_rate, 0.03, 0.12)
                
                noi_series.append(noi)
                rent_series.append(rent)
                occupancy_series.append(occupancy)
                cap_rate_series.append(cap_rate)
            
            # Create property dataframe
            prop_df = pd.DataFrame({
                'property_id': prop_id,
                'date': date_range,
                'market': market,
                'state': state,
                'asset_type': asset_type,
                'noi': noi_series,
                'rent': rent_series,
                'occupancy': occupancy_series,
                'cap_rate_observed': cap_rate_series
            })
            
            # Calculate price based on NOI and cap rate
            prop_df['price'] = prop_df['noi'] / prop_df['cap_rate_observed']
            
            property_data.append(prop_df)
        
        # Combine all properties
        combined_df = pd.concat(property_data, ignore_index=True)
        
        logger.info(f"Generated property series for {len(property_ids)} properties, {n_periods} periods each")
        
        return combined_df
    
    def _get_state_for_market(self, market: str) -> str:
        """Map market to state"""
        market_to_state = {
            'austin': 'TX', 'dallas': 'TX', 'houston': 'TX', 'san_antonio': 'TX',
            'denver': 'CO', 'phoenix': 'AZ', 'atlanta': 'GA', 'nashville': 'TN',
            'tampa': 'FL', 'miami': 'FL'
        }
        return market_to_state.get(market, 'TX')
    
    def generate_full_dataset(self, n_properties: int = 20, 
                            months_back: int = 36,
                            markets: Optional[List[str]] = None,
                            asset_types: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate complete synthetic dataset"""
        
        if markets is None:
            markets = self.markets[:5]  # Use subset for demo
        if asset_types is None:
            asset_types = self.asset_types
        
        # Date range
        end_date = datetime.now().replace(day=1)  # First of current month
        start_date = end_date - timedelta(days=months_back * 30)
        
        # Generate property IDs
        property_ids = [f"prop_{i:04d}" for i in range(1, n_properties + 1)]
        
        # Generate macro data
        macro_df = self.generate_macro_series(start_date, end_date)
        
        # Generate property data
        property_df = self.generate_property_series(
            property_ids, markets, asset_types, start_date, end_date, macro_df
        )
        
        return property_df, macro_df
    
    def save_sample_macro_csv(self, filepath: Optional[str] = None):
        """Save sample macro data CSV for reference"""
        if filepath is None:
            filepath = ARTIFACTS_PATH / "macro_sample.csv"
        
        # Generate 5 years of data
        end_date = datetime.now().replace(day=1)
        start_date = end_date - timedelta(days=5 * 365)
        
        macro_df = self.generate_macro_series(start_date, end_date)
        macro_df.to_csv(filepath, index=False)
        
        logger.info(f"Saved sample macro data to {filepath}")
        
        return macro_df

class DatasetLoader:
    """Load real or synthetic datasets for ML pipeline"""
    
    def __init__(self):
        self.synthetic_generator = SyntheticDataGenerator()
    
    def load_property_series(self, source: str = 'synthetic', **kwargs) -> pd.DataFrame:
        """Load property time series data"""
        if source == 'synthetic':
            property_df, _ = self.synthetic_generator.generate_full_dataset(**kwargs)
            return property_df
        elif source == 'database':
            # In real implementation, this would query the database
            # For now, return synthetic data
            logger.warning("Database loading not implemented, using synthetic data")
            return self.load_property_series('synthetic', **kwargs)
        else:
            raise ValueError(f"Unknown data source: {source}")
    
    def load_macro_series(self, source: str = 'synthetic', 
                         filepath: Optional[str] = None) -> pd.DataFrame:
        """Load macro economic time series data"""
        if source == 'synthetic':
            _, macro_df = self.synthetic_generator.generate_full_dataset()
            return macro_df
        elif source == 'csv' and filepath:
            try:
                macro_df = pd.read_csv(filepath)
                macro_df['date'] = pd.to_datetime(macro_df['date'])
                return macro_df
            except Exception as e:
                logger.warning(f"Failed to load CSV {filepath}: {e}, using synthetic data")
                return self.load_macro_series('synthetic')
        else:
            # Try to load sample CSV
            sample_path = ARTIFACTS_PATH / "macro_sample.csv"
            if sample_path.exists():
                return self.load_macro_series('csv', str(sample_path))
            else:
                # Generate and save sample
                self.synthetic_generator.save_sample_macro_csv()
                return self.load_macro_series('csv', str(sample_path))
    
    def create_train_test_split(self, df: pd.DataFrame, 
                              test_months: int = 6,
                              date_col: str = 'date') -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create time-based train/test split"""
        df = df.sort_values(date_col)
        
        # Find split date
        max_date = df[date_col].max()
        split_date = max_date - timedelta(days=test_months * 30)
        
        train_df = df[df[date_col] <= split_date].copy()
        test_df = df[df[date_col] > split_date].copy()
        
        logger.info(f"Train/test split: {len(train_df)} train, {len(test_df)} test samples")
        logger.info(f"Split date: {split_date}")
        
        return train_df, test_df
    
    def get_latest_data(self, months_back: int = 12) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get most recent data for inference"""
        end_date = datetime.now().replace(day=1)
        start_date = end_date - timedelta(days=months_back * 30)
        
        # For now, generate synthetic data
        # In production, this would query the database for recent records
        property_df, macro_df = self.synthetic_generator.generate_full_dataset(
            months_back=months_back
        )
        
        # Filter to recent data
        property_df = property_df[property_df['date'] >= start_date]
        macro_df = macro_df[macro_df['date'] >= start_date]
        
        return property_df, macro_df

# Utility functions
def load_demo_dataset(n_properties: int = 15, months_back: int = 24) -> Dict[str, pd.DataFrame]:
    """Load complete demo dataset for training and testing"""
    generator = SyntheticDataGenerator()
    
    property_df, macro_df = generator.generate_full_dataset(
        n_properties=n_properties,
        months_back=months_back
    )
    
    # Save sample macro CSV
    generator.save_sample_macro_csv()
    
    return {
        'property_series': property_df,
        'macro_series': macro_df
    }

def create_forecast_targets(df: pd.DataFrame, 
                          target_col: str,
                          horizon_months: List[int] = [3, 6, 12]) -> pd.DataFrame:
    """Create forward-looking target variables for different horizons"""
    df = df.copy()
    df = df.sort_values(['property_id', 'date'])
    
    for horizon in horizon_months:
        target_name = f'{target_col}_target_{horizon}m'
        df[target_name] = df.groupby('property_id')[target_col].shift(-horizon)
    
    return df

__all__ = [
    'SyntheticDataGenerator',
    'DatasetLoader', 
    'load_demo_dataset',
    'create_forecast_targets'
]
