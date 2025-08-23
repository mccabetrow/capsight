"""
Time slicing and as-of date logic for backtesting
Ensures no look-ahead bias in historical predictions
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import hashlib
import json

from .config import config, MARKET_METADATA

@dataclass
class TimeWindow:
    """Represents a training/prediction time window"""
    train_start: date
    train_end: date
    prediction_date: date
    horizon_end: date
    
    @property
    def train_duration_months(self) -> int:
        """Calculate training window duration in months"""
        return (self.train_end.year - self.train_start.year) * 12 + \
               (self.train_end.month - self.train_start.month)
    
    @property
    def horizon_months(self) -> int:
        """Calculate horizon duration in months"""
        return (self.horizon_end.year - self.prediction_date.year) * 12 + \
               (self.horizon_end.month - self.prediction_date.month)

class TimeSlicer:
    """Handles time slicing logic for backtesting with no look-ahead bias"""
    
    def __init__(self):
        self.feature_ttl_constraints = config.feature_ttl_constraints
        self.min_train_window_months = config.min_train_window_months
    
    def asof_window(self, asof_date: date, horizon_months: int = 6) -> TimeWindow:
        """
        Define training window and forecast horizon for an as-of date
        
        Args:
            asof_date: The as-of date for prediction
            horizon_months: Forecast horizon in months
            
        Returns:
            TimeWindow with train/prediction boundaries
        """
        # Prediction date is the as-of date
        prediction_date = asof_date
        
        # Training end is slightly before prediction to avoid leakage
        # Use end of previous month to ensure clean separation
        if prediction_date.day == 1:
            train_end = (prediction_date - timedelta(days=1))
        else:
            train_end = date(prediction_date.year, prediction_date.month, 1) - timedelta(days=1)
        
        # Training start based on minimum window requirement
        train_start = date(
            train_end.year - (self.min_train_window_months // 12),
            train_end.month - (self.min_train_window_months % 12),
            1
        )
        
        # Handle month rollover
        if train_start.month <= 0:
            train_start = train_start.replace(
                year=train_start.year - 1,
                month=train_start.month + 12
            )
        
        # Horizon end date
        horizon_end = date(
            prediction_date.year + (horizon_months // 12),
            prediction_date.month + (horizon_months % 12),
            prediction_date.day
        )
        
        # Handle month rollover for horizon
        if horizon_end.month > 12:
            horizon_end = horizon_end.replace(
                year=horizon_end.year + (horizon_end.month - 1) // 12,
                month=((horizon_end.month - 1) % 12) + 1
            )
        
        return TimeWindow(
            train_start=train_start,
            train_end=train_end,
            prediction_date=prediction_date,
            horizon_end=horizon_end
        )
    
    def generate_asof_dates(
        self,
        start_date: date,
        end_date: date,
        frequency: str = "monthly"
    ) -> List[date]:
        """
        Generate series of as-of dates for backtesting
        
        Args:
            start_date: First as-of date
            end_date: Last as-of date
            frequency: 'weekly', 'monthly', or 'quarterly'
            
        Returns:
            List of as-of dates
        """
        dates = []
        current_date = start_date
        
        if frequency == "weekly":
            delta = timedelta(weeks=1)
        elif frequency == "monthly":
            delta = timedelta(days=30)  # Approximate, will adjust
        elif frequency == "quarterly":
            delta = timedelta(days=90)  # Approximate, will adjust
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")
        
        while current_date <= end_date:
            dates.append(current_date)
            
            if frequency == "monthly":
                # Move to first of next month
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, current_date.month + 1, 1)
            elif frequency == "quarterly":
                # Move to first of next quarter
                next_quarter_month = ((current_date.month - 1) // 3 + 1) * 3 + 1
                if next_quarter_month > 12:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, next_quarter_month, 1)
            else:
                current_date += delta
        
        return dates
    
    def validate_data_vintage(
        self,
        data_timestamp: datetime,
        asof_date: date,
        data_source: str,
        feature_name: Optional[str] = None
    ) -> bool:
        """
        Validate that data is available as-of the prediction date
        
        Args:
            data_timestamp: When the data was actually available
            asof_date: The as-of date for prediction
            data_source: Source of the data (for TTL lookup)
            feature_name: Specific feature name for fine-grained TTL
            
        Returns:
            True if data should be available as-of prediction date
        """
        # Convert as-of date to end-of-day datetime
        asof_datetime = datetime.combine(asof_date, datetime.max.time())
        
        # Check basic temporal constraint
        if data_timestamp > asof_datetime:
            return False
        
        # Check feature TTL constraints
        ttl_key = feature_name if feature_name in self.feature_ttl_constraints else data_source
        ttl_seconds = self.feature_ttl_constraints.get(ttl_key)
        
        if ttl_seconds:
            # Data must not be fresher than allowed TTL at as-of date
            earliest_allowed = asof_datetime - timedelta(seconds=ttl_seconds)
            if data_timestamp > earliest_allowed:
                return False
        
        return True
    
    def compute_feature_fingerprint(
        self,
        asof_date: date,
        training_window: TimeWindow,
        feature_sources: List[str],
        model_version: Optional[str] = None
    ) -> str:
        """
        Compute stable fingerprint for feature set and time window
        Used for caching and auditing
        """
        fingerprint_data = {
            "asof_date": asof_date.isoformat(),
            "train_start": training_window.train_start.isoformat(),
            "train_end": training_window.train_end.isoformat(),
            "prediction_date": training_window.prediction_date.isoformat(),
            "horizon_end": training_window.horizon_end.isoformat(),
            "feature_sources": sorted(feature_sources),
            "model_version": model_version,
            "ttl_constraints": sorted(self.feature_ttl_constraints.items())
        }
        
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_json.encode()).hexdigest()[:16]
    
    def get_market_timezone(self, market: str) -> str:
        """Get timezone for market (for proper as-of cutoffs)"""
        return MARKET_METADATA.get(market, {}).get("timezone", "UTC")
    
    def adjust_for_market_hours(
        self,
        asof_datetime: datetime,
        market: str,
        data_source: str
    ) -> datetime:
        """
        Adjust as-of cutoff for market hours and data availability
        
        Some data sources only update during business hours
        """
        # For MLS data, assume updates happen during business hours
        if data_source in ["mls_data", "market_prices"]:
            # If as-of time is before 9 AM, use previous business day
            if asof_datetime.hour < 9:
                asof_datetime = asof_datetime.replace(hour=17, minute=0, second=0) - timedelta(days=1)
                
                # Skip weekends
                while asof_datetime.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    asof_datetime -= timedelta(days=1)
                    asof_datetime = asof_datetime.replace(hour=17, minute=0, second=0)
        
        return asof_datetime
    
    def validate_training_window(self, window: TimeWindow) -> List[str]:
        """
        Validate training window meets minimum requirements
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check minimum training window
        if window.train_duration_months < self.min_train_window_months:
            issues.append(
                f"Training window ({window.train_duration_months} months) below minimum "
                f"({self.min_train_window_months} months)"
            )
        
        # Check for temporal leakage
        if window.train_end >= window.prediction_date:
            issues.append("Training end date must be before prediction date")
        
        # Check horizon reasonableness
        if window.horizon_months > config.max_horizon_months:
            issues.append(
                f"Horizon ({window.horizon_months} months) exceeds maximum "
                f"({config.max_horizon_months} months)"
            )
        
        # Check for realistic time ranges
        if window.train_start < date(2010, 1, 1):
            issues.append("Training start date is too early (before 2010)")
        
        if window.horizon_end > date.today() + timedelta(days=365*3):
            issues.append("Horizon end date is too far in future (>3 years)")
        
        return issues
    
    def get_data_sources_asof(
        self,
        asof_date: date,
        required_sources: List[str]
    ) -> Dict[str, bool]:
        """
        Check which data sources should be available as-of date
        
        Returns:
            Dict mapping source name to availability boolean
        """
        availability = {}
        
        for source in required_sources:
            # Simulate data source availability based on historical rollout dates
            rollout_dates = {
                "mls_data": date(2015, 1, 1),
                "mortgage_rates": date(2010, 1, 1),
                "economic_indicators": date(2012, 1, 1),
                "demographics": date(2010, 1, 1),
                "market_trends": date(2018, 1, 1),
                "comparable_sales": date(2016, 1, 1),
                "property_tax": date(2014, 1, 1),
                "crime_data": date(2017, 1, 1),
                "school_ratings": date(2015, 6, 1),
                "walkability": date(2019, 1, 1)
            }
            
            rollout_date = rollout_dates.get(source, date(2010, 1, 1))
            availability[source] = asof_date >= rollout_date
        
        return availability
    
    def simulate_data_latency(
        self,
        asof_datetime: datetime,
        data_source: str
    ) -> datetime:
        """
        Simulate realistic data latency for historical accuracy
        
        Returns:
            Actual available timestamp considering latency
        """
        latencies = {
            "mls_data": timedelta(hours=4),       # 4 hour delay
            "mortgage_rates": timedelta(hours=1),  # 1 hour delay
            "economic_indicators": timedelta(days=3),  # 3 day delay
            "demographics": timedelta(days=30),    # 1 month delay
            "market_trends": timedelta(hours=6),   # 6 hour delay
            "comparable_sales": timedelta(hours=12),  # 12 hour delay
        }
        
        latency = latencies.get(data_source, timedelta(hours=1))
        return asof_datetime - latency

# Global instance
time_slicer = TimeSlicer()
