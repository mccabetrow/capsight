# CapSight Frequently Asked Questions

## General Platform Questions

### Q: What is CapSight?
**A**: CapSight is an enterprise-grade valuation platform specifically designed for industrial commercial real estate. We provide instant, accurate property valuations with confidence intervals using robust statistical methods and a database of 10,000+ verified comparable sales.

### Q: How is this different from traditional appraisals?
**A**: Key differences include:
- **Speed**: 2 seconds vs 2-4 weeks
- **Cost**: $0.50-$2.50 vs $3,000-$8,000  
- **Accuracy**: 8.7% MAPE vs 15-20% typical variance
- **Transparency**: See all comps and methodology vs "black box"
- **Availability**: 24/7 API access vs appointment-based
- **Consistency**: Standardized methodology vs appraiser subjectivity

### Q: Is CapSight USPAP compliant?
**A**: No, CapSight is explicitly **non-USPAP** and not intended for regulated appraisal purposes. Our platform is designed for:
- Investment analysis and decision support
- Portfolio monitoring and benchmarking
- Preliminary valuations and deal screening
- Risk assessment and underwriting support

For loan origination, tax appeals, or legal proceedings requiring USPAP compliance, you'll still need a licensed appraiser.

### Q: What markets do you cover?
**A**: Currently 5 major industrial markets:
- **Dallas-Fort Worth (DFW)**: 2,500+ properties
- **Inland Empire (IE)**: 1,800+ properties  
- **Atlanta (ATL)**: 2,200+ properties
- **Phoenix (PHX)**: 1,600+ properties
- **Savannah (SAV)**: 800+ properties

Market expansion is driven by client demand and transaction volume. Enterprise clients can request priority consideration for new markets.

### Q: What property types are supported?
**A**: Industrial property types including:
- Distribution centers and warehouses
- Manufacturing facilities
- Logistics and fulfillment centers  
- Flex/industrial office combinations
- Cold storage and specialized industrial

We focus exclusively on industrial CRE - no office, retail, or multifamily coverage currently.

---

## Methodology & Accuracy

### Q: How do you achieve 8.7% MAPE accuracy?
**A**: Our robust methodology includes:

1. **Quality Data**: Only verified sales (broker-confirmed or public record)
2. **Outlier Removal**: Statistical winsorization removes extreme outliers
3. **Similarity Weighting**: Multi-factor weighting by recency, distance, size, age
4. **Weighted Median**: More robust than simple averages
5. **Time Adjustments**: Market trend normalization
6. **Conformal Prediction**: Empirically calibrated confidence intervals
7. **Continuous Monitoring**: Nightly backtesting and bias detection

### Q: What is "conformal prediction"?
**A**: Conformal prediction is a statistical method that provides theoretically guaranteed confidence intervals. Here's how it works:

1. **Historical Backtest**: We predict every sale using contemporaneous data
2. **Error Calculation**: Measure absolute percentage errors for all predictions  
3. **Quantile Selection**: Use empirical distribution to set confidence bands
4. **Coverage Guarantee**: Ensures true 80% coverage (78-82% target range)

Unlike traditional confidence intervals based on assumptions, conformal prediction provides real-world calibrated uncertainty.

### Q: How often do you update your accuracy metrics?
**A**: **Nightly backtesting** across all markets with:
- Rolling 18-month validation window
- Per-market SLA compliance tracking
- Bias detection and drift monitoring
- Automated alerting for SLA violations

If accuracy degrades below SLA targets for >30 days, we trigger methodology review and recalibration.

### Q: What happens if there aren't enough comparables?
**A**: Our **automatic fallback logic** handles edge cases:

1. **Low Sample Size** (<8 comps):
   - Fall back to market median cap rate (last 12 months)
   - Widen confidence interval to minimum 10%
   - Display "Low sample" warning badge

2. **High Dispersion** (weighted IQR >150 bps):
   - Add 200-300 bps to confidence interval
   - Display "High dispersion" warning

3. **Stale Data** (all comps >18 months old):
   - Require user confirmation
   - Add 400-500 bps uncertainty penalty
   - Display "Stale data" warning

### Q: Can I see which comparables were used?
**A**: Yes! Full transparency includes:
- Top 5 contributing comparables with weights
- Masked addresses for privacy (e.g., "***** Industrial Blvd, Dallas TX")
- Sale date, size, price, and cap rate for each comp
- Similarity score and weighting factors
- Time adjustments applied
- Quality indicators and data age

---

## Data Sources & Privacy

### Q: Where do you get your data?
**A**: We aggregate from multiple sources:
- Commercial real estate databases (CoStar, LoopNet, etc.)
- Public records and county assessor data
- Broker networks and MLS systems
- Direct submissions from market participants

**Every sale goes through our quality validation pipeline** before inclusion.

### Q: How do you verify data accuracy?
**A**: Multi-step verification process:
1. **Source Verification**: Broker-confirmed or public record validation
2. **Geofence Validation**: Automated market boundary enforcement
3. **Statistical Outlier Detection**: Removes obvious errors and outliers
4. **Cross-Reference Validation**: Multiple source confirmation when available
5. **Manual Review Queue**: Human review for flagged transactions

Current verification rate: 85-91% across markets.

### Q: Do you store or share my property data?
**A**: **No personal or proprietary information is stored or shared**:
- API requests are processed in real-time and not logged long-term
- No property addresses or client names in our database
- Aggregate market trends only (no individual property tracking)
- SOC 2 Type II certified with encryption at rest and in transit

### Q: Is my data secure?
**A**: Enterprise-grade security includes:
- **Encryption**: TLS 1.3 in transit, AES-256 at rest
- **Access Control**: Role-based permissions, MFA required
- **Audit Logging**: Complete API access logs with tamper protection
- **Compliance**: SOC 2 Type II, GDPR compliant, US data residency
- **Monitoring**: 24/7 security monitoring and incident response

---

## Technical Integration

### Q: How do I integrate with the CapSight API?
**A**: Simple REST API integration:

```json
POST https://api.capsight.com/v1/value
{
  "market_slug": "dfw",
  "noi_annual": 1500000,
  "building_sf": 100000,
  "year_built": 2015
}
```

**Resources available**:
- OpenAPI 3.0 specification
- SDKs for Python, JavaScript, C#, Java
- Comprehensive documentation portal
- Test environment for development
- Technical integration support

### Q: What are the API rate limits?
**A**: Depends on your plan:
- **Starter**: 100 requests/minute, 1,000/day
- **Professional**: 500 requests/minute, unlimited daily
- **Enterprise**: Unlimited requests

All plans include burst capacity and rate limit headers for proper handling.

### Q: What's the API response time SLA?
**A**: **<2 seconds** for 95th percentile response times with:
- 99.9% uptime guarantee (8.8 hours downtime/year maximum)
- Automated failover and redundancy
- Global CDN for optimized performance
- Real-time monitoring and alerting

### Q: Can you handle batch processing?
**A**: Yes, multiple options:
- **Synchronous API**: Up to 50 properties per request
- **Asynchronous Batch**: Upload CSV, get results via webhook
- **Streaming API**: Real-time processing for large datasets
- **Custom Integration**: Direct database access for enterprise clients

### Q: Do you support webhooks?
**A**: Yes, webhook support for:
- Batch processing completion notifications
- SLA violation alerts
- Market data updates
- Custom event triggers for enterprise clients

---

## Pricing & Business Model

### Q: How much does CapSight cost?
**A**: Usage-based pricing with three tiers:

**🏢 Starter**: $0.50/valuation (pay-as-you-go)
- 100 requests/minute rate limit
- Email support
- 30-day API access logs

**🏭 Professional**: $2,500/month (includes 10,000 valuations)
- $0.20/additional valuation
- 500 requests/minute
- Priority support + phone
- 12-month audit trails

**🏗️ Enterprise**: Custom pricing based on volume
- Unlimited API requests
- Dedicated customer success manager
- Custom integrations and SLA guarantees
- White-label options

### Q: Are there volume discounts?
**A**: Yes:
- **10K+ valuations/month**: 15% discount
- **50K+ valuations/month**: 25% discount
- **Annual contracts**: Additional 10% discount
- **Enterprise custom pricing** available

### Q: What's included in the free trial?
**A**: 30-day free trial includes:
- 1,000 complimentary valuations
- Full access to all 5 markets
- Complete API functionality
- Technical integration support
- Performance benchmarking report
- No setup fees or long-term commitment

### Q: Do you offer refunds?
**A**: **Money-back guarantee**:
- 30-day full refund for any reason
- Pro-rated refunds for annual contracts
- Service credits for SLA violations (5% monthly credit per 0.1% below 99.9% uptime)

---

## Use Cases & Industry Applications

### Q: Who typically uses CapSight?
**A**: Primary user segments:

**Investment Managers & REITs**:
- Portfolio valuation and NAV calculations
- Acquisition screening and due diligence
- Asset performance benchmarking

**Commercial Lenders**:
- Loan origination and underwriting
- Portfolio surveillance and monitoring
- Workout and REO valuation

**Brokers & Advisors**:
- Client pitch materials and market analysis
- Listing price optimization
- Transaction comparable analysis

**Property Technology Platforms**:
- Real-time valuation integrations
- Automated underwriting tools
- Portfolio monitoring dashboards

### Q: Can CapSight replace traditional appraisals?
**A**: **No, CapSight complements rather than replaces appraisals**:

**CapSight is ideal for**:
- Rapid deal screening and preliminary analysis
- Portfolio monitoring and benchmarking
- Investment decision support
- Market analysis and trending

**Traditional appraisals still needed for**:
- Loan origination (regulatory requirement)
- Tax appeals and legal proceedings
- Insurance and compliance purposes
- Final due diligence confirmation

### Q: How do I know when to use CapSight vs order an appraisal?
**A**: **Use CapSight when you need**:
- Speed (seconds vs weeks)
- Cost efficiency (frequent valuations)
- Consistency (standardized methodology)
- Transparency (see all calculations)

**Order appraisal when you need**:
- USPAP compliance
- Regulatory/legal requirements
- Final transaction documentation
- Unique property characteristics requiring expert judgment

---

## Implementation & Support

### Q: How long does implementation take?
**A**: Typical timeline:
- **API Key Setup**: Same day
- **Technical Integration**: 2-3 days
- **User Training**: 1 day
- **Pilot Testing**: 3-5 days
- **Production Launch**: 1-2 weeks total

Enterprise implementations may take longer for custom integrations.

### Q: What support do you provide?
**A**: Comprehensive support includes:
- **Technical Integration**: API documentation, SDKs, sandbox environment
- **User Training**: Platform walkthroughs and best practices
- **Ongoing Support**: Email, phone, and chat support based on plan
- **Documentation**: Methodology guides, technical specs, FAQs
- **Account Management**: Dedicated success managers for enterprise clients

### Q: How do I get started?
**A**: Three easy options:

1. **Free Trial**: Sign up at capsight.com for immediate access
2. **Schedule Demo**: 15-minute platform walkthrough
3. **Contact Sales**: Custom consultation for enterprise needs

**Trial includes**: 1,000 valuations, full documentation, technical support

### Q: Do you provide training?
**A**: Yes, multiple training options:
- **Self-service**: Comprehensive documentation portal
- **Live Training**: Platform walkthroughs and Q&A sessions  
- **Custom Training**: Tailored to your specific use cases
- **Best Practices**: Ongoing methodology and optimization guidance

---

## Regulatory & Compliance

### Q: Can I use CapSight for regulated lending?
**A**: CapSight can **supplement but not replace** regulated appraisals. Appropriate uses:
- **Pre-approval screening**: Initial risk assessment
- **Portfolio monitoring**: Ongoing collateral surveillance
- **Internal analysis**: Investment committee materials
- **Secondary validation**: Cross-check against formal appraisals

Always consult your compliance team for regulatory requirements.

### Q: What about liability and errors?
**A**: **Clear liability structure**:
- CapSight provides analytical estimates, not professional opinions
- Users retain responsibility for investment and lending decisions
- Comprehensive Terms of Service define limitations and use cases
- Professional liability insurance covers platform operations
- **Recommendation**: Use CapSight as one input in broader decision-making process

### Q: Are there geographic restrictions?
**A**: Currently available in:
- United States (5 markets operational)
- Canada (limited availability for US border properties)

**Not available**: International markets, Hawaii, Alaska, or territories due to data limitations.

---

## Competitive Landscape

### Q: How does CapSight compare to [Competitor X]?
**A**: Key differentiators:
- **Industrial Focus**: Purpose-built for industrial CRE (not generic commercial)
- **Accuracy**: 8.7% MAPE vs typical 12-15% for automated solutions
- **Transparency**: Full methodology and comparable details (not "black box")
- **Enterprise Features**: 99.9% uptime SLA, unlimited API access, dedicated support
- **Continuous Improvement**: Nightly backtesting and methodology optimization

### Q: What about free valuation websites?
**A**: Free tools typically have:
- Limited accuracy (15-25% typical variance)
- No methodology transparency
- Poor data quality and verification
- No confidence intervals or uncertainty quantification  
- No enterprise support or SLAs

**CapSight is built for professional use** with accuracy guarantees and enterprise reliability.

---

## Troubleshooting & Support

### Q: What if I get an error or unexpected result?
**A**: **Immediate steps**:
1. Check the quality score and warnings in the API response
2. Review the top comparables for obvious issues
3. Verify input parameters (market, NOI, size within reasonable ranges)
4. Contact support with the request ID for investigation

**Common issues**:
- **Low sample size**: Normal for unique properties, results include appropriate warnings
- **High dispersion**: Market volatility reflected in wider confidence intervals
- **Stale data**: Older comp data triggers uncertainty adjustments

### Q: How do I report a problem or request features?
**A**: Multiple channels:
- **Support Portal**: support.capsight.com
- **Email**: support@capsight.com  
- **Phone**: Enterprise clients get dedicated support line
- **Feature Requests**: Product roadmap input via customer success managers

**Response times**:
- P1 (API down): <2 hours
- P2 (degraded performance): <8 hours  
- P3 (questions/requests): <24 hours

### Q: Can you provide references or case studies?
**A**: Yes, with client permission we can provide:
- **Case studies**: Anonymized success stories and ROI analyses
- **Reference calls**: Direct conversations with similar clients
- **Pilot results**: Performance benchmarking from trial implementations
- **Industry testimonials**: Quotes and feedback from active users

---

*For additional questions not covered here, contact our support team at support@capsight.com or schedule a consultation at calendly.com/capsight-demo.*
