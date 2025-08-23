"""
Time utilities for ML forecasting
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

def get_date_ranges(start_date: datetime, end_date: datetime, 
                   freq: str = 'M') -> pd.DatetimeIndex:
    """Generate date range with specified frequency"""
    return pd.date_range(start=start_date, end=end_date, freq=freq)

def create_forecast_dates(last_date: datetime, 
                         horizon_months: int) -> pd.DatetimeIndex:
    """Create future dates for forecasting"""
    # Start from next month
    start_date = last_date.replace(day=1) + timedelta(days=32)
    start_date = start_date.replace(day=1)  # First of next month
    
    return pd.date_range(start=start_date, periods=horizon_months, freq='M')

def get_train_test_dates(df: pd.DataFrame, 
                        test_months: int = 6,
                        date_col: str = 'date') -> Tuple[datetime, datetime, datetime]:
    """Get train/test split dates"""
    df_sorted = df.sort_values(date_col)
    min_date = df_sorted[date_col].min()
    max_date = df_sorted[date_col].max()
    
    # Split date is test_months before max_date
    split_date = max_date - timedelta(days=test_months * 30)
    
    return min_date, split_date, max_date

def add_time_features(df: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
    """Add time-based features to dataframe"""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    
    df['year'] = df[date_col].dt.year
    df['month'] = df[date_col].dt.month
    df['quarter'] = df[date_col].dt.quarter
    df['day_of_year'] = df[date_col].dt.dayofyear
    df['week_of_year'] = df[date_col].dt.isocalendar().week
    
    return df

def get_months_between(start_date: datetime, end_date: datetime) -> int:
    """Calculate number of months between two dates"""
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
