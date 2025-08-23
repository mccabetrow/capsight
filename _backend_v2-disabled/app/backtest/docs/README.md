# CapSight Backtest & Counterfactual Replay System

## Overview

The CapSight Backtest System is a comprehensive, production-grade backtesting and counterfactual replay platform designed for real estate investment ML models. It provides robust time-series validation, feature loading from Feast, counterfactual analysis, uplift measurement, automated reporting, and job scheduling.

## Architecture

### System Components

```
backend_v2/app/backtest/
├── __init__.py                 # Core subsystem exports
├── config.py                   # Configuration and constants
├── schemas.py                  # Pydantic models for API/DB
├── data_access.py              # Database operations
├── time_slicer.py              # Time slicing logic
├── feature_loader.py           # Feast feature integration
├── replay.py                   # Counterfactual replay engine
├── metrics.py                  # ML and investment metrics
├── uplift.py                   # Causal inference and uplift
├── reports/
│   └── renderer.py             # Report generation
├── jobs/
│   ├── scheduler.py            # Job orchestration  
│   └── cli.py                  # Command-line interface
├── api/
│   └── routes.py               # FastAPI endpoints
├── tests/
│   ├── conftest.py             # Test configuration
│   └── test_backtest.py        # Comprehensive test suite
├── grafana/
│   ├── backtest_dashboard.json # Grafana dashboard
│   ├── prometheus.yml          # Prometheus config
│   └── backtest_rules.yml      # Alerting rules
└── docs/
    ├── README.md               # This file
    ├── API.md                  # API documentation
    └── DEPLOYMENT.md           # Deployment guide
```

### Database Schema

The system uses PostgreSQL with the following key tables:

- `backtest_runs` - Track backtest executions
- `backtest_results` - Store individual prediction results
- `prediction_snapshots` - Historical predictions for replay
- `metrics_summary` - Aggregated performance metrics
- `model_snapshots` - ML model metadata and versions
- `backtest_jobs` - Scheduled job configurations
- `feature_sets` - Feature engineering metadata
- `backtest_audit_logs` - Audit trail for compliance

## Key Features

### 1. Time Series Backtesting

- **Walk-Forward Validation**: Progressive time-based splits
- **As-of Point-in-Time**: Ensures no data leakage
- **Configurable Windows**: Flexible training/testing periods
- **Market Regime Detection**: Automatic market condition segmentation

### 2. Feature Integration

- **Feast Integration**: Direct feature store connectivity
- **As-of Semantics**: Point-in-time correct feature loading  
- **Fallback Mechanisms**: Mock data when Feast unavailable
- **Feature Drift Detection**: Monitor for feature distribution changes

### 3. Counterfactual Replay

- **Historical Recreation**: Replay past model decisions
- **What-if Analysis**: Adjust model parameters retroactively
- **A/B Testing**: Compare model versions side-by-side
- **Scenario Planning**: Test different market conditions

### 4. Advanced Analytics

- **ML Metrics**: Accuracy, precision, recall, ROC-AUC, F1
- **Investment Metrics**: Sharpe ratio, max drawdown, volatility
- **Market Metrics**: Segment performance, price accuracy
- **Uplift Analysis**: Causal impact measurement
- **Cohort Analysis**: User behavior over time

### 5. Automated Reporting

- **Multi-format Output**: HTML, PDF, Markdown
- **Interactive Charts**: Time series, distributions, comparisons
- **Executive Summaries**: High-level insights for stakeholders
- **Drill-down Capability**: Detailed analysis on demand

### 6. Production Operations

- **Job Scheduling**: Cron-style recurring backtests
- **SLA Monitoring**: Runtime and accuracy thresholds
- **Alerting**: Prometheus-based performance alerts
- **API Integration**: RESTful endpoints for all operations

## Quick Start

### 1. Installation

```bash
# Install dependencies
cd backend_v2
pip install -r requirements.txt

# Run database migration
cd ../backend
alembic upgrade head
```

### 2. Configuration

Set environment variables:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/capsight"
export REDIS_URL="redis://localhost:6379/0" 
export MLFLOW_TRACKING_URI="http://localhost:5000"
export FEAST_REGISTRY="feast_registry.pb"
```

### 3. Run Your First Backtest

```bash
# Using CLI
python -m app.backtest.jobs.cli run-backtest \
  --name "my_first_backtest" \
  --model-version "v1.0.0" \
  --start-date "2023-01-01" \
  --end-date "2023-12-31" \
  --feature-sets "property_features,market_features" \
  --targets "price_change,investment_score"

# Or using API
curl -X POST "http://localhost:8000/backtest/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_first_backtest",
    "model_version": "v1.0.0", 
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "feature_sets": ["property_features", "market_features"],
    "prediction_targets": ["price_change", "investment_score"]
  }'
```

### 4. Schedule Recurring Backtests

```bash
# Schedule daily backtest at 2 AM
python -m app.backtest.jobs.cli schedule \
  --name "daily_model_validation" \
  --schedule daily \
  --hour 2 \
  --minute 0 \
  --config-file backtest_config.json
```

## Usage Examples

### Basic Backtest

```python
from app.backtest import BacktestConfig, run_full_backtest
from datetime import datetime, timedelta

# Configure backtest
config = BacktestConfig(
    name="property_price_validation",
    model_version="v2.1.0",
    start_date=datetime.now() - timedelta(days=90),
    end_date=datetime.now() - timedelta(days=1),
    time_slice_hours=24,
    feature_sets=["property_features", "market_features", "neighborhood_features"],
    prediction_targets=["price_change_7d", "investment_score"],
    metrics=["accuracy", "precision", "recall", "roc_auc", "sharpe_ratio"],
    sla_max_runtime_minutes=120
)

# Run backtest
results = await run_full_backtest(config)
print(f"Backtest completed: {results.accuracy:.3f} accuracy")
```

### Counterfactual Replay

```python
from app.backtest.replay import CounterfactualReplay

# Standard replay
replay = CounterfactualReplay(config, data_access)
results = await replay.run_replay("market_downturn_2022")

# What-if replay with adjusted parameters
what_if_params = {
    'model_threshold': 0.75,  # More conservative threshold
    'feature_weights': {
        'price_momentum': 1.2,  # Increase weight
        'market_sentiment': 0.8  # Decrease weight
    }
}

what_if_results = await replay.run_what_if_replay(
    "conservative_strategy", 
    what_if_params
)

print(f"Original ROI: {results.metrics['roi']:.2%}")
print(f"What-if ROI: {what_if_results.metrics['roi']:.2%}")
```

### Uplift Analysis

```python
from app.backtest.uplift import UpliftAnalysis

uplift = UpliftAnalysis(data_access)

# Compare model versions
results = await uplift.compare_model_versions(
    treatment_version="v2.1.0",
    control_version="v2.0.0", 
    start_date=datetime(2023, 6, 1),
    end_date=datetime(2023, 8, 31)
)

print(f"Model uplift: {results.uplift_percentage:.2%}")
print(f"Statistical significance: p={results.p_value:.4f}")
```

### Custom Metrics

```python
from app.backtest.metrics import BacktestMetrics

class CustomRealEstateMetrics(BacktestMetrics):
    def calculate_custom_metrics(self, predictions_df):
        """Custom real estate specific metrics."""
        
        # Days on market accuracy
        dom_accuracy = self._calculate_dom_accuracy(predictions_df)
        
        # Price per square foot error
        ppsf_error = self._calculate_ppsf_error(predictions_df)
        
        # Market segment performance
        segment_performance = self._segment_analysis(predictions_df)
        
        return {
            'dom_accuracy': dom_accuracy,
            'ppsf_mae': ppsf_error,
            'segment_performance': segment_performance
        }

# Use custom metrics
metrics_calc = CustomRealEstateMetrics()
custom_results = metrics_calc.calculate_custom_metrics(results_df)
```

## API Reference

### Core Endpoints

#### Create Backtest Run
```http
POST /backtest/runs
Content-Type: application/json

{
  "name": "string",
  "model_version": "string",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31", 
  "time_slice_hours": 24,
  "feature_sets": ["property_features"],
  "prediction_targets": ["price_change"],
  "metrics": ["accuracy", "roc_auc"],
  "sla_max_runtime_minutes": 120
}
```

#### Get Backtest Results
```http
GET /backtest/runs/{run_id}
```

#### List All Runs
```http
GET /backtest/runs?limit=50&offset=0&status=completed
```

#### Run Counterfactual Replay
```http
POST /backtest/replay
Content-Type: application/json

{
  "scenario_name": "string",
  "base_run_id": "string",
  "replay_params": {
    "model_version": "v2.0.0",
    "feature_adjustments": {}
  }
}
```

#### Generate Report
```http
POST /backtest/reports
Content-Type: application/json

{
  "run_id": "string",
  "format": "html|pdf|markdown",
  "include_charts": true,
  "sections": ["summary", "metrics", "analysis"]
}
```

### Job Management

#### Schedule Backtest Job
```http
POST /backtest/jobs/schedule
Content-Type: application/json

{
  "name": "string",
  "schedule_type": "daily|weekly|monthly|cron",
  "schedule_params": {"hour": 2, "minute": 0},
  "backtest_config": { /* BacktestConfig */ }
}
```

#### List Scheduled Jobs
```http
GET /backtest/jobs
```

#### Cancel Job
```http
DELETE /backtest/jobs/{job_id}
```

## Configuration

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `MLFLOW_TRACKING_URI`: MLflow server URL
- `FEAST_REGISTRY`: Path to Feast feature registry
- `BACKTEST_DEFAULT_WORKERS`: Default parallel workers (default: 4)
- `BACKTEST_MAX_RUNTIME_HOURS`: Global timeout (default: 12)
- `BACKTEST_ENABLE_CACHING`: Enable Redis caching (default: true)

### Configuration File Example

```yaml
# backtest_config.yaml
name: "comprehensive_validation"
model_version: "v2.1.0"
start_date: "2023-01-01"
end_date: "2023-12-31"
time_slice_hours: 24
feature_sets:
  - "property_features"
  - "market_features" 
  - "neighborhood_features"
  - "economic_indicators"
prediction_targets:
  - "price_change_7d"
  - "price_change_30d"
  - "investment_score"
  - "days_on_market"
metrics:
  - "accuracy"
  - "precision"
  - "recall"
  - "roc_auc"
  - "sharpe_ratio"
  - "max_drawdown"
sla_max_runtime_minutes: 180
parallel_workers: 8
enable_feature_importance: true
enable_drift_detection: true
notification_webhooks:
  - "https://hooks.slack.com/services/..."
```

## Monitoring & Alerting

### Grafana Dashboard

The system includes a comprehensive Grafana dashboard with:

- **Backtest runs over time**: Track execution frequency
- **Success rate by model**: Monitor model performance
- **Average accuracy trends**: Track model degradation
- **Investment return accuracy**: Real estate specific metrics  
- **SLA compliance**: Monitor performance thresholds
- **Feature drift scores**: Data quality monitoring
- **Active job counts**: Operational health

### Prometheus Metrics

Key metrics exposed:

- `backtest_runs_total`: Total backtest executions
- `backtest_runs_successful_total`: Successful runs
- `backtest_runtime_seconds`: Execution time
- `backtest_model_accuracy`: Accuracy scores
- `backtest_sla_breaches_total`: SLA violations
- `backtest_feature_drift_score`: Drift detection
- `backtest_uplift_percentage`: Uplift measurements

### Alerting Rules

Pre-configured alerts for:

- High failure rates (>10%)
- SLA breaches
- Model accuracy drops (<70%)
- High feature drift (>25%)
- Long runtimes (>1 hour)
- Stuck jobs (>30 minutes)
- Missing scheduled runs

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database connectivity
psql $DATABASE_URL -c "SELECT version();"

# Run pending migrations
alembic upgrade head
```

#### Feast Integration Issues
```bash
# Verify Feast registry
feast registry-dump

# Test feature serving
feast serve
```

#### Performance Issues
```bash
# Check Redis connectivity
redis-cli ping

# Monitor resource usage
docker stats capsight-backtest

# Review slow queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

#### Job Scheduling Problems
```bash
# List active jobs
python -m app.backtest.jobs.cli list-jobs

# Check job logs
python -m app.backtest.jobs.cli job-logs --job-id {job_id}

# Restart scheduler
python -m app.backtest.jobs.cli restart-scheduler
```

### Logging

The system provides structured logging at multiple levels:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log'),
        logging.StreamHandler()
    ]
)

# Log levels by component
logger = logging.getLogger('app.backtest')
logger.setLevel(logging.DEBUG)  # Detailed debugging
```

Log locations:
- Application logs: `logs/backtest.log`
- Job scheduler logs: `logs/scheduler.log`
- Database query logs: `logs/db_queries.log`
- Performance metrics: `logs/performance.log`

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_backtest_runs_created_at ON backtest_runs(created_at);
CREATE INDEX CONCURRENTLY idx_backtest_results_run_time ON backtest_results(run_id, time_slice);
CREATE INDEX CONCURRENTLY idx_prediction_snapshots_timestamp ON prediction_snapshots(timestamp, property_id);

-- Partition large tables by date
CREATE TABLE backtest_results_y2023 PARTITION OF backtest_results 
FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
```

### Redis Caching Strategy

```python
# Configure caching for expensive operations
cache_config = {
    'feature_cache_ttl': 3600,  # 1 hour
    'model_cache_ttl': 86400,   # 24 hours  
    'metrics_cache_ttl': 1800,  # 30 minutes
    'max_memory_policy': 'allkeys-lru'
}
```

### Parallel Processing

```python
# Configure worker pools
config = BacktestConfig(
    parallel_workers=min(8, cpu_count()),
    batch_size=1000,
    async_processing=True,
    memory_limit_gb=16
)
```

## Security Considerations

### Authentication & Authorization

```python
# API authentication
from fastapi.security import HTTPBearer
from app.core.auth import verify_token

security = HTTPBearer()

@router.post("/runs")
async def create_backtest_run(
    config: BacktestConfig,
    token: str = Depends(security)
):
    user = await verify_token(token)
    if not user.has_permission('backtest:create'):
        raise HTTPException(403, "Insufficient permissions")
    # ...
```

### Data Privacy

- **PII Handling**: Automatic detection and masking of personal data
- **Audit Logging**: Complete trail of all data access
- **Encryption**: At-rest and in-transit encryption
- **Retention Policies**: Automated data cleanup

### Network Security

```yaml
# docker-compose.yml security
services:
  backtest-api:
    networks:
      - internal
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
    environment:
      - ALLOWED_HOSTS=localhost,127.0.0.1
      - CORS_ORIGINS=https://app.capsight.com
```

## Testing

### Running Tests

```bash
# Run all tests
pytest app/backtest/tests/

# Run specific test categories
pytest -m unit            # Unit tests only
pytest -m integration     # Integration tests only  
pytest -m performance     # Performance tests only

# Run with coverage
pytest --cov=app.backtest --cov-report=html
```

### Test Configuration

```python
# conftest.py test setup
@pytest.fixture
async def test_data_access():
    # Setup test database
    async with TestDatabase() as db:
        yield BacktestDataAccess(db)

@pytest.fixture
def sample_backtest_config():
    return BacktestConfig(
        name="test_run",
        model_version="test_v1.0.0",
        # ... test configuration
    )
```

## Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  backtest-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/capsight
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
      
  db:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: capsight
      
  redis:
    image: redis:6-alpine
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: capsight-backtest
spec:
  replicas: 3
  selector:
    matchLabels:
      app: capsight-backtest
  template:
    metadata:
      labels:
        app: capsight-backtest
    spec:
      containers:
      - name: api
        image: capsight/backtest:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: backtest-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/capsight/backtest-system.git
cd backtest-system

# Setup development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Code Style

The project uses:
- **Black** for code formatting
- **isort** for import sorting  
- **flake8** for linting
- **mypy** for type checking

```bash
# Format code
black app/
isort app/

# Check style
flake8 app/
mypy app/
```

### Submitting Changes

1. Create feature branch: `git checkout -b feature/new-backtest-metric`
2. Make changes with tests
3. Run full test suite: `pytest`
4. Submit pull request with description

## Roadmap

### Version 2.1 (Current)
- ✅ Core backtesting pipeline
- ✅ Counterfactual replay
- ✅ What-if analysis mode
- ✅ Comprehensive monitoring
- ✅ Job scheduling

### Version 2.2 (Q1 2024)
- 🔄 A/B testing framework
- 🔄 Multi-armed bandit support
- 🔄 Advanced drift detection
- 🔄 Real-time model scoring

### Version 2.3 (Q2 2024)
- 📋 Federated learning support
- 📋 Cross-market backtesting
- 📋 Advanced causal inference
- 📋 MLOps integration

### Version 3.0 (Q3 2024)
- 📋 Real-time streaming backtests
- 📋 AutoML integration
- 📋 Advanced visualization
- 📋 Cloud-native architecture

## Support

### Documentation
- 📚 [API Documentation](API.md)
- 🚀 [Deployment Guide](DEPLOYMENT.md)
- 📊 [Analytics Guide](ANALYTICS.md)

### Community
- 💬 [Slack Channel](https://capsight.slack.com/channels/backtest)
- 🐛 [Issue Tracker](https://github.com/capsight/backtest/issues)
- 📧 [Support Email](mailto:backtest-support@capsight.com)

### Enterprise Support
Contact enterprise@capsight.com for:
- Custom deployment assistance
- Performance optimization
- Feature prioritization
- SLA agreements

## License

Copyright (c) 2024 CapSight Technologies. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use is prohibited.
