"""
Test configuration for pytest.
"""

import pytest
import asyncio
from typing import Generator
import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration  
pytest.mark.performance = pytest.mark.performance

# Async test support
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Database test fixtures
@pytest.fixture(scope="session")
def test_db_url():
    """Test database URL."""
    return os.getenv("TEST_DATABASE_URL", "sqlite:///./test_backtest.db")

@pytest.fixture(scope="session") 
def test_redis_url():
    """Test Redis URL."""
    return os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

@pytest.fixture(scope="session")
def test_mlflow_url():
    """Test MLflow URL."""
    return os.getenv("TEST_MLFLOW_URL", "http://localhost:5000")

# Test data fixtures
@pytest.fixture
def sample_property_data():
    """Sample property data for testing."""
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    
    return pd.DataFrame({
        'property_id': [f'test_prop_{i}' for i in range(100)],
        'price': np.random.uniform(100000, 1000000, 100),
        'sqft': np.random.uniform(500, 5000, 100),
        'bedrooms': np.random.randint(1, 6, 100),
        'bathrooms': np.random.uniform(1, 4, 100),
        'lat': np.random.uniform(40.7, 40.8, 100),
        'lng': np.random.uniform(-74.1, -73.9, 100),
        'year_built': np.random.randint(1950, 2023, 100),
        'property_type': np.random.choice(['house', 'condo', 'townhouse'], 100),
        'market_segment': np.random.choice(['luxury', 'mid-market', 'affordable'], 100)
    })

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )

# Test collection configuration
def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests in integration folder
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        # Mark tests in performance folder  
        elif "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        # Mark everything else as unit tests
        else:
            item.add_marker(pytest.mark.unit)
