import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metric for tracking rate limit responses
export let rateLimitRate = new Rate('rate_limit_rate');

// Test configuration
export let options = {
  // Ramp up from 1 to 50 VUs over 2 minutes
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 30 },
    { duration: '30s', target: 50 },
  ],
  
  // Performance thresholds
  thresholds: {
    // 95th percentile response time under 300ms
    'http_req_duration{status:200}': ['p(95)<300'],
    
    // Failure rate under 0.5% (excluding rate limits)
    'http_req_failed{status:!429}': ['rate<0.005'],
    
    // Track rate limits separately but don't fail on them
    'rate_limit_rate': ['rate<0.1'], // Allow up to 10% rate limits
    
    // Basic checks should pass
    'checks': ['rate>0.95'],
  },
};

// Base URL from environment variable (for staging/production testing)
const BASE_URL = __ENV.PERF_BASE_URL || 'http://localhost:8000';

// Realistic test payloads for 5 markets
const testPayloads = [
  // Dallas-Fort Worth (DFW)
  {
    market: 'dfw',
    building_sf: 250000,
    noi_annual: 1500000,
  },
  {
    market: 'dfw',
    building_sf: 85000,
    noi_annual: 680000,
  },
  {
    market: 'dfw',
    building_sf: 450000,
    noi_annual: 2250000,
  },
  
  // Austin (AUS)
  {
    market: 'aus',
    building_sf: 180000,
    noi_annual: 1260000,
  },
  {
    market: 'aus',
    building_sf: 320000,
    noi_annual: 2080000,
  },
  {
    market: 'aus',
    building_sf: 95000,
    noi_annual: 760000,
  },
  
  // Houston (HOU)
  {
    market: 'hou',
    building_sf: 400000,
    noi_annual: 2400000,
  },
  {
    market: 'hou',
    building_sf: 150000,
    noi_annual: 975000,
  },
  
  // San Antonio (SAT)
  {
    market: 'sat',
    building_sf: 200000,
    noi_annual: 1100000,
  },
  {
    market: 'sat',
    building_sf: 75000,
    noi_annual: 525000,
  },
  
  // Phoenix (PHX)
  {
    market: 'phx',
    building_sf: 300000,
    noi_annual: 1950000,
  },
  {
    market: 'phx',
    building_sf: 125000,
    noi_annual: 875000,
  },
];

export default function() {
  // Select a random payload for variety
  const payload = testPayloads[Math.floor(Math.random() * testPayloads.length)];
  
  // Make API request
  const response = http.post(`${BASE_URL}/api/value`, JSON.stringify(payload), {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      market: payload.market,
      building_size: payload.building_sf < 100000 ? 'small' : 
                    payload.building_sf < 300000 ? 'medium' : 'large'
    }
  });
  
  // Track rate limits separately (don't count as failures)
  rateLimitRate.add(response.status === 429);
  
  // Performance and correctness checks
  const checks = check(response, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    'response time OK': (r) => r.timings.duration < 500, // Warn threshold
    'has valuation data': (r) => r.status === 429 || (r.json() && r.json().valuation_total_usd > 0),
    'market matches': (r) => r.status === 429 || (r.json() && r.json().market_slug === payload.market),
  });
  
  // Only check detailed response structure for successful requests
  if (response.status === 200) {
    const data = response.json();
    check(data, {
      'has confidence intervals': (d) => d.valuation_low_usd && d.valuation_high_usd,
      'has method info': (d) => d.method && d.method_version,
      'has comp count': (d) => typeof d.comp_count === 'number',
      'reasonable cap rate': (d) => d.implied_cap_rate > 0.03 && d.implied_cap_rate < 0.15,
    });
  }
  
  // Brief pause between requests to simulate realistic usage
  sleep(Math.random() * 2 + 1); // 1-3 second random pause
}

// Setup function - run once before test starts
export function setup() {
  console.log(`Starting performance test against: ${BASE_URL}`);
  console.log(`Test payloads: ${testPayloads.length} variations across 5 markets`);
  
  // Health check before starting
  const healthResponse = http.get(`${BASE_URL}/api/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`Health check failed: ${healthResponse.status}`);
  }
  
  return { baseUrl: BASE_URL };
}

// Teardown function - run once after test completes
export function teardown(data) {
  console.log('Performance test completed');
  console.log(`Base URL: ${data.baseUrl}`);
}
