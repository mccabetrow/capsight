# CapSight Enhanced Operations Monitoring Playbook

## Overview
This playbook covers monitoring and maintaining the enhanced CapSight valuation system with robust estimators, conformal prediction, and automated accuracy tracking.

## System Architecture

### Core Components
1. **Robust Valuation API** (`pages/api/value.ts`)
   - Weighted median estimator with similarity kernels
   - Dynamic confidence bands via conformal prediction
   - Automatic fallback rules for edge cases
   - Full auditability with masked comps

2. **Enhanced Data Validator** (`validate_csv.py`)
   - Geofence validation for all markets
   - NOI consistency checks
   - Automated review queue flagging
   - Size/age bucket categorization

3. **Nightly Accuracy Monitor** (`nightly_accuracy.py`)
   - Automated backtesting across all markets
   - SLA compliance tracking (MAPE ≤10%, RMSE ≤50bps, Coverage 78-82%)
   - Bias detection and drift monitoring
   - Automated alerting for violations

4. **Database Schema**
   - `accuracy_metrics`: Rolling performance metrics
   - `comp_review_queue`: Data quality workflow
   - `v_comps_trimmed`: Outlier-filtered view
   - `latest_accuracy`: Current SLA status

## Daily Operations

### Morning Health Check (9 AM)
```sql
-- Check overall system health
SELECT * FROM v_system_health ORDER BY metric;

-- Verify nightly accuracy run completed
SELECT market_slug, last_updated, mape, rmse_bps, coverage80
FROM latest_accuracy 
WHERE last_updated >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY market_slug;
```

**Expected Results:**
- All 5 markets should have updated accuracy metrics from last night
- SLA passing rate should be >80% across markets
- Review queue should have <20 pending items

**Red Flags:**
- Any market missing from nightly update
- MAPE >15% or RMSE >75bps consistently
- Coverage <75% or >85% (miscalibrated)

### Weekly Performance Review (Monday 10 AM)

```sql
-- Weekly accuracy trend
SELECT 
    market_slug,
    AVG(mape) as avg_mape,
    AVG(rmse_bps) as avg_rmse,
    AVG(coverage80) as avg_coverage,
    COUNT(*) as data_points
FROM accuracy_metrics 
WHERE last_updated >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY market_slug
ORDER BY avg_mape DESC;

-- Data quality issues
SELECT 
    market_slug,
    reason,
    COUNT(*) as count,
    MIN(created_at) as first_seen,
    MAX(created_at) as last_seen
FROM comp_review_queue 
WHERE status = 'pending'
GROUP BY market_slug, reason
ORDER BY count DESC;
```

**Actions:**
- Review markets with degrading MAPE trends
- Process high-priority review queue items
- Update methodology documentation if needed

## SLA Monitoring

### Target SLAs
- **MAPE (Mean Absolute Percentage Error)**: ≤10%
- **RMSE (Root Mean Square Error)**: ≤50 basis points
- **Coverage**: 78-82% (80% confidence intervals)
- **Data Freshness**: ≤24 hours old
- **API Response Time**: <2 seconds (95th percentile)

### SLA Violation Response

#### MAPE > 10%
1. Check recent data quality in that market
2. Review comp mix - any unusual sales?
3. Verify market fundamentals are current
4. Consider temporary confidence band widening

```bash
# Investigate MAPE violation
python3 nightly_accuracy.py --market [MARKET] --dry-run --log-level DEBUG
```

#### RMSE > 50bps
1. Indicates systematic estimation errors
2. Check for market trend changes
3. Review cap rate time-adjustment factors
4. May need methodology recalibration

#### Coverage Outside 78-82%
1. **Coverage <78%**: Confidence bands too narrow (overconfident)
2. **Coverage >82%**: Confidence bands too wide (underconfident)
3. Review conformal prediction calibration
4. Adjust fallback rules if needed

## Data Quality Management

### Review Queue Processing
Priority order for manual review:
1. **Price outliers** (>$300/sf or <$20/sf)
2. **Cap rate outliers** (<3% or >12%)
3. **Geofence violations**
4. **NOI inconsistencies**
5. **Missing critical fields**

```sql
-- Daily review queue processing
SELECT 
    sale_id,
    market_slug,
    reason,
    address,
    created_at
FROM comp_review_queue 
WHERE status = 'pending'
ORDER BY 
    CASE 
        WHEN reason LIKE '%Price/SF%' THEN 1
        WHEN reason LIKE '%Cap rate%' THEN 2
        WHEN reason LIKE '%geofence%' THEN 3
        WHEN reason LIKE '%NOI%' THEN 4
        ELSE 5
    END,
    created_at;
```

### Data Validation Workflow
1. **Incoming Data**: Enhanced CSV validator flags issues
2. **Auto-Triage**: High-confidence issues go to review queue
3. **Manual Review**: Operations team processes queue daily
4. **Resolution**: Accept, reject, or modify data points
5. **Re-validation**: Rerun accuracy metrics if significant changes

## Troubleshooting Guide

### API Performance Issues

**Symptoms:**
- Slow response times (>5 seconds)
- Timeouts or 500 errors
- Memory usage spikes

**Diagnosis:**
```bash
# Check API logs
tail -f logs/api.log | grep "valuation"

# Test API endpoint
curl -X POST https://your-domain.com/api/value \
  -H "Content-Type: application/json" \
  -d '{"market_slug":"dfw","noi_annual":500000,"building_sf":50000}'
```

**Common Fixes:**
- Review database query performance
- Check if too many comps being processed
- Verify connection pooling configuration
- Consider caching frequently requested markets

### Database Performance

**Symptoms:**
- Slow queries (>10 seconds)
- High CPU usage
- Connection pool exhaustion

**Diagnosis:**
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
WHERE query LIKE '%v_comps_trimmed%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats 
WHERE tablename IN ('comparables', 'fundamentals')
ORDER BY n_distinct;
```

**Common Fixes:**
- Add indexes on frequently filtered columns
- Update table statistics: `ANALYZE comparables;`
- Consider partitioning by market_slug
- Review RLS policy efficiency

### Accuracy Drift

**Symptoms:**
- Gradual MAPE increase over weeks
- Systematic bias in predictions
- Market-specific performance degradation

**Diagnosis:**
```python
# Run detailed market analysis
python3 -c "
import psycopg2
import numpy as np
import matplotlib.pyplot as plt

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Get 30-day rolling accuracy
cur.execute('''
    SELECT date_trunc('day', last_updated) as date, 
           AVG(mape) as daily_mape
    FROM accuracy_metrics 
    WHERE market_slug = 'dfw'
    AND last_updated >= NOW() - INTERVAL '30 days'
    GROUP BY date_trunc('day', last_updated)
    ORDER BY date
''')

dates, mapes = zip(*cur.fetchall())
plt.plot(dates, mapes)
plt.title('DFW MAPE Trend (30 days)')
plt.ylabel('MAPE')
plt.show()
"
```

**Common Fixes:**
- Review recent comp additions for outliers
- Check if market fundamentals changed
- Recalibrate time-decay parameters
- Update market trend adjustments

## Alerting Configuration

### Critical Alerts (Immediate Response)
- Any market MAPE >15%
- System health <70%
- Nightly accuracy job failure
- API error rate >5%

### Warning Alerts (Next Business Day)
- MAPE trending upward >3 days
- Coverage drift outside 75-85%
- Review queue >50 items
- Data freshness >48 hours

### Slack Integration
```bash
# Test Slack alerting
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🚨 CapSight Alert: DFW MAPE exceeded 10% (current: 12.3%)",
    "channel": "#capsight-ops"
  }'
```

### Email Alerts
Configure in `nightly_accuracy.py`:
```python
def send_sla_alert(violations):
    import smtplib
    from email.mime.text import MIMEText
    
    message = f"SLA Violations: {len(violations)} markets affected"
    # ... email sending logic
```

## Maintenance Schedule

### Daily (Automated)
- [ ] Nightly accuracy monitoring (2 AM UTC)
- [ ] Review queue auto-triage
- [ ] System health checks
- [ ] Backup verification

### Weekly (Manual - Mondays)
- [ ] Performance trend review
- [ ] Process high-priority review queue
- [ ] Update market fundamentals
- [ ] Capacity planning check

### Monthly (Manual - 1st of month)
- [ ] Full accuracy model recalibration
- [ ] Database maintenance (VACUUM, ANALYZE)
- [ ] Security access review
- [ ] Backup restore testing
- [ ] Documentation updates

### Quarterly (Manual)
- [ ] Market expansion planning
- [ ] Methodology improvements
- [ ] Infrastructure scaling
- [ ] Compliance audit
- [ ] Disaster recovery testing

## Emergency Response

### System Down (API Unavailable)
1. **Immediate**: Check Supabase dashboard
2. **Fallback**: Static cap rate response mode
3. **Communication**: Notify stakeholders within 15 minutes
4. **Investigation**: Debug logs and error tracking
5. **Resolution**: Fix and validate
6. **Post-mortem**: Document lessons learned

### Data Corruption Detected
1. **Immediate**: Stop data ingestion
2. **Assess**: Scope of corruption
3. **Rollback**: Restore from latest clean backup
4. **Re-validate**: Run full accuracy check
5. **Prevention**: Update validation rules

### Security Incident
1. **Immediate**: Rotate API keys
2. **Assess**: Check access logs
3. **Contain**: Disable compromised accounts
4. **Investigation**: Work with security team
5. **Recovery**: Restore secure operations

## Performance Benchmarks

### Expected Metrics (Production)
- **API Response Time**: P50 <1s, P95 <3s, P99 <5s
- **Database Queries**: P95 <2s for complex aggregations
- **Nightly Job**: Complete within 30 minutes for all markets
- **Memory Usage**: <512MB per API instance
- **CPU Usage**: <70% under normal load

### Capacity Planning
- **Current**: ~1000 requests/day across 5 markets
- **Growth**: Plan for 5x growth over 12 months
- **Scaling**: Horizontal API scaling, read replicas
- **Storage**: ~1GB growth per market per year

## Documentation Maintenance

Keep these documents current:
- `VALUATION_METHOD.md` - Methodology changes
- `OPERATIONS_MONITORING_PLAYBOOK.md` - This document
- `PRODUCTION_DEPLOYMENT_GUIDE.md` - Infrastructure changes
- `schema/schema.sql` - Database schema versions

## Contact Information

### Escalation Path
1. **Level 1**: Operations team (daily monitoring)
2. **Level 2**: Engineering team (technical issues)
3. **Level 3**: CTO (strategic decisions)

### Emergency Contacts
- **Operations**: ops@capsight.com
- **Engineering**: eng@capsight.com  
- **On-call**: +1-xxx-xxx-xxxx
- **Slack**: #capsight-ops

---

**Last Updated**: [Current Date]  
**Version**: 2.0 (Enhanced System)  
**Next Review**: [Date + 30 days]
