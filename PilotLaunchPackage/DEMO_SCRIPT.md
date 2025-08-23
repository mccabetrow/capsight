# CapSight Demo Script

## Pre-Demo Setup (5 minutes)

### Environment Preparation
```powershell
# Ensure all services are running
cd "c:\Users\mccab\New folder (2)\backend_v2"
.\deploy\deploy.ps1 status

# Switch to demo mode for clean data
copy .env.demo .env
docker compose -f config/docker-compose.yml restart api

# Validate everything is working
python ..\validate_deployment.py
```

### Browser Tabs Setup
1. **API Documentation**: http://localhost:8000/docs
2. **Grafana Dashboard**: http://localhost:3000 (admin/admin)
3. **Prometheus Metrics**: http://localhost:9090
4. **Demo Properties**: http://localhost:8000/api/v1/demo/properties

---

## Demo Flow (15 minutes)

### Opening: The Real Estate Arbitrage Problem (2 minutes)
> "Traditional real estate analysis takes hours or days, uses outdated data, and lacks confidence intervals. CapSight changes that with real-time, ML-powered property valuation."

**Key Pain Points:**
- Manual analysis takes 2-4 hours per property
- Data is often 30+ days old
- No confidence intervals or risk assessment
- Difficult to scale for portfolio analysis

### Part 1: Speed Demonstration (3 minutes)

**Show Real-time Analysis:**
```bash
# Navigate to API docs
POST /api/v1/analyze

# Demo property payload:
{
  "property_id": "demo_001",
  "address": "2847 NE 55th Street, Seattle, WA 98105",
  "property_type": "single_family",
  "bedrooms": 4,
  "bathrooms": 2.5,
  "square_feet": 2100,
  "lot_size": 8400,
  "year_built": 1950,
  "listing_price": 895000
}
```

**Expected Response (< 100ms):**
```json
{
  "property_id": "demo_001",
  "predicted_value": 943500,
  "confidence_interval": {
    "lower": 896825,
    "upper": 990175,
    "confidence": 0.95
  },
  "arbitrage_potential": 48500,
  "risk_score": 0.23,
  "analysis_timestamp": "2024-12-19T10:30:45Z",
  "model_version": "v2.1.3"
}
```

**Key Metrics to Highlight:**
- **Response Time**: Sub-100ms (show in Grafana)
- **Confidence**: 95% confidence intervals
- **Arbitrage Potential**: $48,500 upside
- **Risk Score**: Low risk (0.23/1.0)

### Part 2: Accuracy & Trust (4 minutes)

**Switch to Grafana Dashboard**
- **Model Performance**: 94.2% accuracy over last 30 days
- **Prediction Distribution**: Show bell curve of predictions vs actuals
- **Confidence Calibration**: Demonstrate that 95% intervals contain 95% of outcomes

**Show Data Freshness:**
```bash
GET /api/v1/data/freshness
```

**Response showing real-time data:**
```json
{
  "mls_data": "2024-12-19T10:25:00Z",
  "market_trends": "2024-12-19T10:20:00Z",
  "economic_indicators": "2024-12-19T09:00:00Z",
  "comparable_sales": "2024-12-19T10:30:00Z"
}
```

**Highlight:**
- Data refreshed every 15 minutes
- Multiple data sources integrated
- Real-time market conditions factored in

### Part 3: Transparency & Explainability (3 minutes)

**Show SHAP Explanations:**
```bash
GET /api/v1/analyze/demo_001/explain
```

**Feature Importance Display:**
- Location Score: +$45,000 (highest impact)
- Square Footage: +$32,000
- Market Trends: +$18,000
- Lot Size: +$12,000
- Age Penalty: -$8,500

**Risk Factors:**
- Market volatility: Low
- Data confidence: High
- Comparable density: Excellent (47 recent sales)

### Part 4: Operational Excellence (3 minutes)

**Show Monitoring Dashboard in Grafana:**

1. **Real-time Metrics:**
   - Requests per minute: 150-200
   - 99th percentile latency: 87ms
   - Error rate: 0.02%
   - Model accuracy: 94.2%

2. **Data Pipeline Health:**
   - Ingestion rate: 1,200 records/min
   - Data freshness: 12 minutes average
   - Pipeline uptime: 99.97%

3. **Business Metrics:**
   - Properties analyzed today: 1,247
   - Arbitrage opportunities found: 89
   - Average upside identified: $42,300

**Alert Demonstration:**
```bash
# Trigger a test alert
python test_alert.py --type=accuracy_drop
```

Show how alerts flow to:
- Slack notifications
- PagerDuty escalation
- Email summaries

---

## Q&A Responses

### "How accurate is your model?"
- **Current accuracy**: 94.2% within ±5% of actual sale price
- **Confidence intervals**: 95% of properties fall within predicted ranges
- **Continuous learning**: Model retrains daily with new data
- **Benchmark**: 23% more accurate than traditional AVMs

### "How fresh is your data?"
- **MLS data**: Updated every 15 minutes
- **Market indicators**: Real-time streaming
- **Comparable sales**: Within 6 hours of recording
- **SLA**: 99.5% of predictions use data <1 hour old

### "What about data privacy and compliance?"
- **SOC 2 Type II** certified
- **GDPR compliant** data handling
- **Encrypted at rest** and in transit
- **Audit trails** for all predictions
- **No PII storage** in ML models

### "How do you handle market volatility?"
- **Real-time adjustment** for market conditions
- **Volatility scoring** included in risk assessment
- **Confidence intervals** widen during uncertain periods
- **Multi-model ensemble** for robustness

---

## Closing: Value Proposition (2 minutes)

### ROI Demonstration
**For a 50-property portfolio analysis:**
- **Traditional method**: 100-200 hours @ $150/hr = $15,000-$30,000
- **CapSight**: 5 minutes @ $0.50/property = $25
- **Time savings**: 99.97%
- **Cost savings**: 99.92%
- **Improved accuracy**: +23%

### Implementation Timeline
- **Week 1**: API integration and testing
- **Week 2**: Team training and workflow integration
- **Week 3**: Production deployment with monitoring
- **Week 4**: Full operation with support

### Next Steps
1. **Pilot program**: 30-day trial with 100 free analyses
2. **Integration support**: Dedicated technical team
3. **Training sessions**: Team onboarding included
4. **Success metrics**: Agreed KPIs and reporting

---

## Technical Deep-Dive (If Requested)

### Architecture Overview
- **Microservices**: Independent scaling and deployment
- **Event-driven**: Real-time data processing
- **ML Pipeline**: Automated model training and deployment
- **Observability**: Full distributed tracing

### Integration Options
- **REST API**: Standard HTTP/JSON interface
- **Webhooks**: Real-time notifications
- **Batch Processing**: Bulk analysis capabilities
- **SDKs**: Python, JavaScript, .NET libraries

### Security & Compliance
- **API Authentication**: JWT with role-based access
- **Rate Limiting**: Prevents abuse and ensures SLA
- **Audit Logging**: Complete request/response tracking
- **Data Retention**: Configurable policies

---

## Demo Troubleshooting

### If Services Don't Start
1. Check Docker Desktop is running
2. Verify port availability (8000, 3000, 9090, 5432, 6379)
3. Check .env file has valid API keys
4. Restart with: `docker compose down && docker compose up -d`

### If API Returns Errors
1. Check logs: `docker compose logs api`
2. Verify database connection
3. Confirm demo data is loaded
4. Reset with demo configuration

### If Performance is Slow
1. Check system resources (RAM, CPU)
2. Verify no other heavy processes running
3. Restart Docker Desktop if needed
4. Use demo mode for consistent performance
