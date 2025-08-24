# Event-Driven Ingestion and Jobs System

## Overview

This system implements comprehensive event-driven ingestion, job tracking, cache metrics, and API request logging with full observability and contract testing.

## Architecture

### Core Components

1. **Ingestion Events** (`ingestion_events` table)
   - Tracks all data ingestion operations
   - Records processing time, cache invalidation, and provenance
   - Supports event types: market.fundamentals.upsert, comps.upsert, macro.update, api.prediction, cache.warming

2. **Jobs System** (`jobs` table)
   - Tracks long-running operations with status (QUEUED → RUNNING → COMPLETED/FAILED)
   - Job types: prediction, cache_warming, accuracy_check, data_sync
   - Includes input/output data, processing time, and error messages

3. **Cache Metrics** (`cache_metrics` table)
   - Monitors cache hit ratios, warming operations, and performance
   - Tagged metrics for filtering and aggregation
   - Real-time cache health monitoring

4. **API Requests** (`api_requests` table)
   - Logs all API requests with response times and status codes
   - Tracks cache hits, market context, and payload sizes
   - Enables performance analysis and debugging

### Database Schema

The complete schema is defined in `supabase-ingestion-schema.sql` with:
- Full tables with constraints and indexes
- Row Level Security (RLS) policies
- Utility functions for metrics aggregation
- Optimized queries for observability dashboards

## API Endpoints

### Health Endpoint
```
GET /api/health/data
```

Returns comprehensive system health:
```json
{
  "status": "GREEN|YELLOW|RED",
  "as_of": "2024-01-15T10:30:00Z",
  "services": {
    "macro": {
      "status": "GREEN",
      "source": "FRED",
      "last_success_at": "2024-01-15T10:25:00Z",
      "freshness_seconds": 150,
      "cache": { "used": true, "ttl_seconds": 300 },
      "breaker": { "state": "CLOSED", "failures": 0 }
    },
    "fundamentals": {
      "status": "YELLOW",
      "source": "Supabase",
      "last_row_as_of": "2024-01-14T00:00:00Z",
      "max_allowed_staleness_days": 30,
      "stale_markets": ["san-antonio"]
    },
    "comps": {
      "status": "GREEN",
      "source": "Supabase",
      "last_row_as_of": "2024-01-12T00:00:00Z",
      "min_required_recent": 10,
      "markets_below_min": []
    }
  },
  "metrics": {
    "cache_hit_ratio": { "macro": 0.85, "fundamentals": 0.72, "comps": 0.68 },
    "api_retry_count_5m": { "macro": 2, "fundamentals": 0, "comps": 1 },
    "prediction_latency_ms_p50": 245,
    "prediction_latency_ms_p95": 890
  }
}
```

### Ingestion Webhook
```
POST /api/ingest/webhook
```

Handles real-time data updates with:
- HMAC signature verification
- Idempotency protection
- Automatic cache invalidation
- Event logging and job tracking

### Cache Warming Cron
```
POST /api/cron/cache-warming
```

Automated cache warming every 6 hours:
- Pre-fetches macro data and market fundamentals
- Warms comparable sales cache
- Performs system health checks
- Logs all operations and metrics

## Logging Integration

### Automatic Logging

All API endpoints now include automatic logging:
```typescript
import { logIngestionEvent, createJob, updateJobStatus, logApiRequest } from '../../lib/ingestion-logger'

// In API handler
const job_id = await createJob({
  job_type: 'prediction',
  market_slug: 'dallas',
  input_data: { city, investment_criteria }
})

await updateJobStatus(job_id, { status: 'RUNNING' })

// ... processing ...

await updateJobStatus(job_id, { 
  status: 'COMPLETED',
  output_data: { predictions_count: 5 },
  processing_time_ms: 1200
})

await logIngestionEvent({
  event_type: 'api.prediction',
  market_slug: 'dallas',
  source: 'predict-properties-api',
  processed_records: 5,
  processing_time_ms: 1200
})
```

### Cache Metrics

Track cache performance:
```typescript
import { logCacheMetric } from '../../lib/ingestion-logger'

await logCacheMetric({
  metric_name: 'cache_hit_ratio',
  metric_value: 0.85,
  tags: { service: 'macro', market: 'dallas' }
})
```

## Observability Features

### Real-Time Metrics
- Cache hit ratios per service
- API response times (P50/P95)
- Job success/failure rates
- Data freshness monitoring

### Health Status Rules
- **GREEN**: All services healthy, fresh data, good performance
- **YELLOW**: 1 service degraded or some stale data (warnings)
- **RED**: 2+ services down or critical failures (alerts)

### Circuit Breaker Integration
- Automatic failure detection
- Graceful degradation
- Recovery monitoring

## Contract and Golden Tests

### Contract Tests (`__tests__/contract.test.ts`)
- Validates external service contracts (FRED, Supabase)
- Tests circuit breaker behavior
- Verifies cache functionality

### Golden Tests (`__tests__/golden.test.ts`)
- Known input/output validation
- Regression detection
- Performance benchmarking

## Environment Variables

Required environment variables for full functionality:

```bash
# Supabase (required)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# FRED API (required for real-time macro data)
FRED_API_KEY=your-fred-api-key

# Webhook security (production)
WEBHOOK_SECRET=your-webhook-secret

# Cron job security (production)
CRON_SECRET=your-cron-secret

# Cache TTL settings (optional)
CACHE_TTL_MACRO=300
CACHE_TTL_FUNDAMENTALS=3600
CACHE_TTL_COMPS=1800
```

## Deployment

1. **Apply Database Schema**:
   ```sql
   -- Run supabase-ingestion-schema.sql in Supabase SQL editor
   ```

2. **Configure Environment Variables**:
   - Set all required variables in your deployment environment
   - Ensure service role key has write access to ingestion tables

3. **Set Up Monitoring**:
   - Configure alerts on `/api/health/data` endpoint
   - Monitor job failure rates
   - Track cache hit ratios

4. **Schedule Cron Jobs**:
   - Set up cache warming to run every 6 hours
   - Configure webhook endpoints with your data providers

## Usage Examples

### Manual Cache Warming
```bash
curl -X POST https://your-domain.com/api/cron/cache-warming \
  -H "Authorization: Bearer your-cron-secret"
```

### Health Check
```bash
curl https://your-domain.com/api/health/data
```

### Trigger Webhook
```bash
curl -X POST https://your-domain.com/api/ingest/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: sha256=computed-hmac" \
  -H "X-Timestamp: 1642261200" \
  -d '{
    "event_type": "market.fundamentals.upsert",
    "market_slug": "dallas",
    "data": { ... },
    "source": "external-provider"
  }'
```

## Monitoring and Alerts

The system provides comprehensive monitoring through:
- Health endpoint status codes (200/503)
- Structured logging with job IDs
- Cache and performance metrics
- Contract test validation
- Event-driven audit trails

Configure alerts on:
- Health status RED (503 responses)
- Job failure rates > 5%
- Cache hit ratios < 70%
- API response times > 2 seconds
- Stale data > 30 days
