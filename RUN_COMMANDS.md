# CapSight Backtest System - Run Commands & Verification

## Quick Start Commands

### 1. Environment Setup
```powershell
# Navigate to backend_v2 directory
cd backend_v2

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
$env:DATABASE_URL = "postgresql://postgres:password@localhost:5432/capsight"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:MLFLOW_TRACKING_URI = "http://localhost:5000"
$env:FEAST_REGISTRY = "feast_registry.pb"
```

### 2. Database Setup
```powershell
# Navigate to backend directory for Alembic
cd ..\backend

# Run database migrations
alembic upgrade head

# Verify migration
psql $env:DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'backtest_%';"
```

### 3. Start Supporting Services
```powershell
# Start PostgreSQL (if not running)
# Option 1: Docker
docker run -d --name capsight-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=capsight -p 5432:5432 postgres:13

# Start Redis (if not running) 
# Option 1: Docker
docker run -d --name capsight-redis -p 6379:6379 redis:6-alpine

# Start MLflow (if not running)
# Option 1: Local
mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns

# Option 2: Docker Compose (recommended)
cd ..
docker-compose up -d
```

### 4. Run Your First Backtest

#### Option A: Using CLI
```powershell
cd backend_v2

# Basic backtest
python -m app.backtest.jobs.cli run-backtest `
  --name "first_backtest_test" `
  --model-version "v1.0.0" `
  --start-date "2023-06-01" `
  --end-date "2023-08-31" `
  --feature-sets "property_features,market_features" `
  --targets "price_change,investment_score" `
  --metrics "accuracy,roc_auc,sharpe_ratio"

# Advanced backtest with all options
python -m app.backtest.jobs.cli run-backtest `
  --name "comprehensive_validation" `
  --model-version "v2.1.0" `
  --start-date "2023-01-01" `
  --end-date "2023-12-31" `
  --time-slice-hours 24 `
  --feature-sets "property_features,market_features,neighborhood_features" `
  --targets "price_change_7d,price_change_30d,investment_score" `
  --metrics "accuracy,precision,recall,roc_auc,sharpe_ratio,max_drawdown" `
  --workers 4 `
  --max-runtime 180
```

#### Option B: Using Python Script
```powershell
# Create and run a Python script
@"
import asyncio
from datetime import datetime, timedelta
from app.backtest import BacktestConfig
from app.backtest.pipeline import run_full_backtest

async def main():
    config = BacktestConfig(
        name="python_api_test",
        model_version="v1.0.0",
        start_date=datetime.now() - timedelta(days=90),
        end_date=datetime.now() - timedelta(days=1),
        time_slice_hours=24,
        feature_sets=["property_features", "market_features"],
        prediction_targets=["price_change", "investment_score"],
        metrics=["accuracy", "roc_auc", "sharpe_ratio"]
    )
    
    results = await run_full_backtest(config)
    print(f"Backtest completed: {results}")

if __name__ == "__main__":
    asyncio.run(main())
"@ | Out-File -FilePath run_backtest.py

python run_backtest.py
```

#### Option C: Using REST API
```powershell
# Start the FastAPI server
cd backend_v2
uvicorn app.main:app --reload --port 8000

# In another terminal, call the API
Invoke-RestMethod -Uri "http://localhost:8000/backtest/runs" `
  -Method POST `
  -ContentType "application/json" `
  -Body @"
{
  "name": "api_test_backtest",
  "model_version": "v1.0.0",
  "start_date": "2023-06-01",
  "end_date": "2023-08-31",
  "time_slice_hours": 24,
  "feature_sets": ["property_features", "market_features"],
  "prediction_targets": ["price_change", "investment_score"],
  "metrics": ["accuracy", "roc_auc", "sharpe_ratio"],
  "sla_max_runtime_minutes": 120
}
"@
```

### 5. Run Counterfactual Replay

#### Standard Replay
```powershell
python -m app.backtest.jobs.cli run-replay `
  --scenario-name "market_downturn_2022" `
  --base-run-id "your-backtest-run-id" `
  --start-date "2022-03-01" `
  --end-date "2022-09-30"
```

#### What-if Replay
```powershell
python -m app.backtest.jobs.cli run-what-if-replay `
  --scenario-name "conservative_strategy" `
  --base-run-id "your-backtest-run-id" `
  --adjustments "model_threshold:0.8,risk_weight:1.2"
```

### 6. Schedule Recurring Backtests

```powershell
# Daily backtest at 2 AM
python -m app.backtest.jobs.cli schedule `
  --name "daily_model_validation" `
  --schedule daily `
  --hour 2 `
  --minute 0 `
  --config-file daily_backtest_config.json

# Weekly comprehensive validation
python -m app.backtest.jobs.cli schedule `
  --name "weekly_full_validation" `
  --schedule weekly `
  --day-of-week 1 `
  --hour 1 `
  --minute 0 `
  --config-file weekly_backtest_config.json
```

### 7. Generate Reports

```powershell
# Generate HTML report
python -m app.backtest.jobs.cli generate-report `
  --run-id "your-backtest-run-id" `
  --format html `
  --output "reports/backtest_report.html"

# Generate PDF report
python -m app.backtest.jobs.cli generate-report `
  --run-id "your-backtest-run-id" `
  --format pdf `
  --output "reports/backtest_report.pdf" `
  --include-charts
```

### 8. Run Tests

```powershell
# Run all tests
cd backend_v2
pytest app/backtest/tests/ -v

# Run specific test categories
pytest app/backtest/tests/ -v -m unit            # Unit tests only
pytest app/backtest/tests/ -v -m integration     # Integration tests only  
pytest app/backtest/tests/ -v -m performance     # Performance tests only

# Run with coverage
pytest app/backtest/tests/ --cov=app.backtest --cov-report=html
```

### 9. Monitoring Setup

#### Start Prometheus & Grafana
```powershell
# Using Docker Compose
cd backend_v2/app/backtest/grafana
docker-compose up -d prometheus grafana

# Access Grafana at http://localhost:3000 (admin/admin)
# Import dashboard from backtest_dashboard.json
```

#### View Metrics
```powershell
# Check Prometheus metrics
Invoke-WebRequest -Uri "http://localhost:8000/metrics"

# Check backtest-specific metrics
curl http://localhost:9090/api/v1/query?query=backtest_runs_total
```

## Verification Checklist

### ✅ Environment Verification
- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed without errors
- [ ] Environment variables set correctly
- [ ] Database accessible (PostgreSQL running)
- [ ] Redis accessible
- [ ] MLflow server running

### ✅ Database Verification
```powershell
# Check database connection
python -c "
import asyncio
from app.backtest.data_access import BacktestDataAccess

async def test_db():
    da = BacktestDataAccess()
    result = await da.health_check()
    print(f'Database health: {result}')

asyncio.run(test_db())
"

# Verify tables exist
psql $env:DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'backtest_%';"

# Expected tables:
# - backtest_runs
# - backtest_results  
# - prediction_snapshots
# - metrics_summary
# - model_snapshots
# - backtest_jobs
# - feature_sets
# - backtest_audit_logs
```

### ✅ Backtest Pipeline Verification
```powershell
# Test basic backtest functionality
python -c "
import asyncio
from datetime import datetime, timedelta
from app.backtest import BacktestConfig
from app.backtest.pipeline import run_full_backtest

async def verify_backtest():
    config = BacktestConfig(
        name='verification_test',
        model_version='v1.0.0',
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now() - timedelta(days=1),
        time_slice_hours=24,
        feature_sets=['property_features'],
        prediction_targets=['price_change'],
        metrics=['accuracy']
    )
    
    results = await run_full_backtest(config)
    print(f'Verification backtest status: {results[\"status\"]}')
    return results['status'] == 'completed'

result = asyncio.run(verify_backtest())
print(f'Pipeline verification: {\"✅ PASSED\" if result else \"❌ FAILED\"}')
"
```

### ✅ API Verification
```powershell
# Start API server
Start-Process powershell -ArgumentList "cd backend_v2; uvicorn app.main:app --port 8000"
Start-Sleep -Seconds 5

# Test health endpoint
$health = Invoke-RestMethod -Uri "http://localhost:8000/health"
Write-Host "API Health: $($health.status)"

# Test backtest endpoints
$backtest_response = Invoke-RestMethod -Uri "http://localhost:8000/backtest/runs" -Method GET
Write-Host "Backtest API: ✅ WORKING" -ForegroundColor Green

# Test metrics endpoint
$metrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics"
Write-Host "Metrics endpoint: ✅ WORKING" -ForegroundColor Green
```

### ✅ Feature Loading Verification
```powershell
python -c "
import asyncio
from app.backtest.feature_loader import FeatureLoader
from app.backtest import BacktestConfig
from datetime import datetime

async def verify_features():
    config = BacktestConfig(
        name='test',
        model_version='v1.0.0',
        start_date=datetime.now(),
        end_date=datetime.now(),
        feature_sets=['property_features']
    )
    
    loader = FeatureLoader(config)
    features = await loader.load_features(
        feature_sets=['property_features'],
        entities=['prop_1', 'prop_2'],
        as_of_time=datetime.now()
    )
    
    print(f'Feature loading: {\"✅ PASSED\" if not features.empty else \"⚠️  FALLBACK MODE\"}')
    return True

asyncio.run(verify_features())
"
```

### ✅ Job Scheduling Verification
```powershell
# Test job scheduling
python -c "
import asyncio
from app.backtest.jobs.scheduler import BacktestScheduler
from app.backtest.data_access import BacktestDataAccess

async def verify_scheduler():
    data_access = BacktestDataAccess()
    scheduler = BacktestScheduler(data_access)
    
    # Start scheduler
    await scheduler.start()
    print('Scheduler: ✅ STARTED')
    
    # List jobs
    jobs = await scheduler.list_jobs()
    print(f'Active jobs: {len(jobs)}')
    
    return True

asyncio.run(verify_scheduler())
"
```

### ✅ Report Generation Verification
```powershell
# Test report generation
python -c "
from app.backtest.reports.renderer import ReportRenderer
import tempfile

renderer = ReportRenderer()
report_data = {
    'title': 'Test Report',
    'summary': {'accuracy': 0.85},
    'charts': []
}

with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
    success = renderer.render_html_report(report_data, f.name)
    print(f'Report generation: {\"✅ PASSED\" if success else \"❌ FAILED\"}')
"
```

### ✅ Monitoring Verification
```powershell
# Check if Prometheus metrics are exposed
$metrics_response = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -UseBasicParsing
if ($metrics_response.Content -match "backtest_runs_total") {
    Write-Host "Prometheus metrics: ✅ WORKING" -ForegroundColor Green
} else {
    Write-Host "Prometheus metrics: ❌ NOT FOUND" -ForegroundColor Red
}

# Test Grafana dashboard (if running)
try {
    $grafana_response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing
    Write-Host "Grafana: ✅ ACCESSIBLE" -ForegroundColor Green
} catch {
    Write-Host "Grafana: ⚠️  NOT RUNNING" -ForegroundColor Yellow
}
```

### ✅ Performance Verification
```powershell
# Run performance tests
pytest app/backtest/tests/ -v -m performance

# Check memory usage during backtest
python -c "
import asyncio
import psutil
import os
from datetime import datetime, timedelta
from app.backtest import BacktestConfig
from app.backtest.pipeline import run_full_backtest

async def performance_check():
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    config = BacktestConfig(
        name='performance_test',
        model_version='v1.0.0',
        start_date=datetime.now() - timedelta(days=14),
        end_date=datetime.now() - timedelta(days=1),
        time_slice_hours=24,
        feature_sets=['property_features'],
        prediction_targets=['price_change'],
        metrics=['accuracy']
    )
    
    start_time = datetime.now()
    results = await run_full_backtest(config)
    end_time = datetime.now()
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    runtime = (end_time - start_time).total_seconds()
    
    print(f'Runtime: {runtime:.2f} seconds')
    print(f'Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB')
    print(f'Performance: {\"✅ GOOD\" if runtime < 60 else \"⚠️  SLOW\"}')

asyncio.run(performance_check())
"
```

## Expected Output Examples

### Successful Backtest Output
```
INFO - Starting backtest: first_backtest_test
INFO - Created backtest run: btr_20241201_143052_abc123
INFO - Generated 92 time slices
INFO - Processing time slice 1/92: 2023-06-01 to 2023-06-02
...
INFO - Stored 8,432 backtest results  
INFO - Backtest completed successfully in 45.23s

{
  "run_id": "btr_20241201_143052_abc123",
  "status": "completed", 
  "runtime_seconds": 45.23,
  "metrics": {
    "overall_accuracy": 0.847,
    "overall_roc_auc": 0.923,
    "overall_sharpe_ratio": 1.67,
    "total_predictions": 8432
  },
  "results_count": 8432,
  "report_path": "reports/backtest_report_btr_20241201_143052_abc123_20241201_143137.html",
  "time_slices_processed": 92
}
```

### Successful API Response
```json
{
  "run_id": "btr_20241201_143052_def456",
  "name": "api_test_backtest",
  "model_version": "v1.0.0",
  "status": "running",
  "created_at": "2024-12-01T14:30:52.123456Z",
  "config": {
    "name": "api_test_backtest",
    "model_version": "v1.0.0",
    "start_date": "2023-06-01",
    "end_date": "2023-08-31"
  }
}
```

## Troubleshooting Common Issues

### Issue: Database Connection Failed
```powershell
# Check if PostgreSQL is running
Get-Process postgres -ErrorAction SilentlyContinue

# Test connection manually
psql "postgresql://postgres:password@localhost:5432/capsight" -c "SELECT version();"

# Solution: Start PostgreSQL or check connection string
```

### Issue: Redis Connection Failed  
```powershell
# Check if Redis is running
redis-cli ping

# Solution: Start Redis
docker run -d -p 6379:6379 redis:6-alpine
```

### Issue: Import Errors
```powershell
# Check if in correct directory
pwd
# Should be in backend_v2/

# Check if virtual environment is activated
pip list | grep fastapi

# Solution: Activate venv and install requirements
venv\Scripts\activate
pip install -r requirements.txt
```

### Issue: Alembic Migration Failed
```powershell
# Check current migration status
cd ..\backend
alembic current

# Check for conflicts
alembic history

# Solution: Reset and re-run
alembic downgrade base
alembic upgrade head
```

## Success Criteria

✅ **System is ready when:**
- All dependencies installed without errors
- Database tables created successfully  
- Basic backtest runs and completes
- API endpoints respond correctly
- Metrics are collected and exposed
- Reports generate successfully
- Job scheduling works
- Tests pass

✅ **Performance benchmarks:**
- Backtest with 90 days of data completes in < 2 minutes
- Memory usage stays under 2GB during execution
- API response times < 500ms for most endpoints
- Database queries execute in < 100ms average

✅ **Production readiness:**
- All tests passing
- Monitoring dashboards functional
- Alerting rules configured
- Error handling robust
- Logging comprehensive
- Documentation complete
