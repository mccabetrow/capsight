"""
Feature Store implementation for CapSight
Manages feature definition, computation, storage, and serving
Uses Feast as the underlying feature store with custom extensions
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from ..core.config import settings, FEATURE_GROUPS
from ..core.utils import logger, METRICS, track_execution_time, validate_data_freshness

# Mock imports - will resolve when requirements installed
try:
    import pandas as pd
    import numpy as np
    from feast import FeatureStore, Entity, FeatureView, Field, FileSource
    from feast.types import Float32, Int64, String
except ImportError:
    pass


@dataclass
class FeatureRequest:
    """Request for feature computation/retrieval"""
    entity_values: Dict[str, Union[str, int, List[str], List[int]]]
    feature_names: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    max_age_seconds: Optional[int] = None


@dataclass
class FeatureResponse:
    """Response containing computed features"""
    features: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    computation_time_ms: float = 0.0
    cache_hit: bool = False
    freshness_scores: Dict[str, float] = field(default_factory=dict)


class FeatureComputer:
    """Computes derived features from raw market data"""
    
    def __init__(self):
        self.feature_cache = {}
    
    @track_execution_time("feature_compute_duration", {"feature_name": "treasury_features"})
    async def compute_treasury_features(self, raw_data: Dict[str, float], timestamp: datetime) -> Dict[str, float]:
        """Compute treasury-derived features"""
        features = {}
        
        if "treasury_10y_rate" in raw_data and "treasury_2y_rate" in raw_data:
            # Yield curve slope
            features["yield_curve_slope"] = raw_data["treasury_10y_rate"] - raw_data["treasury_2y_rate"]
            
            # Term structure steepness
            if "treasury_30y_rate" in raw_data:
                features["term_structure_steepness"] = (
                    raw_data["treasury_30y_rate"] - raw_data["treasury_2y_rate"]
                ) / 28  # Per year
        
        # Treasury volatility (mock implementation)
        if "treasury_10y_rate" in raw_data:
            features["treasury_10y_volatility"] = await self._compute_volatility(
                "treasury_10y_rate", raw_data["treasury_10y_rate"], timestamp
            )
        
        return features
    
    @track_execution_time("feature_compute_duration", {"feature_name": "credit_features"})
    async def compute_credit_features(self, raw_data: Dict[str, float], timestamp: datetime) -> Dict[str, float]:
        """Compute credit spread derived features"""
        features = {}
        
        # Credit risk premium
        if "high_yield_spread" in raw_data and "investment_grade_spread" in raw_data:
            features["credit_risk_premium"] = raw_data["high_yield_spread"] - raw_data["investment_grade_spread"]
        
        # MBS-Treasury spread
        if "mbs_spread" in raw_data and "treasury_10y_rate" in raw_data:
            features["mbs_treasury_spread"] = raw_data["mbs_spread"]
        
        # CMBS risk gradient
        if "cmbs_aaa_spread" in raw_data and "cmbs_bbb_spread" in raw_data:
            features["cmbs_risk_gradient"] = raw_data["cmbs_bbb_spread"] - raw_data["cmbs_aaa_spread"]
        
        return features
    
    @track_execution_time("feature_compute_duration", {"feature_name": "market_features"})
    async def compute_market_features(self, market_id: str, raw_data: Dict[str, float], timestamp: datetime) -> Dict[str, float]:
        """Compute market-level features"""
        features = {}
        
        # Cap rate compression indicator
        if "reit_implied_caprate" in raw_data:
            features["caprate_compression_indicator"] = await self._compute_caprate_momentum(
                market_id, raw_data["reit_implied_caprate"], timestamp
            )
        
        # Demand pressure index
        if "transaction_volume" in raw_data and "absorption_rate" in raw_data:
            features["demand_pressure_index"] = (
                raw_data["absorption_rate"] * np.log(1 + raw_data["transaction_volume"])
            )
        
        # Supply constraint factor
        if "construction_starts" in raw_data and "absorption_rate" in raw_data:
            features["supply_constraint_factor"] = raw_data["absorption_rate"] / (
                raw_data["construction_starts"] + 0.01
            )
        
        return features
    
    @track_execution_time("feature_compute_duration", {"feature_name": "property_features"})
    async def compute_property_features(self, property_id: str, raw_data: Dict[str, float], timestamp: datetime) -> Dict[str, float]:
        """Compute property-specific features"""
        features = {}
        
        # NOI growth momentum
        if "current_noi" in raw_data:
            features["noi_growth_12m"] = await self._compute_growth_rate(
                f"noi_{property_id}", raw_data["current_noi"], timestamp, months=12
            )
            features["noi_growth_3m"] = await self._compute_growth_rate(
                f"noi_{property_id}", raw_data["current_noi"], timestamp, months=3
            )
        
        # Rent per square foot percentile
        if "rent_psf" in raw_data:
            features["rent_psf_percentile"] = await self._compute_percentile_rank(
                f"rent_{property_id}", raw_data["rent_psf"]
            )
        
        # Location attractiveness score
        if "nearby_foot_traffic" in raw_data and "search_interest" in raw_data:
            features["location_attractiveness"] = (
                0.6 * self._normalize(raw_data["nearby_foot_traffic"]) +
                0.4 * self._normalize(raw_data["search_interest"])
            )
        
        return features
    
    async def _compute_volatility(self, series_name: str, current_value: float, timestamp: datetime, window_days: int = 30) -> float:
        """Compute rolling volatility (mock implementation)"""
        # In production, would fetch historical data and compute actual volatility
        return 0.05 + (hash(series_name) % 100) / 10000  # Mock volatility 0.05-0.15
    
    async def _compute_caprate_momentum(self, market_id: str, current_caprate: float, timestamp: datetime) -> float:
        """Compute cap rate momentum/trend"""
        # Mock momentum calculation - in production would use historical data
        key = f"caprate_momentum_{market_id}"
        if key in self.feature_cache:
            previous = self.feature_cache[key]
            momentum = (current_caprate - previous) / previous
        else:
            momentum = 0.0
        
        self.feature_cache[key] = current_caprate
        return momentum
    
    async def _compute_growth_rate(self, series_key: str, current_value: float, timestamp: datetime, months: int = 12) -> float:
        """Compute growth rate over specified period"""
        # Mock growth calculation
        cache_key = f"growth_{series_key}_{months}m"
        if cache_key in self.feature_cache:
            historical = self.feature_cache[cache_key]
            growth_rate = (current_value - historical) / historical
        else:
            growth_rate = 0.02  # Mock 2% growth
        
        self.feature_cache[cache_key] = current_value
        return growth_rate
    
    async def _compute_percentile_rank(self, series_key: str, value: float) -> float:
        """Compute percentile rank within historical distribution"""
        # Mock percentile - in production would maintain historical distributions
        return min(max(0.0, (hash(series_key) % 100) / 100.0), 1.0)
    
    def _normalize(self, value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
        """Normalize value to 0-1 range"""
        return (value - min_val) / (max_val - min_val)


class FeatureStoreService:
    """Main feature store service using Feast"""
    
    def __init__(self):
        self.feature_computer = FeatureComputer()
        self.feast_store = None
        self.feature_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def initialize(self):
        """Initialize Feast feature store"""
        try:
            # Initialize Feast (mock implementation)
            logger.info("Initializing Feast feature store", repo_path=settings.feast_repo_path)
            
            # Create feature store repository structure
            await self._setup_feature_definitions()
            
            # In production, would use:
            # self.feast_store = FeatureStore(repo_path=settings.feast_repo_path)
            
            logger.info("Feature store initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize feature store", error=str(e))
            raise
    
    @track_execution_time("feature_retrieval_duration", {"feature_group": "all"})
    async def get_features(self, request: FeatureRequest) -> FeatureResponse:
        """Retrieve features for entities"""
        start_time = datetime.now()
        
        # Check cache first
        cache_key = self._get_cache_key(request)
        if cache_key in self.feature_cache:
            cached_result = self.feature_cache[cache_key]
            cache_age = (datetime.now() - cached_result["timestamp"]).total_seconds()
            
            if cache_age < self.cache_ttl:
                response = cached_result["response"]
                response.cache_hit = True
                return response
        
        # Compute fresh features
        features = {}
        freshness_scores = {}
        
        # Extract entities
        date_entities = request.entity_values.get("date", [])
        market_ids = request.entity_values.get("market_id", [])
        property_ids = request.entity_values.get("property_id", [])
        
        # Ensure lists
        if not isinstance(date_entities, list):
            date_entities = [date_entities]
        if not isinstance(market_ids, list):
            market_ids = [market_ids] if market_ids else []
        if not isinstance(property_ids, list):
            property_ids = [property_ids] if property_ids else []
        
        # Get features for each feature group
        for date in date_entities:
            timestamp = datetime.fromisoformat(date) if isinstance(date, str) else date
            
            # Treasury features (date-only entity)
            treasury_raw = await self._get_raw_market_data("treasury", timestamp)
            treasury_features = await self.feature_computer.compute_treasury_features(treasury_raw, timestamp)
            features.update(treasury_features)
            
            # Credit features (date-only entity)  
            credit_raw = await self._get_raw_market_data("credit", timestamp)
            credit_features = await self.feature_computer.compute_credit_features(credit_raw, timestamp)
            features.update(credit_features)
            
            # Market features (market_id + date entities)
            for market_id in market_ids:
                market_raw = await self._get_raw_market_data("market", timestamp, market_id)
                market_features = await self.feature_computer.compute_market_features(market_id, market_raw, timestamp)
                
                # Prefix with market_id
                for feature_name, value in market_features.items():
                    features[f"market_{market_id}_{feature_name}"] = value
            
            # Property features (property_id + date entities)
            for property_id in property_ids:
                property_raw = await self._get_raw_market_data("property", timestamp, property_id)
                property_features = await self.feature_computer.compute_property_features(property_id, property_raw, timestamp)
                
                # Prefix with property_id
                for feature_name, value in property_features.items():
                    features[f"property_{property_id}_{feature_name}"] = value
        
        # Calculate freshness scores
        for feature_group in FEATURE_GROUPS.keys():
            freshness_scores[feature_group] = await self._calculate_freshness_score(feature_group, timestamp)
        
        # Create response
        computation_time = (datetime.now() - start_time).total_seconds() * 1000
        response = FeatureResponse(
            features=features,
            metadata={
                "request_timestamp": request.timestamp or datetime.now(timezone.utc),
                "feature_groups": list(FEATURE_GROUPS.keys()),
                "entity_count": len(date_entities) + len(market_ids) + len(property_ids)
            },
            computation_time_ms=computation_time,
            cache_hit=False,
            freshness_scores=freshness_scores
        )
        
        # Cache result
        self.feature_cache[cache_key] = {
            "response": response,
            "timestamp": datetime.now()
        }
        
        return response
    
    async def _get_raw_market_data(self, data_type: str, timestamp: datetime, entity_id: Optional[str] = None) -> Dict[str, float]:
        """Retrieve raw market data (mock implementation)"""
        
        # Mock data based on type
        mock_data = {}
        
        if data_type == "treasury":
            mock_data = {
                "treasury_10y_rate": 4.5,
                "treasury_2y_rate": 4.8,
                "treasury_30y_rate": 4.3,
                "fed_funds_rate": 5.25
            }
        elif data_type == "credit":
            mock_data = {
                "investment_grade_spread": 1.25,
                "high_yield_spread": 4.85,
                "mbs_spread": 0.75,
                "cmbs_aaa_spread": 1.15,
                "cmbs_bbb_spread": 2.45
            }
        elif data_type == "market":
            mock_data = {
                "reit_implied_caprate": 0.055,
                "transaction_volume": 150.0,
                "absorption_rate": 0.85,
                "construction_starts": 45.0,
                "rent_growth": 0.035,
                "occupancy_rate": 0.92
            }
        elif data_type == "property":
            mock_data = {
                "current_noi": 2500000.0,
                "current_caprate": 0.065,
                "occupancy": 0.94,
                "rent_psf": 28.50,
                "nearby_foot_traffic": 85.2,
                "search_interest": 72.1,
                "submarket_sentiment": 0.68
            }
        
        return mock_data
    
    async def _calculate_freshness_score(self, feature_group: str, timestamp: datetime) -> float:
        """Calculate data freshness score for feature group"""
        # Mock freshness calculation
        now = datetime.now(timezone.utc)
        age_hours = (now - timestamp).total_seconds() / 3600
        
        # Exponential decay based on feature group TTL
        ttl_hours = FEATURE_GROUPS.get(feature_group, {}).get("ttl", 86400) / 3600
        freshness = np.exp(-age_hours / ttl_hours)
        
        return float(freshness)
    
    def _get_cache_key(self, request: FeatureRequest) -> str:
        """Generate cache key for feature request"""
        import hashlib
        key_data = {
            "entities": request.entity_values,
            "features": request.feature_names,
            "timestamp": request.timestamp.isoformat() if request.timestamp else None
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _setup_feature_definitions(self):
        """Setup Feast feature definitions"""
        # Mock feature definition setup
        logger.info("Setting up feature definitions", groups=list(FEATURE_GROUPS.keys()))
        
        # In production, would create Feast entities and feature views
        for group_name, group_config in FEATURE_GROUPS.items():
            logger.debug("Creating feature group", 
                        group=group_name, 
                        features=group_config["features"])


class RealTimeFeatureService:
    """Real-time feature serving for low-latency inference"""
    
    def __init__(self, feature_store: FeatureStoreService):
        self.feature_store = feature_store
        self.hot_cache = {}  # In-memory cache for ultra-low latency
    
    async def get_features_for_inference(
        self, 
        property_ids: List[str], 
        market_ids: List[str],
        max_latency_ms: int = 100
    ) -> Dict[str, FeatureResponse]:
        """Get features optimized for real-time inference"""
        
        start_time = datetime.now()
        results = {}
        
        # Use current timestamp
        current_time = datetime.now(timezone.utc)
        
        for property_id in property_ids:
            # Build feature request
            request = FeatureRequest(
                entity_values={
                    "property_id": property_id,
                    "market_id": market_ids[0] if market_ids else "default", 
                    "date": current_time
                },
                timestamp=current_time
            )
            
            # Get features with latency constraint
            response = await self.feature_store.get_features(request)
            
            # Check if we exceeded latency budget
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            if elapsed_ms > max_latency_ms:
                logger.warning("Feature retrieval exceeded latency budget", 
                             elapsed_ms=elapsed_ms, 
                             budget_ms=max_latency_ms,
                             property_id=property_id)
            
            results[property_id] = response
        
        return results


# Export main classes
__all__ = [
    "FeatureStoreService",
    "RealTimeFeatureService",
    "FeatureRequest", 
    "FeatureResponse",
    "FeatureComputer"
]
