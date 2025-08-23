# Compliance Evidence Pack - CapSight Legal Documentation

**Generated**: {{ current_date }}  
**Version**: 1.0  
**Status**: Production Ready

## 📸 Screenshot Evidence of Legal Disclaimers

### Dashboard Page
- **Location**: `/dashboard`
- **Disclaimer Type**: CompactDisclaimer
- **Element**: `[data-cy="disclaimer-compact"]`
- **Text**: "For informational purposes only. Not investment advice."
- **Status**: ✅ Implemented and visible

### Opportunities Page  
- **Location**: `/opportunities`
- **Disclaimer Types**: 
  - ArbitrageScoreDisclaimer (page header): `[data-cy="disclaimer-arbitrage"]`
  - CompactDisclaimer (per opportunity card): `[data-cy="disclaimer-compact"]`
- **Key Text**: "Arbitrage scores are predictive estimates, not investment recommendations"
- **Status**: ✅ Implemented with dual protection

### Forecasts Page
- **Location**: `/forecasts`
- **Disclaimer Type**: ForecastPageDisclaimer
- **Element**: `[data-cy="disclaimer-forecast"]`
- **Text**: "Forecasts and predictions are for informational purposes only and do not constitute investment advice"
- **Status**: ✅ Comprehensive disclaimer with legal language

### Properties Page
- **Location**: `/properties`
- **Disclaimer Type**: CompactDisclaimer
- **Coverage**: Cap rate analysis and financial metrics
- **Status**: ✅ Protects investment-related property data

### Scenario Page
- **Location**: `/scenario`
- **Disclaimer Type**: CompactDisclaimer
- **Coverage**: Investment modeling and ROI calculations
- **Status**: ✅ Covers all predictive modeling content

### Admin Panel
- **Location**: `/admin`
- **Disclaimer Type**: CompactDisclaimer
- **Coverage**: Business metrics and revenue data
- **Status**: ✅ Protects financial business intelligence

---

## 🔗 API Response Compliance

### Sample Opportunity API Response
```json
{
  "id": "opp-123",
  "property_id": "prop-456", 
  "arbitrage_score": 8.7,
  "confidence": 0.82,
  "model_version": "v2.1.0",
  "disclaimer": "Arbitrage scores are predictive estimates based on historical data and market analysis. They do not constitute investment advice or guarantees of future performance.",
  "disclaimer_version": "1.0",
  "generated_at": "2025-08-21T16:30:00Z",
  "training_data_cutoff": "2025-08-01T00:00:00Z",
  "rationale": "Strong rental growth potential with cap rate compression indicators",
  "window_start": "2025-09-01",
  "window_end": "2025-12-31"
}
```

### Sample Forecast API Response
```json
{
  "id": "forecast-789",
  "property_id": "prop-456",
  "yhat": 145000,
  "yhat_lower": 138000,
  "yhat_upper": 152000,
  "confidence": 0.75,
  "model_version": "prophet-v1.2.0",
  "disclaimer": "Forecasts are based on historical trends and may not predict future performance. Real estate investments carry inherent risks.",
  "disclaimer_version": "1.0",
  "generated_at": "2025-08-21T16:30:00Z",
  "horizon_months": 6
}
```

---

## 📋 Contract Templates

### 1. Pilot Agreement Template
**File**: `LEGAL_RISK_FRAMEWORK.md` (lines 100-150)

**Key Provisions**:
- ✅ **Liability Limitation**: Total liability capped at 12 months of fees paid
- ✅ **Investment Disclaimer**: "Not investment advice" clause in Section 2.1
- ✅ **Use at Own Risk**: Customer acknowledges inherent investment risks
- ✅ **90-Day Pilot Terms**: With success metrics and conversion triggers

### 2. Terms of Service
**Coverage**: 
- Investment disclaimer on all predictive content
- Model limitations and confidence interval disclosure
- Data ownership and usage rights
- Professional liability limitations

### 3. Privacy Policy  
**Coverage**:
- Customer data ownership retention
- Anonymized usage for model improvement
- SOC 2 compliance controls
- 90-day data retention post-termination

### 4. Data Processing Agreement (DPA)
**Coverage**:
- GDPR/CCPA compliance for international customers
- Data minimization and consent management
- Cross-border data transfer protections

---

## 🔒 Security & Technical Controls

### Authentication & Authorization
- ✅ **JWT Expiration**: 45 minutes access, 7 days refresh
- ✅ **Role-Based Access**: Basic/Pro/Enterprise tier enforcement
- ✅ **Rate Limiting**: 100 requests/minute per user
- ✅ **CORS Protection**: Limited to production domains

### Data Protection
- ✅ **Encryption**: AES-256 at rest, TLS 1.3 in transit
- ✅ **Database Security**: Parameterized queries, no SQL injection
- ✅ **API Security**: Input validation and output sanitization
- ✅ **Audit Logging**: All predictions logged with metadata

### Model Governance  
- ✅ **Version Tracking**: Every prediction includes model version
- ✅ **Confidence Intervals**: All forecasts include uncertainty bounds
- ✅ **Training Data Cutoff**: Timestamp of last training data
- ✅ **Performance Monitoring**: Model accuracy tracked over time

---

## 📊 Audit Trail Implementation

### Backend Logging
- **Endpoint**: `/api/v1/compliance/audit`
- **Access Level**: Pro and Enterprise only
- **Retention**: 7 years for compliance
- **Export**: CSV format with counsel-ready headers

### Logged Data Points
- Request ID (for traceability)
- User ID and email
- API route and method
- Model version used
- Confidence score
- Disclaimer version displayed
- Response latency
- Timestamp (UTC)
- Metadata (market, property type, etc.)

### Compliance Metrics
- Total predictions generated
- Average confidence score by model
- Unique users accessing predictions
- Model version distribution
- Error rates and anomaly detection

---

## ⚖️ Legal Position Summary

### Investment Advisory Safe Harbor
✅ **Software Tool Classification**: CapSight provides decision support software, not investment advice  
✅ **User Retains Control**: All disclaimers emphasize user has final decision authority  
✅ **No Personal Recommendations**: General market data, not personalized advice  
✅ **Clear Limitations**: Model limitations and risks prominently disclosed  

### Liability Protection
✅ **Contractual Limits**: Liability capped at fees paid (12 months maximum)  
✅ **Excluded Damages**: No consequential, punitive, or lost profit liability  
✅ **Use at Own Risk**: Customer acknowledges investment risks  
✅ **Professional Standards**: Recommendations to consult qualified professionals  

### Regulatory Compliance
✅ **Securities Law**: Safe harbor provisions met for software tools  
✅ **Data Privacy**: GDPR/CCPA controls implemented  
✅ **Consumer Protection**: Clear, prominent disclaimers  
✅ **Professional Liability**: E&O insurance planned for Enterprise tier  

---

## ✅ Pre-Pilot Validation Checklist

- [x] All forecast pages display required disclaimers
- [x] API responses include disclaimer and confidence fields  
- [x] Contract templates include liability limitations
- [x] Audit logging captures all required metadata
- [x] Access controls prevent unauthorized data access
- [x] Model versions tracked for all predictions
- [x] Confidence intervals displayed where applicable
- [x] Terms of Service and Privacy Policy linked in footer
- [x] Professional liability framework documented
- [x] Data retention and deletion procedures defined

## 🎯 COMPLIANCE STATUS: PILOT-READY ✅

**Legal Risk**: ✅ **LOW** - Comprehensive disclaimer and liability protection  
**Regulatory Risk**: ✅ **LOW** - Investment advisory safe harbor maintained  
**Technical Risk**: ✅ **LOW** - Full audit trail and security controls  
**Contract Risk**: ✅ **LOW** - Clear pilot terms with success metrics  

**Ready for pilot launch with enterprise-grade legal protection.**

---

**Contact for Legal Review**:  
- Business Attorney: [Your legal counsel contact]
- Compliance Officer: [Internal/external compliance contact]  
- Insurance Broker: [Professional liability insurance broker]

*Document Version: 1.0*  
*Last Updated: {{ current_date }}*  
*Classification: Internal Legal Documentation*
