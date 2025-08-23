# Performance Testing

This directory contains k6 performance tests for the CapSight API.

## Overview

The performance tests validate API response times and reliability under load, ensuring the valuation service meets production SLA requirements.

## Test Structure

### value.js
- **Load Pattern**: Ramps from 1→50 virtual users over 2 minutes
- **Test Data**: 12 realistic payloads across 5 markets (DFW, AUS, HOU, SAT, PHX)
- **Building Sizes**: Small (<100k SF), Medium (100k-300k SF), Large (>300k SF)
- **NOI Range**: $525k - $2.4M annually

### Performance Thresholds
- **95th Percentile**: < 300ms response time
- **Failure Rate**: < 0.5% (excluding rate limits)
- **Rate Limits**: Up to 10% allowed (429 responses don't count as failures)
- **Health Checks**: > 95% pass rate

## Running Locally

### Prerequisites
- Docker installed
- API server running on localhost:8000

### Quick Start
```bash
# From project root
docker run -i loadimpact/k6 run - < perf/value.js
```

### With Custom Base URL
```bash
# Test against staging
docker run -e PERF_BASE_URL=https://staging.capsight.com -i loadimpact/k6 run - < perf/value.js

# Test with more detailed output
docker run -i loadimpact/k6 run --out json=results.json - < perf/value.js
```

### Advanced Options
```bash
# Longer test duration
docker run -i loadimpact/k6 run --duration 5m --vus 25 - < perf/value.js

# HTML report generation
docker run -i loadimpact/k6 run --out json=results.json - < perf/value.js
docker run --rm -v $(pwd):/data -i loadimpact/k6 run --out json=/data/results.json - < perf/value.js
```

## Interpreting Results

### Success Metrics
- **http_req_duration**: Response times by percentile
- **http_req_rate**: Requests per second throughput
- **http_req_failed**: Overall failure rate
- **rate_limit_rate**: Rate limiting frequency (informational)

### Key Indicators
- ✅ **Green**: All thresholds passed
- ⚠️ **Yellow**: Some checks failed but within limits
- ❌ **Red**: Critical thresholds breached

### Common Issues
- **High response times**: Database query optimization needed
- **Rate limit spikes**: May need to adjust rate limiting windows
- **Validation failures**: API response schema changes

## CI/CD Integration

Performance tests run automatically on:
- **Pull Requests**: Against staging environment
- **Deployments**: Before production release
- **Scheduled**: Nightly regression testing

### Environment Variables
- `PERF_BASE_URL`: Target API endpoint
- `PERF_DURATION`: Test duration override
- `PERF_VUS`: Virtual user count override

## Monitoring

Results are published to:
- GitHub Actions artifacts (JUnit + HTML reports)
- Performance dashboard (Grafana)
- Slack alerts on threshold breaches

## Market Coverage

Tests validate performance across all supported markets:
- **DFW**: Dallas-Fort Worth
- **AUS**: Austin
- **HOU**: Houston  
- **SAT**: San Antonio
- **PHX**: Phoenix

Each market tested with representative building sizes and NOI values to ensure consistent performance across different property types and valuations.

## Debugging

### Local Development
```bash
# Start API server with debug logging
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

# Run single iteration for debugging  
docker run -i loadimpact/k6 run --iterations 1 --vus 1 - < perf/value.js
```

### Staging Issues
```bash
# Test specific market
export PERF_BASE_URL=https://staging.capsight.com
docker run -e PERF_BASE_URL -i loadimpact/k6 run --iterations 5 --vus 1 - < perf/value.js
```

For support, see the main project README or contact the development team.
