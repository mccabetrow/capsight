# CapSight Operations & Monitoring Playbook

## 📊 Key Metrics Dashboard (Day 1 Tracking)

### Product Metrics
| Metric | Target | Measurement | Alert Threshold |
|--------|--------|-------------|----------------|
| **Weekly Active Users** | 80% of pilots | Weekly login rate | <60% WAU |
| **Forecasts Generated** | 50+ per week per pilot | API calls to /forecasts | <20 per week |
| **Opportunities > Threshold** | 15+ per pilot per month | Scores >70 generated | <10 per month |
| **Export/Share Actions** | 10+ per pilot per month | CSV downloads, links | <5 per month |
| **Session Duration** | >8 minutes average | Frontend analytics | <5 minutes |

### Technical Metrics  
| Metric | Target | Measurement | Alert Threshold |
|--------|--------|-------------|----------------|
| **API Uptime** | 99.5% | Health check monitoring | <99% uptime |
| **Response Time P95** | <2 seconds | API response times | >3 seconds |
| **Error Rate** | <2% | 5xx responses / total | >5% error rate |
| **Database Performance** | <100ms queries | Query execution time | >500ms average |
| **ML Model Latency** | <5 seconds | Forecast generation time | >10 seconds |

### Business Metrics
| Metric | Target | Measurement | Alert Threshold |
|--------|--------|-------------|----------------|
| **Pilot Conversion Rate** | >60% | Pilots → Paid customers | <40% after 60 days |
| **Support Tickets** | <2 per pilot per month | Support system | >5 per month |
| **Demo → Pilot Rate** | >30% | Sales pipeline | <20% conversion |
| **Customer Satisfaction** | >8/10 | Weekly pilot surveys | <7/10 average |

---

## 🚨 Alerting & Escalation

### P1 - Critical (Immediate Response)
- **Service Down**: API health check fails for >5 minutes
- **Database Offline**: Connection failures for >2 minutes  
- **Payment Processing**: Stripe webhook failures >5 in 10 minutes
- **Data Loss**: Any indication of customer data corruption
- **Security Incident**: Unauthorized access detected

**Response Time**: <15 minutes  
**Escalation**: CEO + CTO immediately  
**Communication**: Status page update + pilot customer notification

### P2 - High (4 Hour Response)
- **Performance Degraded**: API response time >5 seconds for >15 minutes
- **ML Models Failing**: Forecast generation errors >10% for >30 minutes  
- **High Error Rate**: 5xx errors >10% for >10 minutes
- **Pilot Blocker**: Feature completely broken for pilot customer

**Response Time**: <4 hours  
**Escalation**: Engineering team lead  
**Communication**: Internal team + affected customers

### P3 - Medium (24 Hour Response)  
- **Minor Performance**: Slow queries, UI glitches
- **Feature Bugs**: Non-blocking functionality issues
- **Integration Issues**: Third-party service degradation
- **Documentation Problems**: Broken links, outdated info

**Response Time**: <24 hours  
**Escalation**: Development team  
**Communication**: Internal tracking only

### Contact Tree
```
P1: CEO → CTO → Engineering Lead → Support Lead
P2: CTO → Engineering Lead → Developer On-Call  
P3: Engineering Lead → Developer → QA
```

---

## 🔧 Incident Response Runbook

### Incident Template (Copy for each incident)
```
INCIDENT #: [YYYY-MM-DD-XXX]
STATUS: [INVESTIGATING/IDENTIFIED/MONITORING/RESOLVED]
SEVERITY: [P1/P2/P3]

IMPACT:
- Users Affected: [Number/Percentage]
- Services Down: [List affected services]
- Duration: [Start time - End time]

TIMELINE:
- [HH:MM] Issue detected via [Alert source]
- [HH:MM] Incident declared, team assembled  
- [HH:MM] Root cause identified: [Brief description]
- [HH:MM] Fix implemented: [Action taken]
- [HH:MM] Service restored, monitoring

ROOT CAUSE: [Technical explanation]

RESOLUTION: [What was done to fix it]

PREVENTION: [How to prevent recurrence]
- [ ] Code change needed
- [ ] Process improvement  
- [ ] Monitoring enhancement
- [ ] Documentation update

FOLLOW-UP:
- [ ] Post-mortem scheduled for [Date]
- [ ] Customer communication sent
- [ ] Prevention tasks assigned
```

### Common Incident Playbooks

#### Database Connection Issues
1. Check database server status: `docker-compose ps postgres`
2. Check connection pool: Look for connection exhaustion in logs
3. Restart backend service: `docker-compose restart backend`  
4. If persistent, restart database: `docker-compose restart postgres`
5. Verify connectivity: `docker-compose exec backend python -c "from app.core.database import get_db; next(get_db())"`

#### API Performance Degradation  
1. Check current response times in monitoring
2. Identify slow endpoints: Review API logs for >2s responses
3. Check database query performance: `EXPLAIN ANALYZE` on slow queries
4. Scale backend containers: `docker-compose scale backend=3`
5. Clear caches if needed: Redis FLUSHALL (careful in production)

#### ML Model Failures
1. Check ML service logs: `docker-compose logs backend | grep ML`
2. Verify model files exist: `ls -la app/ml/artifacts/models/`
3. Test model loading: Python import check
4. Fallback to simpler models if needed
5. Retrain models if corruption suspected

#### Stripe Webhook Issues
1. Check webhook endpoint logs: Look for 5xx responses  
2. Verify webhook signature validation
3. Test webhook manually with Stripe CLI
4. Check Stripe dashboard for failed deliveries
5. Re-sync subscription status if needed

---

## 📈 Performance Optimization

### Database Optimization  
```sql
-- Common slow query optimizations
CREATE INDEX CONCURRENTLY idx_properties_created_at ON properties (created_at DESC);
CREATE INDEX CONCURRENTLY idx_forecasts_property_date ON forecasts (property_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_opportunities_score ON opportunities (score DESC) WHERE score > 70;

-- Connection pooling (pgBouncer config)
pool_mode = transaction
max_client_conn = 100  
default_pool_size = 20
```

### API Performance
- **Caching**: Redis cache for frequently accessed data (forecasts, opportunities)
- **Pagination**: Limit query results to 20-50 items per page
- **Database Indexing**: Index on commonly filtered columns (user_id, created_at, score)  
- **Async Processing**: Move heavy ML computations to background jobs

### Frontend Performance
- **Code Splitting**: Lazy load routes and components
- **Image Optimization**: Compress and serve appropriate sizes  
- **CDN**: Serve static assets from CDN
- **Bundle Analysis**: Monitor bundle size, remove unused code

---

## 🔄 Backup & Recovery

### Daily Backup Process
```bash
#!/bin/bash
# Database backup
docker-compose exec postgres pg_dump -U capsight_user capsight_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# ML models backup  
tar -czf ml_models_$(date +%Y%m%d).tar.gz app/ml/artifacts/

# Upload to cloud storage (S3, GCS, etc.)
aws s3 cp backup_*.sql s3://capsight-backups/database/
aws s3 cp ml_models_*.tar.gz s3://capsight-backups/models/
```

### Recovery Testing (Monthly)
1. **Database Recovery**:
   - Restore backup to test environment
   - Verify data integrity and completeness
   - Test application functionality

2. **Model Recovery**:  
   - Restore model artifacts
   - Verify model loading and predictions
   - Compare outputs with production

3. **Full System Recovery**:
   - Deploy to staging environment  
   - Run end-to-end tests
   - Verify all integrations working

### Recovery Time Objectives
- **Database**: RTO 1 hour, RPO 4 hours (daily backups)
- **Application**: RTO 30 minutes (container restart)
- **ML Models**: RTO 2 hours (model reloading)

---

## 📋 Weekly Operations Checklist

### Monday: Health Check
- [ ] Review weekend alerts and incidents
- [ ] Check backup success for last 7 days  
- [ ] Database performance review (slow queries)
- [ ] SSL certificate expiration check (30-day warning)
- [ ] Security patch review and planning

### Wednesday: Performance Review  
- [ ] API response time trends
- [ ] Error rate analysis by endpoint
- [ ] User engagement metrics review
- [ ] Support ticket themes and resolution times
- [ ] ML model accuracy drift check

### Friday: Planning & Prep
- [ ] Incident post-mortems completion
- [ ] Next week's deployment planning
- [ ] Capacity planning (if growth observed)  
- [ ] Customer feedback review and prioritization
- [ ] Weekend on-call handoff briefing

---

## 🎯 Pilot Customer Success Monitoring

### Weekly Pilot Health Score
**Engagement Score** (40%):
- Logins: 4+ per week = 100%, 2-3 = 70%, <2 = 30%
- Features Used: >3 = 100%, 2-3 = 70%, <2 = 30%  
- Time Spent: >20min/week = 100%, 10-20min = 70%, <10min = 30%

**Value Score** (40%):  
- Opportunities Flagged: >5 = 100%, 3-5 = 70%, <3 = 30%
- Actions Taken: >1 = 100%, 1 = 70%, 0 = 30%
- Exports/Shares: >3 = 100%, 1-3 = 70%, 0 = 30%

**Satisfaction Score** (20%):
- Weekly Survey: >8 = 100%, 6-8 = 70%, <6 = 30%
- Support Tickets: 0 = 100%, 1-2 = 70%, >2 = 30%

**Overall Health**: Weighted average  
- **Green** (>80%): On track for conversion
- **Yellow** (60-80%): Needs attention  
- **Red** (<60%): At risk, immediate action needed

### At-Risk Customer Actions
1. **Immediate**: Schedule 1:1 call within 2 business days
2. **Understand**: What's blocking them from finding value?  
3. **Support**: Provide additional training, data, or customization
4. **Follow-up**: Weekly check-ins until health score improves
5. **Escalate**: If still at-risk after 2 weeks, involve leadership

**Success Indicator**: 80% of pilots maintain green health score after Week 4.
