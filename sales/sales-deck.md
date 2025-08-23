---
pdf_options:
  format: A4
  margin: 20mm
  printBackground: true
  displayHeaderFooter: true
  headerTemplate: '<div style="font-size: 10px; color: #666; width: 100%; text-align: center;">CapSight - Industrial CRE Valuation Platform</div>'
  footerTemplate: '<div style="font-size: 10px; color: #666; width: 100%; text-align: center;">Confidential & Proprietary | Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'
---

<div style="page-break-after: always;">
<div style="text-align: center; margin-top: 150px;">

# CapSight
## Industrial CRE Valuation Platform

### Bulletproof Accuracy • Enterprise Reliability • Instant Results

---

**Industrial Real Estate Valuations Reimagined**  
Powered by robust estimators, conformal prediction, and 10,000+ verified sales

*August 2025 | Version 1.0*

</div>
</div>

---

## The Problem: Traditional Valuations Are Broken

### Current Market Pain Points

**🕒 Slow & Expensive**
- Appraisals take 2-4 weeks, cost $3,000-$8,000
- Manual comparable selection and analysis
- Inconsistent methodologies across appraisers

**📊 Unreliable Results**  
- Wide variance in appraisal outcomes (±15-20%)
- Limited comparable sales data
- No confidence intervals or uncertainty quantification

**🔍 Black Box Process**
- Minimal transparency in valuation methodology
- No audit trail or explainability
- Difficult to challenge or verify results

**💰 High Stakes Decisions**
- $5M-$50M transactions based on uncertain valuations
- Portfolio marking and loan underwriting at risk
- REITs need frequent, accurate property valuations

---

## The CapSight Solution

### Enterprise-Grade Valuation Platform

**⚡ Instant Results**
- Sub-2 second API response times
- 24/7 availability with 99.9% uptime SLA
- Batch processing for portfolio valuations

**🎯 Bulletproof Accuracy**  
- **MAPE ≤ 10%** across all markets (vs. 15-20% industry standard)
- **80% confidence intervals** calibrated via conformal prediction
- **Robust estimator** with automatic fallback logic

**🔬 Full Transparency**
- Complete methodology documentation
- Top 5 comparable sales with weights and adjustments
- Quality indicators and data freshness metrics

**📈 Continuous Improvement**
- Nightly backtesting and accuracy monitoring
- A/B testing for methodology enhancements
- Real-time bias detection and correction

---

## Market Coverage & Data

### 5 Pilot Markets with Deep Coverage

| Market | Properties | Avg. Age | Verification Rate |
|--------|------------|----------|-------------------|
| **Dallas-Fort Worth** | 2,500+ | 8 months | 89% |
| **Inland Empire** | 1,800+ | 6 months | 87% |
| **Atlanta** | 2,200+ | 7 months | 91% |
| **Phoenix** | 1,600+ | 9 months | 85% |
| **Savannah** | 800+ | 11 months | 88% |

### Data Quality Standards
- ✅ **Verified Sales Only**: Broker-confirmed or public record verification
- ✅ **Geofence Validation**: Automated market boundary enforcement  
- ✅ **Outlier Detection**: Statistical winsorization and quality gates
- ✅ **Recency Weighting**: 12-month half-life decay for time adjustments

---

## Methodology: Robust & Transparent

### Weighted Median Approach
```
Final Estimate = WeightedMedian(
  ComparableSales × TimeAdjustment × SimilarityWeights
)
```

### Multi-Factor Similarity Weighting
- **📅 Recency**: 12-month half-life (recent = higher weight)
- **📍 Distance**: 15-mile exponential decay + submarket bonus  
- **📏 Size**: Gaussian kernel on log(SF) with ±35% tolerance
- **🏗️ Age/Quality**: 10-year age tolerance when available

### Confidence Intervals via Conformal Prediction
1. Historical backtest on 18-month rolling window
2. Calculate prediction errors for each comparable
3. Empirical quantiles provide calibrated confidence bands
4. **Result**: True 80% coverage (78-82% target range)

### Automatic Fallback Logic
- **Low Sample Size** (<8 comps): Market median + wider bands
- **High Dispersion** (IQR >150bps): Dispersion penalty + warnings  
- **Stale Data** (>18mo old): User confirmation + uncertainty adjustment

---

<div style="page-break-before: always;">

## API Integration & Technical Specs

### RESTful API with Enterprise Features

**Base URL**: `https://api.capsight.com/v1`

```json
POST /value
{
  "market_slug": "dfw",
  "noi_annual": 1500000,
  "building_sf": 100000,
  "year_built": 2015
}

Response:
{
  "valuation_usd": 25000000,
  "confidence_interval": [23750000, 26250000],
  "cap_rate_pct": 6.0,
  "methodology": "weighted_median_v1.0",
  "comp_count": 12,
  "quality_score": "high",
  "top_comps": [...],
  "warnings": []
}
```

### Performance & Reliability
- **Response Time**: <2 seconds (95th percentile)
- **Rate Limits**: 100/min (1000/day standard, unlimited enterprise)
- **Uptime SLA**: 99.9% with automated failover
- **Security**: SOC 2 Type II, data encryption at rest and in transit

</div>

---

## Sample Results: DFW Industrial Property

### Property Details
- **Market**: Dallas-Fort Worth (DFW)
- **Size**: 125,000 SF industrial warehouse
- **NOI**: $1,850,000 annually
- **Built**: 2018

### CapSight Valuation Results

```
💰 Valuation: $28,500,000
📊 Confidence: $27,200,000 - $29,800,000 (±4.6%)
📈 Cap Rate: 6.49%
💵 Price/SF: $228

✅ Quality Score: HIGH
📋 Comparables: 15 verified sales
⏰ Data Age: 6.2 months average
🎯 Methodology: weighted_median_v1.0
```

### Top Contributing Comparables
1. **Industrial Blvd, Dallas** - 118K SF, $26.8M, 6.2% cap (Weight: 0.23)
2. **Logistics Way, Irving** - 135K SF, $31.2M, 6.8% cap (Weight: 0.19)  
3. **Distribution Dr, Plano** - 105K SF, $24.1M, 6.1% cap (Weight: 0.16)
4. **Commerce St, Fort Worth** - 142K SF, $33.5M, 7.1% cap (Weight: 0.14)
5. **Industrial Park, Garland** - 98K SF, $22.8M, 5.9% cap (Weight: 0.12)

**Quality Indicators**: ✅ Fresh data ✅ High verification rate ✅ Good sample size ✅ Low dispersion

---

## Service Level Agreements

### Accuracy Commitments

| Metric | Target | Current Performance |
|--------|---------|-------------------|
| **MAPE** | ≤ 10% | **8.7%** ✅ |
| **RMSE** | ≤ 50 bps | **43 bps** ✅ |
| **Coverage** | 78-82% | **80.1%** ✅ |
| **Response Time** | <2 sec | **1.4 sec** ✅ |

### Operational SLAs
- **Uptime**: 99.9% (8.8 hours downtime/year max)
- **Data Freshness**: ≤24 hours for accuracy metrics updates
- **Support Response**: <2 hours for P1 issues, <8 hours for P2
- **API Rate Limits**: 100 req/min standard, enterprise unlimited

### Financial Guarantees
- **Service Credit**: 5% monthly fee credit for each 0.1% below 99.9% uptime
- **Accuracy Guarantee**: Methodology review and recalibration if MAPE >12% for 30 days
- **Data Quality**: 100% verified sales guarantee or full refund

---

## Pricing & Packages

### Usage-Based Pricing

**🏢 Starter** - *Perfect for brokers and small firms*
- **$0.50/valuation** (pay-as-you-go)
- 100 requests/minute
- Email support
- Standard accuracy (MAPE ≤10%)
- 30-day API access logs

**🏭 Professional** - *Ideal for active investment managers*  
- **$2,500/month** (includes 10,000 valuations)
- $0.20/additional valuation
- 500 requests/minute
- Priority support + phone
- Enhanced data exports
- 12-month audit trail

**🏗️ Enterprise** - *Built for REITs, lenders, and institutional clients*
- **Custom pricing** based on volume and features
- Unlimited API requests
- Dedicated customer success manager
- Custom data integrations
- SLA guarantees with penalties
- White-label options available

### Volume Discounts Available
- **10K+ valuations/month**: 15% discount
- **50K+ valuations/month**: 25% discount  
- **Annual contracts**: Additional 10% discount

---

<div style="page-break-before: always;">

## Use Cases & ROI

### Primary Use Cases

**💼 Investment Underwriting**
- Rapid preliminary valuations for deal screening
- Portfolio marking and asset management
- Investment committee decision support

**🏦 Loan Underwriting & Servicing**  
- Origination support and risk assessment
- Portfolio surveillance and early warning systems
- Workout and restructuring analysis

**📈 Portfolio Management**
- Quarterly portfolio valuation updates
- Asset performance benchmarking
- Disposition and acquisition strategy

**🤝 Brokerage & Advisory**
- Client pitch materials and market insights
- Listing price optimization
- Transaction comparable analysis

### ROI Calculation

**Traditional Appraisal**:
- Cost: $5,000 per property
- Time: 3 weeks
- Accuracy: ±15-20%

**CapSight Solution**:
- Cost: $2,500/month (10K valuations)
- Time: <2 seconds
- Accuracy: ±8.7% MAPE

**Savings for 100 property portfolio**:
- **Cost**: $500,000/year → $30,000/year = **$470K saved**
- **Time**: 300 weeks → 3.3 minutes = **99.96% faster**
- **Accuracy**: 20% variance → 8.7% variance = **56% improvement**

</div>

---

## Security & Compliance

### Data Protection
- **Encryption**: TLS 1.3 in transit, AES-256 at rest
- **Access Control**: Role-based permissions, multi-factor authentication
- **Audit Logging**: Complete API access logs with tamper protection
- **Data Residency**: US-based infrastructure, SOC 2 Type II certified

### Privacy & Confidentiality  
- **No PII Storage**: Property addresses masked in API responses
- **Anonymized Analytics**: Aggregate market trends only
- **GDPR Compliant**: Data subject rights and consent management
- **NDA Protection**: Standard enterprise confidentiality agreements

### Regulatory Considerations
- **Non-USPAP**: Not for regulated appraisal purposes (clearly disclosed)
- **Indicative Only**: For analytical and decision support use cases
- **Professional Judgment**: Supplement to, not replacement for, expert analysis
- **Liability Limits**: Clearly defined in terms of service

---

## Implementation & Support

### Getting Started (< 1 Week)
1. **API Key Provisioning** (Day 1)
2. **Technical Integration** (Days 2-3)  
3. **User Training & Documentation** (Day 4)
4. **Pilot Testing** (Days 5-7)
5. **Production Launch** (Week 2)

### Integration Support
- **REST API**: OpenAPI 3.0 specification provided
- **SDKs Available**: Python, JavaScript, C#, Java
- **Webhook Support**: Real-time notifications for batch processing
- **Test Environment**: Full-featured sandbox for development

### Ongoing Support
- **Documentation Portal**: Comprehensive API docs and methodology guides
- **24/7 Monitoring**: Automated alerting and incident response
- **Regular Updates**: Quarterly methodology enhancements
- **Training Programs**: User onboarding and best practices

---

## Why Choose CapSight?

### ✅ **Proven Accuracy**
Independent validation shows 8.7% MAPE across 5 markets - better than industry standard appraisals

### ✅ **Enterprise Ready** 
Built for scale with 99.9% uptime, sub-2 second response times, and unlimited API capacity

### ✅ **Full Transparency**
Complete methodology documentation, audit trails, and explainable AI with top comparable breakdowns

### ✅ **Continuous Improvement**
Nightly accuracy monitoring, A/B testing, and bias detection ensure improving performance over time

### ✅ **Risk Mitigation**
Calibrated confidence intervals, fallback logic, and quality warnings help you understand uncertainty

### ✅ **Cost Effective**
10x-50x cost savings vs traditional appraisals with superior accuracy and instant turnaround

---

<div style="text-align: center; margin-top: 100px;">

## Ready to Transform Your Valuation Process?

### 🚀 **Start Your Pilot Today**

**Free 30-Day Trial** - *No commitment required*
- 1,000 complimentary valuations
- Full API access to all 5 markets  
- Technical integration support
- Performance benchmarking report

### 📞 **Contact Information**

**Sales Team**: sales@capsight.com  
**Technical Support**: support@capsight.com  
**Phone**: (555) 123-CAPS

**Schedule a Demo**: [calendly.com/capsight-demo](https://calendly.com/capsight-demo)

---

*CapSight - Industrial CRE Valuations, Reimagined*  
**Bulletproof Accuracy • Enterprise Reliability • Instant Results**

</div>
