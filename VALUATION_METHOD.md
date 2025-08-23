# CapSight Valuation Methodology v1.0

## Overview
This document defines the exact methodology used by CapSight for industrial CRE valuations, including outlier handling, similarity weighting, time adjustments, and confidence interval calibration.

## 1. Data Quality Gates

### Outlier Policy
- **Cap rate bounds**: Reject comps with cap_rate < 2% or > 15%
- **Price per SF bounds**: Reject comps outside [P5, P95] per market
- **Market-level winsorization**: Winsorize cap rates at [P5, P95] per market
- **Required fields**: NOI must be stabilized; reject TTM or pro-forma without conversion

### Data Validation
- Geofence validation by market polygon
- Size and age within reasonable bounds
- Verification status must be 'verified' or 'broker-confirmed'
- Sale date within 18 months for primary analysis

## 2. Similarity Weighting

Weights are multiplicative and normalized to sum=1. Each component:

### Recency Weight
```
w_t = exp(-ln(2) * months_ago / 12)
```
- 12-month half-life decay
- Recent sales weighted more heavily
- Applied to all comps regardless of age

### Distance Weight  
```
w_d = exp(-miles / 15) * submarket_bonus
```
- 15-mile exponential decay
- `submarket_bonus = 2.0` if same submarket, `1.0` otherwise
- Distance calculated from property centroids

### Size Weight
```
w_s = exp(-0.5 * ((log(comp_sf) - log(subject_sf)) / 0.35)^2)
```
- Gaussian kernel on log-scale square footage
- σ = 0.35 (approximately ±35% size tolerance)
- Heavily penalizes size mismatches

### Age/Quality Weight (when available)
```
w_a = exp(-0.5 * ((comp_year - subject_year) / 10)^2)
```
- Gaussian kernel on year built
- σ = 10 years tolerance
- Applied only when both ages are known

### Combined Weight
```
w_final = (w_t * w_d * w_s * w_a) / sum(all_weights)
```

## 3. Time Normalization

### Market Trend Adjustment
- Fit monthly cap rate trend per market using LOESS or robust linear regression
- Minimum 24 months of data required for trend fitting
- Outlier-resistant: use Theil-Sen estimator for linear trends
- Adjust each comp's cap rate forward to valuation date

### Implementation
```sql
-- Market trend calculation (simplified)
SELECT market_slug,
       regr_slope(cap_rate_pct, extract(epoch from sale_date)) as trend_bps_per_day
FROM v_verified_sales_18mo 
WHERE cap_rate_pct IS NOT NULL
GROUP BY market_slug
HAVING count(*) >= 24;
```

## 4. Final Estimator

### Weighted Trimmed Median
- Apply all weights to time-adjusted cap rates
- Use weighted median (not mean) for robustness
- Trim extreme 5% of weighted distribution before calculation

### Fallback Rules
1. **Low sample size** (< 8 valid comps):
   - Fall back to market median cap rate (last 12 months)
   - Widen confidence interval to max(10%, conformal_q)
   - Display "Low sample" warning badge

2. **High dispersion** (weighted IQR > 150 bps):
   - Widen confidence interval by +200-300 bps
   - Display "High dispersion" warning

3. **Stale data** (all comps > 18 months old):
   - Require user confirmation to proceed
   - Widen confidence interval by +400-500 bps
   - Display "Stale data" warning

## 5. Confidence Interval Calibration

### Conformal Prediction Method
1. Create backtest set from historical sales
2. For each comp, predict value using contemporaneous comps
3. Calculate Absolute Percentage Error (APE) for each prediction
4. Use conformal quantile for desired coverage:

```python
def conformal_width(apes, coverage=0.80):
    apes = np.asarray([a for a in apes if np.isfinite(a)])
    if len(apes) < 50:  # Minimum sample size
        return 0.10     # Conservative 10% default
    return float(np.quantile(apes, coverage))
```

### Dynamic Band Logic
- **Target**: 80% coverage (±5% aspiration)
- **SLA met**: MAPE ≤ 10%, RMSE ≤ 50 bps, coverage ∈ [78%, 82%]
- **Display**: ±min(5%, conformal_q) if SLA met, otherwise ±conformal_q with warning

## 6. Quality Metrics & SLA Targets

### Primary Metrics
- **MAPE** (Mean Absolute Percentage Error): ≤ 10%
- **RMSE** (Root Mean Square Error): ≤ 50 basis points  
- **Coverage**: 78-82% of actual sales within predicted bands
- **Sample size**: ≥ 8 comps per market minimum

### Secondary Metrics
- **Weighted IQR**: < 150 basis points (dispersion check)
- **Data freshness**: < 18 months median age
- **Verification rate**: > 80% verified or broker-confirmed

## 7. Auditability & Transparency

### Valuation Output Includes
1. **Primary estimate**: Weighted median cap rate
2. **Confidence interval**: Calibrated or fallback width
3. **Top 5 comps**: Address (masked), date, adjusted cap, weight
4. **Quality indicators**: Sample size, dispersion, data age
5. **Method version**: v1.0 timestamp

### Explainability Panel
- Methodology summary and key assumptions
- Comp weighting breakdown by factor
- Time adjustments applied
- Fallback rules triggered (if any)

## 8. Version Control & Updates

### Version 1.0 (Current)
- Weighted median with multiplicative similarity kernels  
- Conformal prediction calibration
- Market trend time adjustment
- Robust outlier handling

### Future Enhancements
- **v1.1**: Hedonic regression residual calibration
- **v1.2**: Property-specific feature adjustments
- **v1.3**: Cross-market spillover modeling

### Change Policy
- Minor version bump for kernel parameter changes
- Major version bump for fundamental methodology changes
- All versions stored in accuracy_metrics table
- A/B testing required for major changes

## 9. Implementation Notes

### Database Views Required
- `comps_trimmed`: Market-level outlier winsorization
- `latest_accuracy`: Current SLA metrics per market
- `backtest_results`: Historical prediction accuracy

### API Enhancements
- `/api/value`: Enhanced with top-5 comps and quality metrics
- `/api/accuracy`: Real-time SLA dashboard
- `/api/backtest`: Historical performance analysis

### UI Components
- `AccuracyBadge`: Green/amber/red SLA status
- `ConfidenceBands`: Dynamic width with explanation
- `CompDetails`: Top contributing comparables
- `QualityWarnings`: Data limitations display

## 10. Validation & Testing

### Golden Test Set
- Frozen comp bundle with expected outputs
- ±5-10 bps tolerance for regression testing
- Covers edge cases (large/small, old/new, remote locations)

### Nightly Backtesting
- Rolling 12-18 month validation window
- Per-market accuracy metrics calculation  
- SLA breach alerting
- Historical trend analysis

### CI/CD Gates
- MAPE regression > 1 percentage point: Fail PR
- Coverage regression > 1 percentage point: Fail PR
- Golden test deviations > tolerance: Fail PR

---

*This methodology is designed to be robust, transparent, and continuously improving based on empirical validation. All parameters are data-driven and regularly recalibrated.*
