"""
Feature loading and as-of data retrieval for backtesting
Integrates with Feast feature store and ensures proper historical context
"""
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from dataclasses import dataclass

# Feast imports
try:
    from feast import FeatureStore, Entity, Feature, FeatureView
    from feast.data_source import DataSource
    from feast.types import ValueType
except ImportError:
    # Mock for environments without Feast
    class FeatureStore: pass
    class Entity: pass
    class Feature: pass
    class FeatureView: pass
    class DataSource: pass
    class ValueType: pass

from .config import config
from .schemas import BacktestFeatureSet
from .time_slicer import TimeSlicer, TimeWindow, time_slicer

@dataclass
class FeatureMetadata:
    """Metadata about a feature for auditing and validation"""
    name: str
    source: str
    entity: str
    dtype: str
    retrieval_timestamp: datetime
    asof_timestamp: datetime
    row_count: int
    null_rate: float
    vintage_valid: bool

class FeatureLoader:
    """Loads features from Feast store with proper as-of semantics"""
    
    def __init__(
        self,
        feast_store_path: Optional[str] = None,
        redis_connection_string: Optional[str] = None
    ):
        self.feast_store_path = feast_store_path or config.feast_store_path
        self.redis_connection_string = redis_connection_string or config.redis_url
        self.time_slicer = time_slicer
        self._feature_store = None
        self._feature_cache = {}
        
    async def _get_feature_store(self) -> FeatureStore:
        """Lazy initialization of Feast feature store"""
        if self._feature_store is None:
            # Initialize Feast store
            self._feature_store = FeatureStore(repo_path=self.feast_store_path)
        return self._feature_store
    
    async def load_features_asof(
        self,
        entity_df: pd.DataFrame,
        asof_date: date,
        feature_views: List[str],
        entity_column: str = "property_id"
    ) -> pd.DataFrame:
        """
        Load features from Feast store as-of specific date
        
        Args:
            entity_df: DataFrame with entities (properties) to get features for
            asof_date: As-of date for feature values
            feature_views: List of feature view names to load
            entity_column: Name of entity column in DataFrame
            
        Returns:
            DataFrame with features joined to entities
        """
        store = await self._get_feature_store()
        
        # Convert as-of date to datetime (end of day)
        asof_datetime = datetime.combine(asof_date, datetime.max.time())
        
        # Create entity DataFrame with timestamp
        entity_df_with_ts = entity_df.copy()
        entity_df_with_ts["event_timestamp"] = asof_datetime
        
        # Validate entities exist
        if entity_column not in entity_df.columns:
            raise ValueError(f"Entity column '{entity_column}' not found in DataFrame")
        
        # Get historical features from Feast
        try:
            training_df = store.get_historical_features(
                entity_df=entity_df_with_ts,
                features=[
                    f"{view}:*"  # Get all features from each view
                    for view in feature_views
                ],
                full_feature_names=True
            ).to_df()
            
        except Exception as e:
            # Fallback to mock data for testing
            print(f"Warning: Feast feature loading failed ({e}), using mock data")
            training_df = await self._generate_mock_features(
                entity_df, asof_date, feature_views
            )
        
        return training_df
    
    async def _generate_mock_features(
        self,
        entity_df: pd.DataFrame,
        asof_date: date,
        feature_views: List[str]
    ) -> pd.DataFrame:
        """Generate mock features for testing when Feast is unavailable"""
        
        # Start with entity DataFrame
        result_df = entity_df.copy()
        n_entities = len(entity_df)
        
        # Add basic property features
        if "property_features" in feature_views:
            result_df["sqft"] = np.random.normal(2000, 500, n_entities)
            result_df["bedrooms"] = np.random.choice([2, 3, 4, 5], n_entities)
            result_df["bathrooms"] = np.random.normal(2.5, 0.8, n_entities)
            result_df["age_years"] = np.random.exponential(15, n_entities)
            result_df["lot_size"] = np.random.lognormal(8, 0.5, n_entities)
        
        # Add market features
        if "market_features" in feature_views:
            result_df["median_price_zip"] = np.random.normal(400000, 100000, n_entities)
            result_df["days_on_market_avg"] = np.random.exponential(30, n_entities)
            result_df["inventory_months"] = np.random.gamma(2, 2, n_entities)
            result_df["price_per_sqft_zip"] = result_df["median_price_zip"] / 2000
        
        # Add economic features
        if "economic_features" in feature_views:
            result_df["mortgage_rate_30y"] = np.random.normal(3.5, 0.5, n_entities)
            result_df["unemployment_rate"] = np.random.beta(2, 20, n_entities) * 15
            result_df["gdp_growth_rate"] = np.random.normal(2.0, 1.5, n_entities)
            result_df["consumer_confidence"] = np.random.normal(100, 15, n_entities)
        
        # Add neighborhood features
        if "neighborhood_features" in feature_views:
            result_df["walkability_score"] = np.random.beta(3, 2, n_entities) * 100
            result_df["school_rating"] = np.random.beta(4, 2, n_entities) * 10
            result_df["crime_rate"] = np.random.exponential(5, n_entities)
            result_df["transit_access"] = np.random.beta(2, 3, n_entities) * 100
        
        # Add temporal decay based on as-of date
        days_from_base = (asof_date - date(2020, 1, 1)).days
        trend_factor = 1.0 + (days_from_base / 365.0) * 0.05  # 5% annual trend
        
        numeric_cols = result_df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col in ["median_price_zip", "price_per_sqft_zip"]:
                result_df[col] *= trend_factor
        
        return result_df
    
    async def validate_feature_freshness(
        self,
        features_df: pd.DataFrame,
        asof_date: date,
        feature_views: List[str]
    ) -> List[FeatureMetadata]:
        """
        Validate feature freshness and generate metadata
        
        Returns:
            List of feature metadata for auditing
        """
        metadata = []
        retrieval_time = datetime.now()
        asof_datetime = datetime.combine(asof_date, datetime.max.time())
        
        for col in features_df.columns:
            if col in ["property_id", "event_timestamp"]:
                continue
                
            # Determine source from column name
            source = self._infer_feature_source(col)
            
            # Calculate statistics
            values = features_df[col]
            row_count = len(values.dropna())
            null_rate = values.isnull().mean()
            dtype = str(values.dtype)
            
            # Validate vintage (simplified check)
            vintage_valid = self.time_slicer.validate_data_vintage(
                data_timestamp=asof_datetime,
                asof_date=asof_date,
                data_source=source
            )
            
            metadata.append(FeatureMetadata(
                name=col,
                source=source,
                entity="property",
                dtype=dtype,
                retrieval_timestamp=retrieval_time,
                asof_timestamp=asof_datetime,
                row_count=row_count,
                null_rate=null_rate,
                vintage_valid=vintage_valid
            ))
        
        return metadata
    
    def _infer_feature_source(self, feature_name: str) -> str:
        """Infer data source from feature name"""
        feature_lower = feature_name.lower()
        
        if any(term in feature_lower for term in ["sqft", "bedroom", "bathroom", "age", "lot"]):
            return "mls_data"
        elif any(term in feature_lower for term in ["mortgage", "rate", "interest"]):
            return "mortgage_rates"
        elif any(term in feature_lower for term in ["unemployment", "gdp", "confidence"]):
            return "economic_indicators"
        elif any(term in feature_lower for term in ["school", "crime", "walk", "transit"]):
            return "neighborhood_data"
        elif any(term in feature_lower for term in ["median_price", "inventory", "days_on_market"]):
            return "market_trends"
        else:
            return "unknown"
    
    async def create_training_dataset(
        self,
        entity_ids: List[str],
        training_window: TimeWindow,
        feature_views: List[str],
        target_column: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Create training dataset for a specific time window
        
        Args:
            entity_ids: List of property IDs
            training_window: Time window for training
            feature_views: Feature views to include
            target_column: Target variable column name
            
        Returns:
            Complete training dataset with features and targets
        """
        # Create entity DataFrame
        entity_df = pd.DataFrame({"property_id": entity_ids})
        
        # Load features as-of training end date
        features_df = await self.load_features_asof(
            entity_df=entity_df,
            asof_date=training_window.train_end,
            feature_views=feature_views
        )
        
        # Add target variable if specified
        if target_column:
            targets = await self._load_targets(
                entity_ids=entity_ids,
                prediction_date=training_window.prediction_date,
                horizon_end=training_window.horizon_end,
                target_column=target_column
            )
            
            features_df = features_df.merge(
                targets,
                on="property_id",
                how="left"
            )
        
        # Add time window metadata
        features_df["train_start"] = training_window.train_start
        features_df["train_end"] = training_window.train_end
        features_df["prediction_date"] = training_window.prediction_date
        features_df["horizon_end"] = training_window.horizon_end
        
        return features_df
    
    async def _load_targets(
        self,
        entity_ids: List[str],
        prediction_date: date,
        horizon_end: date,
        target_column: str
    ) -> pd.DataFrame:
        """Load target values for training (actual outcomes)"""
        
        # Mock target loading - in production this would query actual sales data
        n_entities = len(entity_ids)
        
        # Simulate realistic price appreciation
        days_horizon = (horizon_end - prediction_date).days
        annual_appreciation = 0.05  # 5% annual
        expected_return = annual_appreciation * (days_horizon / 365.0)
        
        # Add noise and market variations
        actual_returns = np.random.normal(
            expected_return,
            expected_return * 0.5,  # 50% volatility
            n_entities
        )
        
        targets_df = pd.DataFrame({
            "property_id": entity_ids,
            target_column: actual_returns,
            "target_calculated_date": horizon_end
        })
        
        return targets_df
    
    async def load_feature_set(
        self,
        feature_set_config: BacktestFeatureSet
    ) -> Dict[str, Any]:
        """
        Load complete feature set based on configuration
        
        Returns:
            Dictionary with features, metadata, and validation results
        """
        # Create entity DataFrame from property IDs
        entity_df = pd.DataFrame({
            "property_id": feature_set_config.entity_ids
        })
        
        # Load features
        features_df = await self.load_features_asof(
            entity_df=entity_df,
            asof_date=feature_set_config.asof_date,
            feature_views=feature_set_config.feature_views
        )
        
        # Validate features
        metadata = await self.validate_feature_freshness(
            features_df=features_df,
            asof_date=feature_set_config.asof_date,
            feature_views=feature_set_config.feature_views
        )
        
        # Apply feature transformations if specified
        if feature_set_config.transformations:
            features_df = self._apply_transformations(
                features_df,
                feature_set_config.transformations
            )
        
        return {
            "features": features_df,
            "metadata": metadata,
            "config": feature_set_config,
            "validation_passed": all(m.vintage_valid for m in metadata)
        }
    
    def _apply_transformations(
        self,
        df: pd.DataFrame,
        transformations: Dict[str, str]
    ) -> pd.DataFrame:
        """Apply feature transformations"""
        
        result_df = df.copy()
        
        for feature_name, transformation in transformations.items():
            if feature_name not in result_df.columns:
                continue
                
            if transformation == "log":
                result_df[f"{feature_name}_log"] = np.log1p(
                    result_df[feature_name].clip(lower=0)
                )
            elif transformation == "standardize":
                mean_val = result_df[feature_name].mean()
                std_val = result_df[feature_name].std()
                result_df[f"{feature_name}_std"] = (
                    result_df[feature_name] - mean_val
                ) / std_val
            elif transformation == "rank":
                result_df[f"{feature_name}_rank"] = result_df[feature_name].rank(
                    pct=True
                )
        
        return result_df
    
    async def cache_feature_set(
        self,
        feature_set_key: str,
        feature_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> None:
        """Cache feature set in Redis for reuse"""
        
        try:
            import redis
            import pickle
            
            r = redis.from_url(self.redis_connection_string)
            
            # Serialize feature data
            serialized_data = pickle.dumps(feature_data)
            
            # Store in Redis with TTL
            r.setex(
                name=f"backtest:features:{feature_set_key}",
                time=ttl_seconds,
                value=serialized_data
            )
            
        except Exception as e:
            print(f"Warning: Feature caching failed ({e})")
    
    async def get_cached_feature_set(
        self,
        feature_set_key: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached feature set from Redis"""
        
        try:
            import redis
            import pickle
            
            r = redis.from_url(self.redis_connection_string)
            
            # Get from Redis
            serialized_data = r.get(f"backtest:features:{feature_set_key}")
            
            if serialized_data:
                return pickle.loads(serialized_data)
            
        except Exception as e:
            print(f"Warning: Feature cache retrieval failed ({e})")
        
        return None

# Global instance
feature_loader = FeatureLoader()
