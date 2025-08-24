# CapSight Ingestion Pipeline

## Overview

The CapSight Ingestion Pipeline is a robust, production-grade system for automatically ingesting, processing, and scoring commercial real estate property data. It transforms raw property data from various public sources into actionable investment insights.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Connectors     │    │  Normalization  │
│                 │───▶│                  │───▶│                 │
│ • County APIs   │    │ • County Data    │    │ • Address Clean │
│ • CSV Files     │    │ • ACS Demo       │    │ • Geocoding     │
│ • BLS Data      │    │ • BLS Employment │    │ • Deduplication │
│ • FEMA Flood    │    │ • FEMA Risk      │    │ • ID Generation │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Webhooks      │    │   Persistence    │    │   Enrichment    │
│                 │    │                  │    │                 │
│ • n8n Events    │◀───│ • Supabase DB    │◀───│ • Market Data   │
│ • HMAC Security │    │ • Bulk Upserts   │    │ • Demographics  │
│ • Retry Logic   │    │ • Health Checks  │    │ • Flood Risk    │
└─────────────────┘    └──────────────────┘    │ • Broadband     │
                                               └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Deal Score      │    │   Valuation      │    │    Scoring      │
│ MTS Score       │◀───│                  │◀───│                 │
│ Yield Signal    │    │ • Income Method  │    │ • Deal Score    │
│ Classification  │    │ • Comp Method    │    │ • MTS Analysis  │
└─────────────────┘    │ • Forecasting    │    │ • Yield Signals │
                       └──────────────────┘    └─────────────────┘
```

## Features

### ✅ **Multi-Source Data Connectors**
- County assessor data (CSV/API)
- American Community Survey demographics
- Bureau of Labor Statistics employment data
- FEMA flood risk data
- FCC broadband coverage data

### ✅ **Robust Data Processing**
- Address cleaning and standardization
- Geocoding with Mapbox/Nominatim fallback
- Duplicate detection and deduplication
- Data quality validation

### ✅ **Advanced Enrichment**
- Real-time market fundamentals
- Demographics by ZIP/county
- Flood risk assessment
- Broadband coverage analysis
- NOI estimation

### ✅ **Proprietary Scoring**
- **Deal Score**: Value opportunity relative to market
- **MTS Score**: Market tension and supply/demand dynamics  
- **Yield Signal**: Income generation potential
- Property classification (A, B+, B, B-, C, D)

### ✅ **Production-Grade Infrastructure**
- TypeScript strict mode with comprehensive typing
- HMAC-secured webhook integration
- Bulk processing with batching
- Error handling and retry logic
- Health monitoring and observability

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Required environment variables
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
MAPBOX_ACCESS_TOKEN=pk.your_mapbox_token
N8N_WEBHOOK_URL=https://your-n8n-webhook-url
N8N_WEBHOOK_SECRET=your-webhook-secret
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Run Pipeline

```bash
# Full pipeline with 100 properties
node run-ingestion.mjs --max-properties 100

# Dry run without database saves
node run-ingestion.mjs --dry-run --max-properties 10

# Health check
node run-ingestion.mjs --health-check
```

## CLI Usage

### Basic Commands

```bash
# Run full pipeline
node run-ingestion.mjs

# Limit property count
node run-ingestion.mjs --max-properties 500

# Dry run (no database writes)
node run-ingestion.mjs --dry-run

# Disable webhooks
node run-ingestion.mjs --disable-webhooks

# Skip specific stages
node run-ingestion.mjs --skip-stages persistence,webhooks
```

### Advanced Options

```bash
# Custom data source
node run-ingestion.mjs --county-data county_2024.csv

# Custom run ID
node run-ingestion.mjs --run-id pipeline-$(date +%Y%m%d)

# Health check
node run-ingestion.mjs --health-check
```

## API Endpoints

### Run Pipeline

```http
POST /api/ingestion/run
Content-Type: application/json

{
  "max_properties": 100,
  "enable_webhooks": true,
  "dry_run": false,
  "skip_stages": []
}
```

### Health Check

```http
GET /api/ingestion/health
```

Response:
```json
{
  "healthy": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "geocoding": {
      "status": "healthy",
      "cache_size": 1250,
      "cache_hit_rate": 85,
      "total_requests": 8420
    },
    "database": {
      "status": "healthy",
      "properties_count": 125000,
      "valuations_count": 124850,
      "scores_count": 124800
    },
    "webhooks": {
      "status": "healthy",
      "latency_ms": 120
    }
  }
}
```

## Pipeline Stages

### 1. **Ingestion**
- Fetch raw property data from configured connectors
- Support for CSV files, APIs, and bulk data sources
- Rate limiting and error handling

### 2. **Normalization** 
- Clean and standardize addresses
- Geocode properties to lat/lon coordinates
- Generate deterministic property IDs
- Build provenance chain

### 3. **Enrichment**
- Fetch market fundamentals by MSA
- Add demographic data by ZIP/county
- Assess flood risk via FEMA zones
- Check broadband coverage
- Calculate estimated NOI

### 4. **Valuation**
- Income approach valuation
- Comparable sales analysis (when available)
- 12-month forecast values
- Confidence scoring

### 5. **Scoring**
- **Deal Score**: Market opportunity analysis
- **MTS Score**: Supply/demand tension
- **Yield Signal**: Income potential
- Property classification and ranking

### 6. **Persistence**
- Bulk upsert to Supabase tables
- Atomic operations with rollback
- Data integrity validation

### 7. **Webhooks**
- Emit events to n8n workflow
- HMAC security with replay protection
- Retry logic with exponential backoff
- High-value opportunity alerts

## Data Model

### Core Tables

#### `properties`
- Normalized property records
- Address, location, physical characteristics
- Assessment data and ownership

#### `features_properties`  
- Enriched property features
- Market fundamentals, demographics
- Risk factors, computed financials

#### `valuations`
- Property valuation results
- Current and forecast values
- Confidence intervals

#### `scores`
- CapSight proprietary scores
- Deal Score, MTS, Yield Signal
- Classification and confidence

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key | ✅ |
| `MAPBOX_ACCESS_TOKEN` | Mapbox geocoding token | ✅ |
| `N8N_WEBHOOK_URL` | n8n webhook endpoint | ✅ |
| `N8N_WEBHOOK_SECRET` | Webhook HMAC secret | ✅ |
| `MAX_BATCH_SIZE` | Processing batch size | ⚪ |
| `GEOCODING_CACHE_TTL_HOURS` | Geocoding cache TTL | ⚪ |

### Pipeline Options

```typescript
interface PipelineOptions {
  run_id?: string                // Custom run identifier
  max_properties?: number        // Limit property count
  enable_webhooks?: boolean      // Enable webhook events
  county_data_source?: string    // Data source path/ID
  skip_stages?: string[]         // Stages to skip
  dry_run?: boolean             // Skip database writes
}
```

## Monitoring

### Health Metrics

- **Geocoding**: Cache hit rate, request count
- **Database**: Record counts, connection health  
- **Webhooks**: Latency, success rate
- **Pipeline**: Success rate, error counts

### Observability

```bash
# View logs during execution
node run-ingestion.mjs --max-properties 10

# Health check with detailed metrics
node run-ingestion.mjs --health-check
```

### Error Handling

- Automatic retries with exponential backoff
- Stage-level error isolation
- Comprehensive error logging
- Webhook failure notifications

## Development

### Project Structure

```
lib/
├── ingestion-config.ts        # Environment validation
├── ingestion-types.ts         # TypeScript definitions
├── geocode.ts                # Geocoding service
├── normalize.ts              # Data normalization
├── enrichment.ts             # Property enrichment
├── scoring.ts                # Scoring algorithms
├── supabase-ingestion.ts     # Database operations
├── webhook-emission.ts       # Event emission
└── ingestion-orchestrator.ts # Main coordinator

connectors/
└── county-data.ts            # County data connector

pages/api/ingestion/
├── run.ts                    # API endpoint
└── health.ts                 # Health check endpoint
```

### Adding New Connectors

```typescript
// connectors/new-source.ts
export class NewSourceConnector implements DataConnector {
  async fetchProperties(source: string, limit?: number): Promise<RawProperty[]> {
    // Implementation
  }
}
```

### Custom Scoring Models

```typescript
// lib/scoring.ts - extend scoring algorithms
private computeCustomScore(property: CapsightProperty): number {
  // Custom scoring logic
  return score
}
```

## Testing

```bash
# Dry run with small dataset
node run-ingestion.mjs --dry-run --max-properties 5

# Test specific stages
node run-ingestion.mjs --skip-stages persistence,webhooks

# Health check
node run-ingestion.mjs --health-check
```

## Production Deployment

### Performance Recommendations

- Use batching for large datasets (`MAX_BATCH_SIZE=1000`)
- Enable geocoding cache (`GEOCODING_CACHE_TTL_HOURS=168`)
- Configure webhook retries appropriately
- Monitor database connection pools

### Scaling Considerations

- Horizontal scaling via multiple pipeline instances
- Database read replicas for health checks
- Webhook rate limiting and circuit breakers
- Caching for frequently accessed market data

### Security

- Environment variable encryption at rest
- HMAC webhook signatures
- Service role key rotation
- Network security groups

## Support

For questions or issues:

1. Check the health endpoint: `GET /api/ingestion/health`
2. Run diagnostic: `node run-ingestion.mjs --health-check`
3. Review logs for error details
4. Verify environment configuration

## Changelog

### v1.0.0
- Initial release with 7-stage pipeline
- County data connector
- CapSight proprietary scoring
- HMAC-secured webhook integration
- Comprehensive health monitoring
- Production-grade error handling
