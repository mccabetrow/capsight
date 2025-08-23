# Release Notes

## v1.0.0 - Production Launch (August 23, 2025)

### 🎉 Initial Production Release

**Core Features:**
- Industrial CRE valuation for 5 pilot markets (DFW, IE, ATL, PHX, SAV)
- Weighted median cap rate methodology with ±50bps confidence intervals
- Real-time market fundamentals and comparable sales data
- Professional UI with responsive design

**Technical Foundation:**
- Next.js 14 with TypeScript
- Supabase PostgreSQL with Row Level Security (RLS)
- Secure public views for frontend data access
- Environment variable configuration (no hardcoded secrets)

**Security & Compliance:**
- Database-level access control via RLS policies
- Browser-safe anon key usage only
- Service role key restricted to API routes
- Comprehensive input validation

**Data Quality:**
- CSV templates for all 5 markets
- Python validation script with cross-field checks
- Market slug enforcement and enum validation
- Data freshness indicators

**Testing & CI/CD:**
- Jest unit tests with React Testing Library
- Playwright E2E tests across browsers
- GitHub Actions CI pipeline
- Automated deployment to Vercel

**Monitoring:**
- `/api/accuracy` endpoint for SLA monitoring
- Green/Amber/Red status based on MAPE, RMSE, coverage targets
- Error tracking and graceful fallbacks

**SLA Targets:**
- Valuation MAPE ≤ 10%
- Cap rate RMSE ≤ 50 bps
- Confidence interval coverage: 78-82%
- Response time < 500ms TTFB

### 🛡️ Security Measures
- All database access via secure views
- No service role keys in browser code
- CORS properly configured in Supabase
- Environment variables for all secrets

### 📊 Market Coverage
- Dallas-Fort Worth (DFW)
- Inland Empire (IE)  
- Atlanta (ATL)
- Phoenix (PHX)
- Savannah (SAV)

### 🚀 Deployment Ready
- Vercel-optimized configuration
- Production environment variable templates
- Rollback capabilities via deployment history
- Domain setup instructions

---

## Schema Changes

### v1.0.0 Schema
- `markets` table with slug-based identification
- `market_fundamentals` with market_slug for easier joins
- `industrial_sales` with NOI column and verification status
- `eval_metrics` for accuracy monitoring
- Secure public views: `v_market_fundamentals_latest`, `v_verified_sales_18mo`

### RLS Policies
- Public read access to markets
- View-based access for fundamentals and sales
- Service role access for eval_metrics

---

## Breaking Changes
None (initial release)

---

## Known Issues
- Playwright type errors in development (does not affect runtime)
- CSS Tailwind warnings in development (does not affect styling)

---

## Upgrade Notes
This is the initial release. Future upgrades will include migration instructions here.

---

## Contributors
- Production deployment and architecture
- Frontend UI/UX implementation  
- Database schema and security implementation
- Testing infrastructure and CI/CD pipeline
