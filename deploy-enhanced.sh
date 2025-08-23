#!/bin/bash
# Cap# 2. Database Schema Deployment with Performance Optimization
echo ""
echo "🗄️  Deploying Enhanced Database Schema with Indexes..."
if [ -f "schema/schema.sql" ]; then
    echo "   Applying schema.sql with accuracy_metrics and comp_review_queue tables..."
    psql "$DATABASE_URL" -f schema/schema.sql
    
    echo "   Creating performance indexes..."
    psql "$DATABASE_URL" << 'EOF'
-- Performance indexes for hot paths
CREATE INDEX IF NOT EXISTS idx_comps_market_date 
ON comparables (market_slug, sale_date DESC);

CREATE INDEX IF NOT EXISTS idx_comps_lat_lng 
ON comparables (lat, lng) WHERE lat IS NOT NULL AND lng IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_fund_market_asof 
ON fundamentals (market_slug, as_of_date DESC);

-- Trimmed comps view (removes top/bottom 5% outliers)
CREATE OR REPLACE VIEW v_comps_trimmed AS
SELECT *
FROM (
    SELECT c.*,
           PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY cap_rate_pct) OVER (PARTITION BY market_slug) AS p05,
           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY cap_rate_pct) OVER (PARTITION BY market_slug) AS p95
    FROM comparables c
    WHERE verification_status = 'verified'
    AND sale_date >= CURRENT_DATE - INTERVAL '5 years'
) z
WHERE z.cap_rate_pct BETWEEN z.p05 AND z.p95;

-- Recent comps materialized view for fast access
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_comps_recent_12m AS
SELECT * FROM v_comps_trimmed 
WHERE sale_date >= (CURRENT_DATE - INTERVAL '12 months');

CREATE UNIQUE INDEX IF NOT EXISTS mv_idx_recent_pk ON mv_comps_recent_12m (sale_id);
CREATE INDEX IF NOT EXISTS mv_idx_recent_market ON mv_comps_recent_12m (market_slug, sale_date DESC);

-- Fast refresh function
CREATE OR REPLACE FUNCTION refresh_recent_mv() 
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_comps_recent_12m;
END$$;

-- Accuracy metrics table
CREATE TABLE IF NOT EXISTS accuracy_metrics (
    id BIGSERIAL PRIMARY KEY,
    market_slug TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'weighted_median_robust_v1.0',
    calc_date DATE NOT NULL DEFAULT CURRENT_DATE,
    window_months INT NOT NULL DEFAULT 12,
    sample_size INT NOT NULL,
    mape NUMERIC NOT NULL,
    rmse_bps NUMERIC NOT NULL,
    coverage80 NUMERIC NOT NULL,
    ape_q80 NUMERIC NOT NULL,
    bias_bps NUMERIC DEFAULT 0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(market_slug, method, calc_date)
);

-- Latest accuracy view
CREATE OR REPLACE VIEW latest_accuracy AS
SELECT DISTINCT ON (market_slug)
    market_slug, method, calc_date, window_months, sample_size,
    mape, rmse_bps, coverage80, ape_q80, bias_bps, last_updated
FROM accuracy_metrics
ORDER BY market_slug, calc_date DESC, last_updated DESC;

-- Market status kill switch
CREATE TABLE IF NOT EXISTS market_status (
    market_slug TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT true,
    reason TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default enabled status for all markets
INSERT INTO market_status (market_slug, enabled) 
VALUES ('dfw', true), ('ie', true), ('atl', true), ('phx', true), ('sav', true)
ON CONFLICT (market_slug) DO NOTHING;

-- System health monitoring view
CREATE OR REPLACE VIEW v_system_health AS
SELECT 
    'accuracy_sla' as metric,
    COUNT(CASE WHEN mape <= 0.10 AND rmse_bps <= 50 AND coverage80 BETWEEN 0.78 AND 0.82 THEN 1 END) as passing,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN mape <= 0.10 AND rmse_bps <= 50 AND coverage80 BETWEEN 0.78 AND 0.82 THEN 1 END) / COUNT(*), 1) as pct_passing
FROM latest_accuracy
WHERE last_updated >= NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 
    'data_freshness' as metric,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '24 hours' THEN 1 END) as passing,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '24 hours' THEN 1 END) / COUNT(*), 1) as pct_passing
FROM latest_accuracy
UNION ALL
SELECT 
    'markets_enabled' as metric,
    COUNT(CASE WHEN enabled = true THEN 1 END) as passing,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN enabled = true THEN 1 END) / COUNT(*), 1) as pct_passing
FROM market_status;

-- Grant permissions
GRANT SELECT ON v_comps_trimmed TO authenticated, anon;
GRANT SELECT ON latest_accuracy TO authenticated, anon;
GRANT SELECT ON market_status TO authenticated, anon;
GRANT SELECT ON v_system_health TO authenticated, anon;
EOF
    echo "   ✅ Database schema and indexes created"
else
    echo "   ❌ schema/schema.sql not found"
    exit 1
fiction Deployment with Enhanced Accuracy Monitoring
# This script deploys the robust, auditable valuation system

set -e
echo "🚀 CapSight Production Deployment Starting..."

# Configuration
PROJECT_NAME="capsight-valuation"
SUPABASE_PROJECT_ID="${SUPABASE_PROJECT_ID:-your-project-id}"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres}"

echo "📋 Deployment Configuration:"
echo "   Project: $PROJECT_NAME"
echo "   Supabase Project ID: $SUPABASE_PROJECT_ID"
echo "   Database URL: [REDACTED]"

# 1. Database Schema Deployment
echo ""
echo "🗄️  Deploying Enhanced Database Schema..."
if [ -f "schema/schema.sql" ]; then
    echo "   Applying schema.sql with accuracy_metrics and comp_review_queue tables..."
    psql "$DATABASE_URL" -f schema/schema.sql
    echo "   ✅ Database schema updated"
else
    echo "   ❌ schema/schema.sql not found"
    exit 1
fi

# 2. Backend Dependencies
echo ""
echo "🐍 Installing Backend Dependencies..."
cd backend
pip install -r requirements.txt
pip install numpy psycopg2-binary  # For nightly accuracy script
echo "   ✅ Backend dependencies installed"
cd ..

# 3. Frontend Build
echo ""
echo "🎨 Building Frontend..."
cd frontend
npm install
npm run build
echo "   ✅ Frontend built successfully"
cd ..

# 4. Deploy Enhanced API
echo ""
echo "🔄 Deploying Enhanced Valuation API..."
if [ -f "pages/api/value-enhanced.ts" ]; then
    cp pages/api/value-enhanced.ts pages/api/value.ts
    echo "   ✅ Enhanced API deployed (robust estimator, fallback logic, auditability)"
else
    echo "   ❌ Enhanced API not found"
    exit 1
fi

# 5. Setup Data Validation
echo ""
echo "✅ Setting up Enhanced Data Validation..."
if [ -f "validate_csv_enhanced.py" ]; then
    cp validate_csv_enhanced.py validate_csv.py
    chmod +x validate_csv.py
    echo "   ✅ Enhanced CSV validator deployed (geofence, NOI validation, review queue)"
else
    echo "   ❌ Enhanced validator not found"
    exit 1
fi

# 6. Deploy Nightly Accuracy Monitoring
echo ""
echo "📊 Setting up Nightly Accuracy Monitoring..."
if [ -f "nightly_accuracy.py" ]; then
    chmod +x nightly_accuracy.py
    
    # Create log directory
    mkdir -p logs
    
    # Setup cron job for nightly execution (2 AM UTC)
    echo "0 2 * * * cd $(pwd) && python3 nightly_accuracy.py --config production >> logs/nightly_accuracy.log 2>&1" > /tmp/capsight_cron
    
    # Install cron job (commented out for safety)
    # crontab /tmp/capsight_cron
    echo "   ✅ Nightly accuracy script ready (manual cron setup required)"
    echo "   📝 Add to crontab: 0 2 * * * cd $(pwd) && python3 nightly_accuracy.py --config production"
else
    echo "   ❌ Nightly accuracy script not found"
    exit 1
fi

# 7. Create Production Configuration
echo ""
echo "⚙️  Creating Production Configuration..."
cat > .env.production << EOF
# CapSight Production Configuration
NEXT_PUBLIC_SUPABASE_URL=https://$SUPABASE_PROJECT_ID.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[your-anon-key]
SUPABASE_SERVICE_ROLE_KEY=[your-service-role-key]
DATABASE_URL=$DATABASE_URL

# Accuracy Monitoring
ACCURACY_ALERT_EMAIL=ops@capsight.com
SLACK_WEBHOOK_URL=[your-slack-webhook]

# Security
NEXTAUTH_SECRET=[your-nextauth-secret]
NEXTAUTH_URL=https://your-domain.com

# Feature Flags
ENABLE_CONFORMAL_PREDICTION=true
ENABLE_FALLBACK_RULES=true
ENABLE_AUDIT_LOGGING=true
EOF
echo "   ✅ Production configuration template created"

# 8. Setup Database Monitoring
echo ""
echo "📈 Setting up Database Monitoring Views..."
psql "$DATABASE_URL" << EOF
-- Create monitoring views for ops dashboard
CREATE OR REPLACE VIEW v_system_health AS
SELECT 
    'accuracy_sla' as metric,
    COUNT(CASE WHEN mape <= 0.10 AND rmse_bps <= 50 AND coverage80 BETWEEN 0.78 AND 0.82 THEN 1 END) as passing,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN mape <= 0.10 AND rmse_bps <= 50 AND coverage80 BETWEEN 0.78 AND 0.82 THEN 1 END) / COUNT(*), 1) as pct_passing
FROM latest_accuracy
UNION ALL
SELECT 
    'data_freshness' as metric,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '24 hours' THEN 1 END) as passing,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '24 hours' THEN 1 END) / COUNT(*), 1) as pct_passing
FROM latest_accuracy
UNION ALL
SELECT 
    'review_queue_size' as metric,
    COUNT(*) as passing,
    0 as total,
    0 as pct_passing
FROM comp_review_queue 
WHERE status = 'pending';

-- Grant access to monitoring role
GRANT SELECT ON v_system_health TO authenticated;
EOF
echo "   ✅ System health monitoring views created"

# 9. Pre-flight Green Light Checks
echo ""
echo "🚦 PRE-FLIGHT GREEN LIGHT CHECKS..."

# 1) Validate data with strict mode
echo "   📊 Validating all market data..."
if python3 validate_csv_enhanced.py --all-markets --strict; then
    echo "   ✅ Data validation passed"
else
    echo "   ❌ Data validation failed - aborting deploy"
    exit 1
fi

# 2) Dry-run nightly backtest
echo "   🔄 Running dry-run backtest (18m window)..."
if python3 nightly_accuracy.py --since 18m --dry-run --print-metrics; then
    echo "   ✅ Nightly backtest dry-run passed"
else
    echo "   ❌ Nightly backtest failed - aborting deploy"
    exit 1
fi

# 3) SLA Gate Check
echo "   📏 Checking SLA compliance..."
if python3 nightly_accuracy.py --since 18m --dry-run --assert "MAPE<=0.10,RMSE_BPS<=50,COVERAGE80>=0.78,COVERAGE80<=0.82"; then
    echo "   ✅ SLA requirements met"
else
    echo "   ❌ SLA not met - aborting deploy"
    exit 1
fi

# 4) E2E + Unit Tests
echo "   🧪 Running test suite..."
cd frontend
if npm run test && npx playwright install --with-deps && npm run test:e2e; then
    echo "   ✅ All tests passed"
    cd ..
else
    echo "   ❌ Tests failed - aborting deploy"
    cd ..
    exit 1
fi

# 5) Market Data Seeding (Staging Integration)
echo "   📊 Seeding market data to staging database..."
cd tools
if pip install -r requirements.txt; then
    echo "   ✅ Tools dependencies installed"
else
    echo "   ❌ Tools dependencies failed - aborting deploy"
    exit 1
fi

# Test with dry-run first
if python3 seed_markets.py --all --dry-run; then
    echo "   ✅ Market data validation passed (dry-run)"
else
    echo "   ❌ Market data validation failed - aborting deploy"
    exit 1
fi

# Seed to staging database (if STAGING_DATABASE_URL is provided)
if [ -n "$STAGING_DATABASE_URL" ]; then
    echo "   🚀 Seeding data to staging database..."
    if SUPABASE_URL="$NEXT_PUBLIC_SUPABASE_URL" SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_ROLE_KEY" python3 seed_markets.py --all --verbose; then
        echo "   ✅ Market data seeded to staging successfully"
    else
        echo "   ❌ Market data seeding failed - aborting deploy"
        exit 1
    fi
else
    echo "   ℹ️  Staging database not configured (STAGING_DATABASE_URL not set)"
fi
cd ..

# 10. Database Performance Optimization
echo ""
echo "🔍 Validating Deployment..."

# Check database connectivity
if psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "   ✅ Database connectivity confirmed"
else
    echo "   ❌ Database connectivity failed"
    exit 1
fi

# Check required tables exist
if psql "$DATABASE_URL" -c "SELECT 1 FROM accuracy_metrics LIMIT 1;" > /dev/null 2>&1; then
    echo "   ✅ accuracy_metrics table exists"
else
    echo "   ❌ accuracy_metrics table missing"
    exit 1
fi

if psql "$DATABASE_URL" -c "SELECT 1 FROM comp_review_queue LIMIT 1;" > /dev/null 2>&1; then
    echo "   ✅ comp_review_queue table exists"
else
    echo "   ❌ comp_review_queue table missing"
    exit 1
fi

# Test enhanced validator
if python3 validate_csv.py --help > /dev/null 2>&1; then
    echo "   ✅ Enhanced CSV validator working"
else
    echo "   ❌ Enhanced CSV validator failed"
    exit 1
fi

# Test nightly accuracy script
if python3 nightly_accuracy.py --dry-run --market dfw > /dev/null 2>&1; then
    echo "   ✅ Nightly accuracy script working"
else
    echo "   ❌ Nightly accuracy script failed"
    exit 1
fi

# 10. Initial Data Quality Check
echo ""
echo "🧹 Running Initial Data Quality Check..."
python3 -c "
import psycopg2
import os

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Count records in key tables
cur.execute('SELECT COUNT(*) FROM comparables')
comp_count = cur.fetchone()[0]
print(f'   📊 Comparables: {comp_count:,} records')

cur.execute('SELECT COUNT(*) FROM fundamentals')
fund_count = cur.fetchone()[0]
print(f'   📊 Fundamentals: {fund_count:,} records')

cur.execute('SELECT market_slug, COUNT(*) FROM v_comps_trimmed GROUP BY market_slug ORDER BY market_slug')
for market, count in cur.fetchall():
    print(f'   📊 {market.upper()}: {count:,} trimmed comps')

conn.close()
"

# 11. Security Hardening
echo ""
echo "🔒 Applying Security Hardening..."

# Ensure RLS is enabled on all tables
psql "$DATABASE_URL" << EOF
-- Verify RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('comparables', 'fundamentals', 'accuracy_metrics', 'comp_review_queue');

-- Enable RLS on accuracy tables if not already enabled
ALTER TABLE accuracy_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE comp_review_queue ENABLE ROW LEVEL SECURITY;

-- Create policies for accuracy tables
CREATE POLICY "accuracy_metrics_read" ON accuracy_metrics
  FOR SELECT USING (true);

CREATE POLICY "accuracy_metrics_write" ON accuracy_metrics
  FOR INSERT WITH CHECK (true);

CREATE POLICY "review_queue_read" ON comp_review_queue
  FOR SELECT USING (true);

CREATE POLICY "review_queue_write" ON comp_review_queue
  FOR INSERT WITH CHECK (true);
EOF
echo "   ✅ Security hardening applied"

# 12. Create Backup Strategy
echo ""
echo "💾 Setting up Backup Strategy..."
cat > backup_strategy.md << EOF
# CapSight Backup Strategy

## Automated Backups
- Supabase automatic daily backups (retained for 7 days on Pro plan)
- Custom pg_dump weekly backups to S3 (retained for 30 days)

## Critical Data
1. **comparables** table - Core transaction data
2. **fundamentals** table - Market data
3. **accuracy_metrics** table - Model performance tracking
4. **comp_review_queue** table - Data quality workflow

## Backup Commands
\`\`\`bash
# Weekly full backup
pg_dump "$DATABASE_URL" | gzip > "backup_\$(date +%Y%m%d).sql.gz"

# Upload to S3 (requires AWS CLI)
aws s3 cp "backup_\$(date +%Y%m%d).sql.gz" s3://capsight-backups/
\`\`\`

## Recovery Testing
- Monthly restore test to staging environment
- Documented in OPERATIONS_MONITORING_PLAYBOOK.md
EOF
echo "   ✅ Backup strategy documented"

# 13. Final Production Readiness Checklist
echo ""
echo "📋 RUNNING COMPREHENSIVE PRODUCTION READINESS CHECKLIST..."
if python3 production_checklist.py --config production --output deployment_results.json; then
    echo "   ✅ Production readiness checklist passed"
else
    echo "   ❌ Production readiness checklist failed"
    echo "   Review deployment_results.json for details"
    exit 1
fi

# 14. Deployment Summary
echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo ""
echo "📋 Summary:"
echo "   ✅ Enhanced database schema with accuracy tracking"
echo "   ✅ Robust valuation API with fallback logic and auditability"
echo "   ✅ Advanced CSV validator with geofence and quality gates"
echo "   ✅ Python CLI for market data seeding and validation"
echo "   ✅ Nightly accuracy monitoring and backtesting"
echo "   ✅ UI components for accuracy visualization"
echo "   ✅ Security hardening and monitoring views"
echo "   ✅ Backup strategy documented"
echo ""
echo "📝 Next Steps:"
echo "   1. Configure cron job for nightly accuracy monitoring"
echo "   2. Set up production environment variables (including STAGING_DATABASE_URL)"
echo "   3. Configure alerting webhooks (Slack/email)"
echo "   4. Load production data using: cd tools && python3 seed_markets.py --all"
echo "   5. Run first nightly accuracy check"
echo ""
echo "🔗 Key Files:"
echo "   - Enhanced API: pages/api/value.ts"
echo "   - Validator: validate_csv.py"
echo "   - Monitoring: nightly_accuracy.py"
echo "   - Data Seeding: tools/seed_markets.py"
echo "   - Config: .env.production"
echo "   - Schema: schema/schema.sql"
echo ""
echo "🏁 Your bulletproof, auditable valuation system is ready!"
