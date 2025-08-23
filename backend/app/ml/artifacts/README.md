# CapSight ML Artifacts

This directory contains all ML model artifacts, metrics, and outputs.

## Directory Structure

```
artifacts/
├── models/              # Trained model files
│   ├── rates_forecast/  # Interest rate forecasting models
│   ├── caprate_forecast/# Cap rate forecasting models  
│   ├── noi_rent_forecast/# NOI and rent forecasting models
│   └── ensemble_score/  # Ensemble scoring models
├── metrics/             # Performance metrics and backtest results
├── plots/               # Visualization outputs
└── macro_sample.csv     # Sample macro economic data
```

## Model Versioning

Models are versioned by timestamp in format: `YYYYMMDD_HHMMSS`

Each model directory contains:
- `*.pkl` - Serialized model files
- `metadata.json` - Model configuration and performance metrics

## Training History

### Latest Training Session
- **Date**: Not yet trained
- **Models**: 0 trained models
- **Performance**: No metrics available

## Retraining Instructions

### Full Pipeline Training
```bash
cd backend
python -m app.ml.jobs.train_all --seed-demo --horizon 6 --save-artifacts
```

### Individual Model Training
```bash
# Rates forecasting
python -c "from app.ml.pipelines import RatesForecastPipeline; p = RatesForecastPipeline(); p.fit(macro_data); p.save_models()"

# Cap rate forecasting
python -c "from app.ml.pipelines import CapRateForecastPipeline; p = CapRateForecastPipeline(); p.fit(property_data); p.save_models()"

# NOI/Rent forecasting
python -c "from app.ml.pipelines import NoiRentForecastPipeline; p = NoiRentForecastPipeline(); p.fit(property_data); p.save_models()"

# Ensemble scoring
python -c "from app.ml.pipelines import EnsembleScoringPipeline; p = EnsembleScoringPipeline(); p.fit(property_data, rates, caprates, noi_rent); p.save_models()"
```

## Performance Monitoring

### Key Metrics to Monitor
- **Rates Forecast MAE**: < 0.005 (50 basis points)
- **Cap Rate Forecast MAE**: < 0.01 (100 basis points)  
- **NOI Forecast MAPE**: < 15%
- **Scoring Rank IC**: > 0.1 (positive correlation)

### Model Refresh Schedule
- **Daily**: Update forecasts with latest data
- **Weekly**: Retrain ensemble scoring model
- **Monthly**: Retrain all forecasting models
- **Quarterly**: Full model validation and hyperparameter tuning

## Data Requirements

### Minimum Data for Training
- **Time Series Length**: 12+ months for training
- **Property Count**: 10+ properties per market/asset type
- **Macro Data**: Monthly rates data
- **Update Frequency**: Monthly for production models

### Data Quality Checks
- No more than 20% missing values
- Reasonable value ranges (cap rates 3-12%, NOI > 0)
- Consistent time series (no large gaps)

## Troubleshooting

### Common Issues
1. **Prophet Installation**: Requires cmdstan, may need conda install
2. **Insufficient Data**: Use synthetic data for testing
3. **Model Loading Errors**: Check model version compatibility
4. **Memory Issues**: Reduce batch size or use sampling

### Support
- Check logs in `app/ml/` modules
- Validate data quality with `datasets.py`
- Use `backtest.py` for model validation
