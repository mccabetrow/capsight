# CapSight Real-Time Data Integration

## 🎯 Overview

CapSight now features a comprehensive real-time data integration system that eliminates hardcoded values and provides fully auditable, traceable valuations with live data sources.

## 🏗️ Architecture

### Data Sources
- **Macro Data**: FRED API (Federal Reserve Economic Data)
  - Series: DFF (Federal Funds Rate), GS10 (10-Year Treasury)
  - Cache TTL: 30 minutes
  - Fallback: Previous cached values with circuit breaker

- **Market Fundamentals**: Supabase
  - Tables: `market_fundamentals`, `market_trends`
  - Freshness threshold: 90 days
  - Fallback: Error on insufficient data

- **Comparable Sales**: Supabase  
  - Table: `v_comps_trimmed`
  - Freshness threshold: 180 days
  - Minimum 3 comps required for confidence > 0.6

### Core Components

1. **DataFetcher Service** (`lib/data-fetcher.ts`)
   - Centralized data fetching with caching and circuit breakers
   - Comprehensive provenance tracking
   - Health monitoring and fallback logic

2. **Valuation API v2** (`pages/api/v2/valuation.ts`)
   - Real-time valuation using live data sources
   - Full provenance and confidence scoring
   - Debug mode for audit trails

3. **Health Monitoring** (`pages/api/health/data.ts`)
   - Data source health checks
   - Freshness monitoring across all markets
   - Circuit breaker status

4. **Webhook Ingestion** (`pages/api/ingest/webhook.ts`)
   - Event-driven data updates
   - HMAC signature verification
   - Automatic cache invalidation

5. **Cache Warming Cron** (`pages/api/cron/cache-warming.ts`)
   - Pre-fetches data every 6 hours
   - System maintenance and health checks
   - Performance optimization

## 🚀 Getting Started

### Environment Setup

Copy `.env.example` to `.env.local` and configure:

```bash
# Real-time Data Sources
FRED_API_KEY=your_fred_api_key_here
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Cache Configuration
CACHE_TTL_MACRO_MINUTES=30
CACHE_TTL_FUNDAMENTALS_HOURS=24
CACHE_TTL_COMPS_HOURS=24

# Data Freshness Thresholds (days)
FRESHNESS_MACRO_DAYS=7
FRESHNESS_FUNDAMENTALS_DAYS=90
FRESHNESS_COMPS_DAYS=180

# Security
WEBHOOK_SECRET=your_webhook_secret_here
CRON_SECRET=your_cron_secret_here
```

### Database Setup

Run the SQL setup script in your Supabase SQL editor:

```sql
-- See supabase-real-data-setup.sql for complete setup
```

### API Usage

#### Valuation API v2

```bash
POST /api/v2/valuation
Content-Type: application/json

{
  "market": "dfw",
  "building_sf": 200000,
  "noi_annual": 1800000,
  "debug": true
}
```

Response includes:
- Estimated value with confidence range
- Applied cap rate with risk adjustments
- Complete provenance chain
- Data freshness indicators
- Debug information (if requested)

#### Health Check

```bash
GET /api/health/data
```

Returns comprehensive system health including:
- Data source status and latency
- Market data freshness
- Circuit breaker states
- Cache performance metrics

## 📊 Data Flow

### Real-Time Valuation Process

1. **Data Fetching**
   - Fetch macro data from FRED API (cached 30min)
   - Get market fundamentals from Supabase (cached 24hr)
   - Retrieve comparable sales (cached 24hr)

2. **Validation & Freshness**
   - Check data freshness thresholds
   - Validate numeric ranges and constraints
   - Apply freshness penalties to confidence scores

3. **Calculation**
   - Calculate risk-adjusted cap rate using macro conditions
   - Apply market growth and credit spread adjustments
   - Perform income approach valuation
   - Validate against comparable sales

4. **Provenance & Confidence**
   - Track all data sources and timestamps
   - Calculate confidence based on data quality and freshness
   - Include debug information for audit trails

### Event-Driven Updates

```bash
POST /api/ingest/webhook
X-Signature: sha256=<hmac>
X-Timestamp: <unix_timestamp>

{
  "event_type": "market.fundamentals.upsert",
  "market_slug": "dfw",
  "data": { ... },
  "source": "internal_update"
}
```

Supported event types:
- `market.fundamentals.upsert`
- `comps.upsert`  
- `macro.update`

## 🔍 Monitoring & Observability

### Health Endpoints

- `GET /api/health/data` - Comprehensive health check
- `HEAD /api/health/data` - Lightweight liveness probe

### Cache Warming

```bash
POST /api/cron/cache-warming
Authorization: Bearer <cron_secret>
```

Runs every 6 hours to:
- Pre-fetch macro data for all markets
- Warm market fundamentals cache
- Load comparable sales data
- Perform system health checks

### Metrics & Logging

All operations include structured logging with:
- Correlation IDs per request
- Data source latencies
- Cache hit/miss ratios
- Circuit breaker state changes

## 🧪 Testing

### Contract Tests

```bash
npm test __tests__/contract.test.ts
```

Validates:
- FRED API response schemas
- Supabase data contracts
- Circuit breaker behavior
- Cache functionality

### Golden Tests

```bash
npm test __tests__/golden.test.ts
```

Ensures consistent valuations using known test data:
- DFW market with fixed inputs
- Expected outputs within ±3% tolerance
- Performance requirements (< 2s response time)

Test data located in `__tests__/testdata/dfw_golden.json`

## 🔧 Configuration

### Circuit Breakers

- **FRED API**: 3 failures → 2 minute timeout
- **Supabase**: 5 failures → 1 minute timeout
- Automatic recovery to half-open state

### Data Freshness Thresholds

- **Macro**: 7 days (aggressive due to market volatility)
- **Fundamentals**: 90 days (quarterly updates typical)
- **Comparables**: 180 days (sales transaction lag)

### Cache Strategy

- **Memory Cache**: In-process for low latency
- **TTL-based**: Automatic expiration
- **Event-driven**: Invalidation on data updates
- **Warming**: Proactive loading via cron job

## 🚨 Error Handling & Fallbacks

### Fallback Chain

1. **Live API** → 2. **Cache** → 3. **Circuit Breaker** → 4. **Error**

### Status Codes

- `FRESH`: All data within freshness thresholds
- `STALE_DATA`: Some data exceeds thresholds (confidence reduced)
- `INSUFFICIENT_DATA`: Missing critical data for valuation
- `CACHE_USED`: API unavailable, serving cached data

## 🔒 Security

### Webhook Authentication

- HMAC-SHA256 signatures
- Timestamp validation (5 minute window)
- Replay attack prevention

### API Security

- Service role keys for Supabase
- Bearer token auth for cron jobs
- Rate limiting (60 RPM default)

## 📈 Performance

### Benchmarks

- **Target Response Time**: < 2 seconds
- **Cache Hit Ratio**: > 80%
- **Data Source Latency**: FRED < 1s, Supabase < 500ms
- **Concurrent Requests**: Up to 10 simultaneous

### Optimization

- Parallel data fetching
- Intelligent caching with TTLs
- Circuit breakers prevent cascade failures
- Connection pooling for database access

## 🎛️ Admin Operations

### Cache Management

```javascript
// Invalidate specific cache
dataFetcher.invalidateCache('fundamentals_dfw')

// Clear all cache
dataFetcher.invalidateCache()
```

### Health Monitoring

Monitor `/api/health/data` endpoint for:
- Overall system status (healthy/degraded/unhealthy)
- Individual data source health
- Stale data alerts
- Circuit breaker states

### Data Updates

Use webhook endpoint for real-time updates or manual Supabase updates will be picked up within cache TTL.

## 📋 Deployment Checklist

### Pre-deployment

- [ ] FRED API key configured and tested
- [ ] Supabase tables created with real data
- [ ] Environment variables set
- [ ] Contract tests passing
- [ ] Golden tests within tolerance

### Post-deployment

- [ ] Health endpoint returning 200
- [ ] Cache warming cron job scheduled
- [ ] Webhook endpoints accessible
- [ ] Monitor logs for errors
- [ ] Validate first valuation response

## 🤝 Contributing

### Adding New Data Sources

1. Extend `DataFetcher` class with new fetch method
2. Add caching and circuit breaker logic
3. Update provenance tracking
4. Add contract tests
5. Update health checks

### Modifying Valuation Logic

1. Update calculation in `pages/api/v2/valuation.ts`
2. Adjust golden test expectations
3. Update debug output
4. Increment model version

---

## 🆘 Troubleshooting

### Common Issues

**"Circuit breaker OPEN"**
- Data source is failing, wait for automatic recovery
- Check data source health in logs
- Manual recovery: restart application

**"INSUFFICIENT_DATA"**
- Market fundamentals missing from Supabase
- Run database setup SQL script
- Check data ingestion webhooks

**High response times**
- Check cache hit ratios
- Monitor external API latencies  
- Consider increasing cache TTLs

**Stale data warnings**
- Data exceeds freshness thresholds
- Update market fundamentals in Supabase
- Check data ingestion pipeline

For additional support, check logs and health endpoints for detailed error information.
