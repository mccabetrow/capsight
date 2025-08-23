# CapSight Backend v2 - Real-Time Predictive Analytics

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)

Production-ready backend system for **CapSight** - a commercial real estate arbitrage analytics platform. Delivers real-time property predictions with strict accuracy and freshness SLAs.

## 🎯 Key Features

### Real-Time Analytics
- **Sub-100ms inference** for property-level predictions
- **Streaming data ingestion** from 10+ financial/alternative data sources
- **Feature store** with microsecond-level serving
- **Champion-challenger model deployment** with A/B testing

### ML Pipeline
- **Ensemble models** (LightGBM + XGBoost + Random Forest) for cap rate prediction
- **Time series forecasting** (Prophet) for NOI growth
- **Conformal prediction** for calibrated uncertainty intervals
- **SHAP explanations** for model interpretability
- **Real-time drift detection** and model retraining

### Production SLAs
- **Accuracy**: Cap-rate MAE <75 BPS, NOI MAPE <12%, Top-decile precision >60%
- **Freshness**: Treasury data <15min, Mortgage pricing <60min, Mobility data <24hrs
- **Availability**: 99.9% uptime with health monitoring and alerting
- **Latency**: <100ms single property, <5s batch (100 properties)

## 🏗 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Ingestion     │    │  Feature Store  │
│                 │    │                 │    │                 │
│ • FRED API      │────│ • Kafka Streams │────│ • Feast         │
│ • Bloomberg     │    │ • Redis Streams │    │ • Redis Cache   │
│ • SafeGraph     │    │ • Batch ETL     │    │ • PostgreSQL    │
│ • REIT Data     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ML Models     │    │   Serving API   │    │   Monitoring    │
│                 │    │                 │    │                 │
│ • Ensemble      │────│ • FastAPI       │────│ • Prometheus    │
│ • Prophet       │    │ • GraphQL       │    │ • Grafana       │
│ • MLflow        │    │ • WebSocket     │    │ • PagerDuty     │
│ • Model Registry│    │                 │    │ • Drift Detection│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- 8GB+ RAM, 4+ CPU cores

### Local Development
```bash
# Clone repository
git clone <repository-url>
cd backend_v2

# Setup environment
cp .env.example .env
# Edit .env with your API keys and configuration

# Install dependencies
pip install -r requirements.txt

# Start infrastructure services
docker-compose -f config/docker-compose.yml up -d postgres redis kafka

# Run application
cd src
python main.py
```

The API will be available at `http://localhost:8000`

### Production Deployment
```bash
# Deploy complete stack
./deploy/deploy.sh deploy

# Check status
./deploy/deploy.sh status

# View logs
./deploy/deploy.sh logs

# Scale application
./deploy/deploy.sh scale 3
```

## 📊 API Endpoints

### Property Predictions
```bash
# Single property prediction
curl -X POST http://localhost:8000/v1/predict/property \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "prop_123",
    "market_id": "atlanta_msa", 
    "current_noi": 2500000,
    "current_caprate": 0.065,
    "property_type": "multifamily"
  }'

# Response
{
  "property_id": "prop_123",
  "prediction_timestamp": "2024-01-15T10:30:00Z",
  "model_version": "ensemble_v2.1",
  "implied_caprate": 0.058,
  "caprate_confidence_lower": 0.052,
  "caprate_confidence_upper": 0.064,
  "noi_growth_12m": 0.035,
  "arbitrage_score": 72.5,
  "arbitrage_percentile": 83.2,
  "key_drivers": [
    "10-year Treasury rate",
    "Market cap rate trend",
    "Local demand indicators"
  ],
  "shap_values": {
    "treasury_10y_rate": 0.15,
    "market_caprate_trend": -0.08,
    "local_foot_traffic": 0.05
  },
  "prediction_latency_ms": 45.2,
  "data_freshness_score": 0.94,
  "model_confidence": 0.87
}
```

### Batch Predictions
```bash
# Batch prediction (up to 100 properties)
curl -X POST http://localhost:8000/v1/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "properties": [
      {"property_id": "prop_1", "market_id": "atlanta_msa"},
      {"property_id": "prop_2", "market_id": "dallas_msa"}
    ],
    "include_explanations": true,
    "confidence_level": 0.8
  }'
```

### System Health
```bash
# Health check
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8000/metrics

# Model status
curl http://localhost:8000/v1/models/status
```

## 🔧 Configuration

### Environment Variables
```bash
# Core settings
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0

# External APIs
FRED_API_KEY=your_fred_api_key
BLOOMBERG_API_KEY=your_bloomberg_key
SAFEGRAPH_API_KEY=your_safegraph_key

# ML/Feature Store
MLFLOW_TRACKING_URI=http://mlflow:5000
FEAST_REPO_PATH=./feature_repo
MODEL_REGISTRY_S3_BUCKET=capsight-models

# SLA Targets (optional overrides)
ACCURACY_CAPRATE_MAE_BPS=75.0
FRESHNESS_INTRADAY_RATES_MINUTES=15
```

### Feature Flags
- `ENABLE_CHALLENGER_MODELS`: A/B test new models
- `ENABLE_REAL_TIME_INFERENCE`: Real-time vs batch predictions
- `ENABLE_FEEDBACK_LOOP`: Collect feedback for model improvement

## 📈 Monitoring & Observability

### Metrics
- **Accuracy metrics**: MAE, MAPE, precision, calibration
- **Freshness metrics**: Data age by source, staleness alerts
- **Latency metrics**: P50/P95/P99 prediction latencies
- **Drift metrics**: Feature drift detection, model performance decay

### Dashboards
- **Grafana**: Real-time operational dashboards
- **MLflow**: Model performance and experiment tracking
- **Health checks**: System health and SLA compliance

### Alerting
- **PagerDuty integration** for critical SLA breaches
- **Slack notifications** for model drift and data staleness
- **Email alerts** for accuracy degradation

## 🧪 Testing

### Run Test Suite
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
cd src
python -m pytest capsight/tests/ -v

# Run specific test categories
python -m pytest capsight/tests/ -m "not integration" -v  # Unit tests only
python -m pytest capsight/tests/ -k "test_api" -v        # API tests only
```

### Test Coverage
- **Unit tests**: Model training, feature computation, accuracy monitoring
- **Integration tests**: End-to-end prediction pipeline
- **API tests**: All REST endpoints with validation
- **Performance tests**: Latency and throughput under load

## 🔐 Security

### Authentication & Authorization
- **JWT tokens** for API access
- **Rate limiting** (configurable per client)
- **CORS policies** for cross-origin requests

### Data Security
- **Encrypted connections** (TLS/SSL)
- **Environment-based secrets** management
- **Database encryption** at rest
- **Audit logging** for compliance

## 📦 Deployment Options

### Docker Compose (Recommended)
- Complete stack deployment
- Development and production configurations
- Automatic service discovery and networking

### Kubernetes
```bash
# Deploy to Kubernetes
kubectl apply -f deploy/k8s/
```

### Manual Installation
```bash
# Install system dependencies
sudo apt-get update && sudo apt-get install -y python3.11 redis postgresql

# Install Python dependencies
pip install -r requirements.txt

# Configure services
# ... (see deployment documentation)
```

## 🛠 Development

### Project Structure
```
backend_v2/
├── src/capsight/           # Main application
│   ├── core/              # Configuration, utilities
│   ├── ingestion/         # Data ingestion pipelines
│   ├── models/            # ML models & feature store
│   ├── api/               # FastAPI endpoints
│   ├── monitoring/        # Health checks & metrics
│   └── tests/             # Test suite
├── config/                # Configuration files
├── deploy/                # Deployment scripts & configs
└── requirements.txt       # Python dependencies
```

### Adding New Models
1. **Implement model class** inheriting from `BaseModel`
2. **Register in model registry** with MLflow
3. **Update prediction service** to load new model
4. **Add tests** for model training and inference
5. **Update API documentation**

### Adding New Data Sources
1. **Implement data source class** inheriting from `DataSource`
2. **Add to streaming service** in `ingestion/streams.py`
3. **Configure Kafka topics** and feature groups
4. **Add freshness monitoring** thresholds
5. **Update feature store** schema

## 📋 SLA Compliance

### Accuracy Targets
- **Cap-rate MAE**: <75 basis points
- **NOI Growth MAPE**: <12%
- **Top-decile Precision**: >60%
- **Confidence Calibration**: <5% miscalibration

### Freshness Targets  
- **Treasury rates**: <15 minutes
- **Mortgage pricing**: <60 minutes
- **Mobility/alternative data**: <24 hours
- **News sentiment**: <60 minutes

### Performance Targets
- **Single prediction**: <100ms P95
- **Batch predictions**: <5s for 100 properties
- **System availability**: >99.9% uptime
- **Data pipeline**: <30s end-to-end latency

## 🐛 Troubleshooting

### Common Issues

**Prediction latency too high**
```bash
# Check feature store performance
curl http://localhost:8000/health | jq '.checks.feature_store'

# Scale Redis cache
docker-compose up -d --scale redis=2
```

**Data freshness alerts**
```bash
# Check data source status
curl http://localhost:8000/health | jq '.checks.data_freshness'

# Restart ingestion service
./deploy/deploy.sh restart
```

**Model accuracy degradation**
```bash
# Check model performance
curl http://localhost:8000/v1/models/status

# View accuracy metrics
curl http://localhost:8000/metrics | grep model_accuracy
```

### Logs
```bash
# Application logs
./deploy/deploy.sh logs capsight-api

# Infrastructure logs
docker-compose logs kafka redis postgres
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Add tests** for new functionality
4. **Run test suite**: `python -m pytest`
5. **Submit pull request**

### Code Standards
- **Python**: Black formatting, type hints, docstrings
- **Tests**: Minimum 80% coverage for new code
- **Documentation**: Update README and API docs
- **Performance**: Benchmark critical paths

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Documentation**: `/docs` directory for detailed guides
- **Monitoring**: Grafana dashboards for operational insights

---

**CapSight Backend v2** - Powering real-time commercial real estate arbitrage with production-grade ML and strict SLA compliance.
