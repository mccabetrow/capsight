# CapSight Go/No-Go Pre-Flight Checklist

## 🚀 60-Minute Production Readiness Checklist

### ✅ API Health Checks
- [ ] `GET /health` returns `{"status":"ok"}` 
- [ ] `GET /docs` loads Swagger UI successfully
- [ ] `GET /api/v1/auth/me` returns 401 (unauthenticated)
- [ ] Database connection working (check logs)

### ✅ Frontend Smoke Test  
- [ ] Frontend loads at configured URL
- [ ] "Top Opportunities" section shows demo data (if DEMO_MODE=true)
- [ ] Login form appears and accepts input
- [ ] 404 page displays correctly

### ✅ Authentication Flow
- [ ] User registration works (`POST /api/v1/auth/register`)
- [ ] Email verification (if enabled) 
- [ ] Login returns valid JWT tokens
- [ ] Token refresh works (`POST /api/v1/auth/refresh`)
- [ ] Protected routes reject invalid tokens

### ✅ Core User Journey
- [ ] Login → Dashboard loads
- [ ] Dashboard → Opportunities page loads
- [ ] Opportunities → Individual opportunity details
- [ ] Scenario page loads (Pro feature test)
- [ ] Billing page loads (Stripe integration)

### ✅ Stripe Integration
- [ ] Stripe webhook endpoint returns 2xx (`/api/v1/subscriptions/stripe/webhook`)
- [ ] Test subscription creation flow
- [ ] Subscription status updates correctly
- [ ] Pro features unlock after payment

### ✅ ML Pipeline (if using)
- [ ] `POST /api/v1/predictions/predict` returns reasonable scores
- [ ] `POST /api/v1/forecasts/run` generates forecasts  
- [ ] Models load without errors (check ML service logs)
- [ ] Batch processing works for multiple properties

### ✅ End-to-End Testing
```bash
cd frontend
npm run cy:run  # Should be green
```
- [ ] All critical user flows pass
- [ ] No console errors during E2E tests
- [ ] Performance within acceptable limits

### ✅ Security Basics
- [ ] JWT_SECRET is strong (32+ characters, random)
- [ ] Access tokens expire in 30-60 minutes  
- [ ] Refresh tokens expire in 7-14 days
- [ ] CORS restricted to production domains only
- [ ] HTTPS enforced (no HTTP in production)
- [ ] SQL injection protection (parameterized queries)

### ✅ Database & Storage
- [ ] PostgreSQL connection pooling enabled
- [ ] Database backups automated (daily minimum)
- [ ] Connection limits appropriate for load
- [ ] Migrations run cleanly (`alembic upgrade head`)

### ✅ Observability & Monitoring
- [ ] Structured logging with request_id, user_id, route, latency
- [ ] Error rate alerts configured (>1% 5xx responses)
- [ ] P95 latency alerts configured (>2 seconds)
- [ ] Webhook failure alerts configured  
- [ ] Daily backup verification job

### ✅ Legal & Compliance
- [ ] Terms of Service accessible at `/terms`
- [ ] Privacy Policy accessible at `/privacy` 
- [ ] Investment disclaimer on all ML predictions
- [ ] Contact information and support email configured

## 🛑 Stop/Fix Required Issues

If ANY of these are red lights, **STOP** and fix before inviting pilots:

- API health check fails
- Database connection errors
- Authentication completely broken
- Stripe webhooks failing (500 errors)
- HTTPS not working/certificates invalid
- No error monitoring/alerting
- No database backups

## ✅ Go Decision Criteria

**GREEN LIGHT** if:
- All API endpoints responding
- Core user journey works end-to-end  
- Stripe test payments work
- Basic monitoring in place
- Security fundamentals covered
- Legal pages accessible

**YELLOW LIGHT** (proceed with caution):
- Minor UI glitches that don't block core functionality
- Non-critical integrations failing (analytics, etc.)
- Performance slightly slower than ideal

**RED LIGHT** (do not launch):
- Core functionality broken
- Data loss risk
- Security vulnerabilities
- Payment processing broken

## Quick Commands for Health Checks

```bash
# API Health
curl https://api.capsight.ai/health

# Database Connection  
docker-compose exec backend python -c "from app.core.database import get_db; next(get_db())"

# Stripe Webhook Test
stripe listen --forward-to https://api.capsight.ai/api/v1/subscriptions/stripe/webhook

# Frontend Build Test
cd frontend && npm run build

# E2E Test Suite
cd frontend && npm run cy:run
```

## Rollback Plan

If issues found in production:

1. **Immediate**: Revert to previous Docker image
   ```bash
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml up -d image@previous_tag
   ```

2. **Database**: Restore from latest backup if schema changes
   ```bash
   pg_restore -d capsight_prod latest_backup.sql
   ```

3. **Communication**: Notify pilot users of temporary issues

---

## Post-Launch Monitoring (First 48 Hours)

Monitor these metrics closely:

- **Error Rate**: Should be <2%
- **Response Time**: P95 <3 seconds  
- **User Sessions**: Track active users
- **Payment Success**: Track Stripe conversion rates
- **Support Tickets**: Monitor for common issues

Success = smooth pilot onboarding with <1 critical issue per day.
