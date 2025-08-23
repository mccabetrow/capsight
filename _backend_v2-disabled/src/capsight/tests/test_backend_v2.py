"""
Test suite for CapSight Backend v2
Comprehensive testing for real-time predictions, accuracy, and system health
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Mock the imports to avoid import errors during testing
try:
    import numpy as np
    import pandas as pd
    from httpx import AsyncClient
    from fastapi.testclient import TestClient
except ImportError:
    # Mock for development environment
    pass

from capsight import app, prediction_service
from capsight.models.feature_store import FeatureStoreService, FeatureRequest
from capsight.models.predictors import CapRatePredictor, ArbitrageScorer
from capsight.monitoring.health import HealthChecker, AccuracyMonitor
from capsight.core.config import settings


# Test Configuration
TEST_SETTINGS = {
    "environment": "test",
    "database_url": "sqlite:///./test.db",
    "redis_url": "redis://localhost:6379/15",  # Use test database
    "mlflow_tracking_uri": "./test_mlruns"
}


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
async def feature_store():
    """Test feature store instance"""
    store = FeatureStoreService()
    await store.initialize()
    return store


@pytest.fixture
async def health_checker():
    """Test health checker instance"""
    checker = HealthChecker()
    await checker.initialize()
    return checker


class TestFeatureStore:
    """Test feature store functionality"""
    
    @pytest.mark.asyncio
    async def test_feature_store_initialization(self, feature_store):
        """Test feature store initializes correctly"""
        assert feature_store is not None
        assert feature_store.feature_computer is not None
        assert hasattr(feature_store, 'feature_cache')
    
    @pytest.mark.asyncio
    async def test_get_features_single_property(self, feature_store):
        """Test feature retrieval for single property"""
        request = FeatureRequest(
            entity_values={
                "property_id": "test_property_123",
                "market_id": "atlanta_msa",
                "date": datetime.now(timezone.utc)
            }
        )
        
        response = await feature_store.get_features(request)
        
        assert response is not None
        assert isinstance(response.features, dict)
        assert len(response.features) > 0
        assert response.computation_time_ms > 0
        assert isinstance(response.freshness_scores, dict)
    
    @pytest.mark.asyncio
    async def test_feature_computation_treasury(self, feature_store):
        """Test treasury feature computation"""
        raw_data = {
            "treasury_10y_rate": 4.5,
            "treasury_2y_rate": 4.8,
            "treasury_30y_rate": 4.3
        }
        
        features = await feature_store.feature_computer.compute_treasury_features(
            raw_data, datetime.now(timezone.utc)
        )
        
        assert "yield_curve_slope" in features
        assert features["yield_curve_slope"] == 4.5 - 4.8  # 10Y - 2Y
        assert "term_structure_steepness" in features


class TestPredictionModels:
    """Test ML prediction models"""
    
    @pytest.mark.asyncio
    async def test_caprate_predictor_training(self):
        """Test cap rate predictor training"""
        model = CapRatePredictor()
        
        # Mock training data
        np.random.seed(42)
        X_train = np.random.random((100, 20))
        y_train = np.random.uniform(0.04, 0.08, 100)  # Cap rates 4-8%
        
        metrics = await model.train(X_train, y_train)
        
        assert "mae_bps" in metrics
        assert "rmse_bps" in metrics
        assert "r2_score" in metrics
        assert metrics["mae_bps"] > 0
        assert model.models["lightgbm"] is not None
    
    @pytest.mark.asyncio
    async def test_caprate_predictor_inference(self):
        """Test cap rate predictor inference"""
        model = CapRatePredictor()
        
        # Mock training first
        X_train = np.random.random((50, 20))
        y_train = np.random.uniform(0.04, 0.08, 50)
        await model.train(X_train, y_train)
        
        # Test prediction
        X_test = np.random.random((5, 20))
        predictions, metadata = await model.predict(X_test, include_uncertainty=True)
        
        assert len(predictions) == 5
        assert all(0.02 < pred < 0.12 for pred in predictions)  # Reasonable cap rate range
        assert "confidence_intervals" in metadata
        assert metadata["model_name"] == "caprate_predictor"
    
    @pytest.mark.asyncio 
    async def test_arbitrage_scorer_training(self):
        """Test arbitrage scoring model"""
        model = ArbitrageScorer()
        
        # Mock training data
        X_train = np.random.random((100, 20))
        y_train = np.random.uniform(0, 100, 100)  # Arbitrage scores 0-100
        
        metrics = await model.train(X_train, y_train)
        
        assert "mae" in metrics
        assert "correlation" in metrics
        assert "top_decile_precision" in metrics
        assert model.scoring_model is not None
        assert len(model.percentile_thresholds) > 0


class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
    
    def test_single_property_prediction(self, client):
        """Test single property prediction endpoint"""
        request_data = {
            "property_id": "test_property_123",
            "market_id": "atlanta_msa",
            "current_noi": 2500000,
            "current_caprate": 0.065,
            "property_type": "multifamily"
        }
        
        response = client.post("/v1/predict/property", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "property_id" in data
        assert "implied_caprate" in data
        assert "arbitrage_score" in data
        assert "noi_growth_12m" in data
        assert "key_drivers" in data
        assert data["property_id"] == "test_property_123"
        
        # Validate prediction values are reasonable
        assert 0.02 < data["implied_caprate"] < 0.12
        assert 0 <= data["arbitrage_score"] <= 100
        assert -0.1 < data["noi_growth_12m"] < 0.2  # -10% to +20% NOI growth
    
    def test_batch_prediction(self, client):
        """Test batch prediction endpoint"""
        request_data = {
            "properties": [
                {
                    "property_id": "test_prop_1",
                    "market_id": "atlanta_msa",
                    "property_type": "multifamily"
                },
                {
                    "property_id": "test_prop_2", 
                    "market_id": "dallas_msa",
                    "property_type": "office"
                }
            ],
            "include_explanations": True,
            "confidence_level": 0.8
        }
        
        response = client.post("/v1/predict/batch", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "predictions" in data
        assert "summary" in data
        assert len(data["predictions"]) <= 2  # May have failures
        assert data["summary"]["total_requests"] == 2
    
    def test_model_status_endpoint(self, client):
        """Test model status endpoint"""
        response = client.get("/v1/models/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "models" in data
        assert "total_models" in data
        assert data["total_models"] >= 0


class TestAccuracyMonitoring:
    """Test accuracy monitoring system"""
    
    @pytest.mark.asyncio
    async def test_accuracy_monitor_initialization(self):
        """Test accuracy monitor initializes"""
        monitor = AccuracyMonitor()
        assert monitor.accuracy_history == {}
        assert monitor.breach_counts == {}
    
    @pytest.mark.asyncio
    async def test_record_accuracy_within_sla(self):
        """Test recording accuracy within SLA"""
        monitor = AccuracyMonitor()
        
        # Record good accuracy (within SLA)
        metric = await monitor.record_accuracy(
            "test_model", 
            "caprate_mae_bps", 
            50.0  # Below 75 BPS threshold
        )
        
        assert metric is not None
        assert metric.is_breach == False
        assert metric.current_value == 50.0
        assert "test_model_caprate_mae_bps" in monitor.accuracy_history
    
    @pytest.mark.asyncio
    async def test_record_accuracy_breach_sla(self):
        """Test recording accuracy breach"""
        monitor = AccuracyMonitor()
        
        # Record poor accuracy (breach SLA)
        metric = await monitor.record_accuracy(
            "test_model",
            "caprate_mae_bps",
            100.0  # Above 75 BPS threshold
        )
        
        assert metric is not None
        assert metric.is_breach == True
        assert metric.current_value == 100.0
        assert "test_model_caprate_mae_bps" in monitor.breach_counts
    
    def test_accuracy_summary(self):
        """Test accuracy summary generation"""
        monitor = AccuracyMonitor()
        
        # Add some mock history
        from capsight.monitoring.health import AccuracyMetric
        test_metric = AccuracyMetric(
            metric_name="caprate_mae_bps",
            current_value=60.0,
            threshold=75.0,
            timestamp=datetime.now(timezone.utc),
            model_name="test_model",
            is_breach=False
        )
        
        monitor.accuracy_history["test_model_caprate_mae_bps"] = [test_metric]
        
        summary = monitor.get_accuracy_summary()
        
        assert "total_metrics" in summary
        assert "active_breaches" in summary
        assert "recent_metrics" in summary
        assert summary["total_metrics"] == 1


class TestDataFreshness:
    """Test data freshness monitoring"""
    
    @pytest.mark.asyncio
    async def test_freshness_monitoring(self, health_checker):
        """Test data freshness checking"""
        freshness_metrics = await health_checker.freshness_monitor.check_data_freshness()
        
        assert isinstance(freshness_metrics, list)
        assert len(freshness_metrics) > 0
        
        for metric in freshness_metrics:
            assert hasattr(metric, 'source_name')
            assert hasattr(metric, 'age_seconds') 
            assert hasattr(metric, 'is_stale')
            assert metric.age_seconds >= 0


class TestSystemIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_prediction_pipeline(self):
        """Test complete prediction pipeline"""
        # Initialize services
        feature_store = FeatureStoreService()
        await feature_store.initialize()
        
        # Create feature request
        request = FeatureRequest(
            entity_values={
                "property_id": "integration_test_property",
                "market_id": "test_market",
                "date": datetime.now(timezone.utc)
            }
        )
        
        # Get features
        features = await feature_store.get_features(request)
        assert features is not None
        assert len(features.features) > 0
        
        # Test model prediction with features
        model = CapRatePredictor()
        X_train = np.random.random((50, 20))
        y_train = np.random.uniform(0.04, 0.08, 50)
        await model.train(X_train, y_train)
        
        # Feature matrix from features dict
        feature_matrix = np.random.random((1, 20))  # Mock feature preparation
        predictions, metadata = await model.predict(feature_matrix)
        
        assert len(predictions) == 1
        assert 0.02 < predictions[0] < 0.12
        assert metadata["model_name"] == "caprate_predictor"


class TestPerformanceAndLatency:
    """Test performance and latency requirements"""
    
    @pytest.mark.asyncio
    async def test_prediction_latency(self, client):
        """Test prediction latency meets SLA"""
        import time
        
        request_data = {
            "property_id": "latency_test_property",
            "market_id": "test_market",
            "property_type": "multifamily"
        }
        
        start_time = time.time()
        response = client.post("/v1/predict/property", json=request_data)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert latency_ms < 500  # Should be under 500ms for single property
        
        # Check reported latency in response
        data = response.json()
        assert "prediction_latency_ms" in data
        assert data["prediction_latency_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_batch_prediction_latency(self, client):
        """Test batch prediction latency scales reasonably"""
        import time
        
        # Create batch of 10 properties
        properties = [
            {
                "property_id": f"batch_test_property_{i}",
                "market_id": "test_market",
                "property_type": "multifamily"
            }
            for i in range(10)
        ]
        
        request_data = {
            "properties": properties,
            "include_explanations": True
        }
        
        start_time = time.time()
        response = client.post("/v1/predict/batch", json=request_data)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert latency_ms < 5000  # Should be under 5 seconds for 10 properties
        
        data = response.json()
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] > 0


# Test configuration for pytest
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([
        __file__,
        "-v",  # verbose output
        "--tb=short",  # shorter traceback format
        "--asyncio-mode=auto",  # auto-detect async tests
    ])
