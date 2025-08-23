# CapSight 6-Minute Demo Script

## Pre-Demo Setup (30 seconds before)

### Technical Preparation
- [ ] Browser tabs ready:
  - CapSight app (https://app.capsight.com)
  - Admin console (https://app.capsight.com/admin) 
  - Documentation site (https://docs.capsight.com)
- [ ] Sample property data ready (copy/paste friendly):
  ```
  Market: Dallas-Fort Worth (DFW)
  Building Size: 125,000 SF
  Annual NOI: $1,850,000
  Year Built: 2018
  ```
- [ ] ADMIN_TOKEN ready for console access
- [ ] Demo mode toggle available (if needed to mask real data)

### Room Setup
- [ ] Projector/screen optimized for web UI
- [ ] Audio working for video elements  
- [ ] Stable internet connection confirmed
- [ ] Backup slides ready (PDF) in case of technical issues

---

## Opening Hook (30 seconds) | Total: 0:30

### The Problem Statement
> "Imagine you're evaluating a $25M industrial property acquisition. Traditional appraisals take 3 weeks, cost $5,000, and can vary by ±20%. What if you could get a more accurate valuation in under 2 seconds, with full transparency, for $2.50?"

### Transition to Demo
> "That's exactly what CapSight delivers. Let me show you how our industrial CRE platform works with a live property example."

**[Navigate to CapSight homepage]**

---

## Platform Overview (45 seconds) | Total: 1:15

### Quick Visual Tour
> "CapSight is the first enterprise-grade valuation platform built specifically for industrial CRE. We cover 5 major markets with over 10,000 verified comparable sales."

**[Scroll through homepage showing market coverage map]**

### Key Differentiators (Point to UI elements)
- **"Instant results"** - No waiting weeks for appraisals
- **"Bulletproof accuracy"** - 8.7% MAPE vs 15-20% industry standard  
- **"Full transparency"** - See exactly how we calculated every number
- **"Enterprise ready"** - 99.9% uptime, unlimited API access

### Demo Property Introduction
> "Let's value a real property - a 125,000 square foot industrial warehouse in Dallas-Fort Worth with $1.85M in annual NOI."

**[Navigate to valuation form]**

---

## Live Valuation Demo (90 seconds) | Total: 2:45

### Input Property Details
**[Fill out form while speaking]**
- Market: Dallas-Fort Worth ✅
- Building Size: 125,000 SF ✅
- Annual NOI: $1,850,000 ✅
- Year Built: 2018 (optional) ✅

> "Notice the clean, intuitive interface. No complex forms or jargon - just the essential data points needed for accurate valuation."

### Execute Valuation
**[Click "Get Valuation" button]**

> "Processing... and there we have it. Under 2 seconds for a complete valuation with confidence intervals."

### Results Breakdown
**[Point to each section of results]**

**Primary Valuation:**
> "Our robust estimator suggests this property is worth $28.5 million, with a confidence interval of $27.2M to $29.8M. That's a 6.49% cap rate at $228 per square foot."

**Quality Indicators:**
> "Notice the quality score is 'HIGH' - we found 15 verified comparable sales with fresh data averaging just 6 months old."

**Methodology Transparency:**  
> "This used our weighted median methodology version 1.0, with no fallback rules triggered. The tight confidence band reflects high certainty in this estimate."

---

## Explainability Deep-Dive (75 seconds) | Total: 4:00

### Top Comparables Analysis  
**[Scroll to comparables section]**

> "Here's what makes CapSight different - complete transparency. These are the 5 most similar properties that drove our valuation:"

**[Point to each comparable]**
- "Industrial Blvd property: 118K SF, $26.8M sale, 6.2% cap rate - weighted 23%"
- "Logistics Way property: 135K SF, $31.2M sale, 6.8% cap rate - weighted 19%"

> "Notice the addresses are masked for privacy, but you get size, sale price, date, and cap rate plus our similarity weighting."

### Similarity Factors
**[Click "How was this calculated?" button]**

> "Our algorithm considers four key factors:"
- **"Recency"** - Recent sales get higher weight (12-month half-life)
- **"Distance"** - Exponential decay with submarket bonuses  
- **"Size"** - Log-normal similarity weighting (±35% tolerance optimal)
- **"Age"** - Building age similarity when available

### Confidence Calibration
> "The confidence interval comes from conformal prediction - we backtest on 18 months of historical sales to ensure true 80% coverage. No guesswork."

---

## Enterprise Features (60 seconds) | Total: 5:00

### Admin Console Demo
**[Navigate to admin console, enter ADMIN_TOKEN]**

> "For enterprise clients, we provide a comprehensive admin console for accuracy monitoring and operational oversight."

**[Show accuracy dashboard]**
- "Real-time SLA compliance across all markets"  
- "Current performance: 8.7% MAPE, well below our 10% target"
- "Nightly backtesting ensures continuous calibration"

**[Show market status]**
- "Market health monitoring with data freshness indicators"
- "Review queue for flagged properties requiring human oversight"

### API Integration  
**[Switch to documentation site]**

> "Everything you just saw is available via our REST API. Here's the actual request that would generate that valuation:"

**[Show API example]**
```json
POST /api/value
{
  "market_slug": "dfw", 
  "noi_annual": 1850000,
  "building_sf": 125000,
  "year_built": 2018
}
```

> "Sub-2 second response times, 99.9% uptime SLA, and unlimited requests for enterprise clients."

---

## Business Impact & Close (60 seconds) | Total: 6:00

### ROI Quantification
> "Let's talk impact. For a typical client with 100 properties:"

**[Reference sales deck or slide]**
- **Cost**: Traditional appraisals $500K/year → CapSight $30K/year = **$470K saved**
- **Time**: 300 weeks → 5 minutes = **99.96% faster** 
- **Accuracy**: 20% variance → 8.7% variance = **56% improvement**

### Use Cases Summary
> "Our clients use CapSight for:"
- **Investment underwriting** - Rapid deal screening and due diligence
- **Loan origination** - Risk assessment and portfolio surveillance  
- **Portfolio management** - Quarterly valuations and benchmarking
- **Brokerage** - Client pitch materials and pricing optimization

### Call to Action
> "Ready to transform your valuation process?"

**Options:**
1. **"Start with our free 30-day trial"** - 1,000 complimentary valuations, full API access
2. **"Schedule a technical integration call"** - Our team will help you get up and running in under a week
3. **"Custom enterprise demo"** - Tailored to your specific use cases and portfolio

### Contact & Next Steps
> "Questions? Email sales@capsight.com or visit calendly.com/capsight-demo to schedule a follow-up. I'll send the demo materials and trial access information right after this call."

---

## Demo Troubleshooting

### If API is slow/down:
- Switch to demo mode with cached data
- Use backup screenshots/video recordings
- Pivot to methodology explanation while system recovers

### If questions go long:
- "Great question - let me address that after the demo"  
- Park questions for Q&A session
- Use a timer/phone to stay on track

### If technical issues:
- Have PDF sales deck ready as backup
- Use pre-recorded screen capture videos
- Switch to Q&A and methodology discussion

### Common Questions & Responses:

**Q: "How does this compare to appraisals?"**
A: "CapSight is not an appraisal replacement - it's analytical support for faster decision-making. Think of it as 'sophisticated comparable sales analysis' rather than a regulated appraisal product."

**Q: "What about USPAP compliance?"**  
A: "CapSight is explicitly non-USPAP. It's designed for analytical and decision support use cases where speed and consistency matter more than regulatory compliance."

**Q: "Can you customize for our market/property type?"**
A: "We're focused on industrial CRE in our 5 core markets currently. Custom market expansion is available for enterprise clients with sufficient transaction volume."

**Q: "What's your data source?"**
A: "We aggregate verified sales from multiple commercial databases, public records, and broker networks. Every transaction goes through our quality validation pipeline."

**Q: "How often do you update accuracy?"**
A: "Nightly backtesting across all markets. If SLA targets are missed for more than 30 days, we trigger methodology review and recalibration."

---

## Post-Demo Follow-Up Checklist

### Immediate (within 2 hours):
- [ ] Send trial access credentials and setup instructions
- [ ] Email PDF sales deck and technical documentation
- [ ] Schedule technical integration call if requested
- [ ] Add prospect to CRM with demo feedback notes

### Within 24 hours:  
- [ ] Send custom proposal based on discussed use cases
- [ ] Provide relevant case study materials
- [ ] Connect with technical team for API integration support
- [ ] Schedule executive alignment call if enterprise prospect

### Within 1 week:
- [ ] Check in on trial progress and address any technical issues
- [ ] Provide usage analytics and preliminary ROI calculations  
- [ ] Schedule contract discussion if trial is successful
- [ ] Gather feedback for demo script improvements
