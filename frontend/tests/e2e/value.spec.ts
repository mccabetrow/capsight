import { test, expect } from '@playwright/test'

// CapSight E2E "Truth Tests" - Catch regressions fast
// These tests assert core system invariants that should never break

test.describe('CapSight Valuation API Truth Tests', () => {
  
  test('DFW warehouse with typical NOI returns sane valuation', async ({ request }) => {
    const response = await request.post('/api/value', {
      data: {
        market_slug: 'dfw',
        noi_annual: 1000000, // $1M NOI
        building_sf: 100000  // 100K SF
      }
    })
    
    expect(response.ok()).toBeTruthy()
    const result = await response.json()
    
    // Core valuation sanity checks
    expect(result.valuation_usd).toBeGreaterThan(5000000) // > $5M
    expect(result.valuation_usd).toBeLessThan(50000000)   // < $50M
    
    // Cap rate should be reasonable for industrial
    expect(result.cap_rate_pct).toBeGreaterThan(3.0)     // > 3%
    expect(result.cap_rate_pct).toBeLessThan(12.0)       // < 12%
    
    // Confidence band should be reasonable
    expect(result.confidence_band.width_pct).toBeGreaterThan(0.03)  // > 3%
    expect(result.confidence_band.width_pct).toBeLessThan(0.20)     // < 20%
    
    // Should have supporting comps
    expect(result.top_comps.length).toBeGreaterThanOrEqual(3)
    expect(result.comp_count).toBeGreaterThanOrEqual(5)
    
    // Methodology should be current
    expect(result.methodology).toBe('weighted_median_robust_v1.0')
  })

  test('IE large distribution center returns higher $/SF', async ({ request }) => {
    const response = await request.post('/api/value', {
      data: {
        market_slug: 'ie',
        noi_annual: 3500000, // $3.5M NOI
        building_sf: 500000  // 500K SF
      }
    })
    
    expect(response.ok()).toBeTruthy()
    const result = await response.json()
    
    // Large facilities should have lower $/SF but higher total value
    expect(result.price_per_sf_usd).toBeGreaterThan(40)
    expect(result.price_per_sf_usd).toBeLessThan(200)
    expect(result.valuation_usd).toBeGreaterThan(20000000) // > $20M
  })

  test('Invalid market returns 404', async ({ request }) => {
    const response = await request.post('/api/value', {
      data: {
        market_slug: 'invalid_market',
        noi_annual: 1000000,
        building_sf: 100000
      }
    })
    
    expect(response.status()).toBe(404)
    const error = await response.json()
    expect(error.error).toContain('comparable sales')
  })

  test('Missing required fields returns 400', async ({ request }) => {
    const response = await request.post('/api/value', {
      data: {
        market_slug: 'dfw'
        // Missing noi_annual and building_sf
      }
    })
    
    expect(response.status()).toBe(400)
    const error = await response.json()
    expect(error.error).toContain('Missing required fields')
  })

  test('Unreasonably small NOI is rejected', async ({ request }) => {
    const response = await request.post('/api/value', {
      data: {
        market_slug: 'dfw',
        noi_annual: 1000, // $1K NOI - too small
        building_sf: 100000
      }
    })
    
    // Should either reject or return very wide confidence bands
    if (response.ok()) {
      const result = await response.json()
      expect(result.confidence_band.status).toBe('bad')
      expect(result.confidence_band.width_pct).toBeGreaterThan(0.15) // > 15%
    } else {
      expect(response.status()).toBe(400)
    }
  })

  test('All markets return consistent structure', async ({ request }) => {
    const markets = ['dfw', 'ie', 'atl', 'phx', 'sav']
    
    for (const market of markets) {
      const response = await request.post('/api/value', {
        data: {
          market_slug: market,
          noi_annual: 800000,
          building_sf: 80000
        }
      })
      
      if (response.ok()) {
        const result = await response.json()
        
        // All successful responses must have consistent structure
        expect(result).toHaveProperty('valuation_usd')
        expect(result).toHaveProperty('confidence_interval')
        expect(result).toHaveProperty('cap_rate_pct')
        expect(result).toHaveProperty('methodology')
        expect(result).toHaveProperty('top_comps')
        expect(result).toHaveProperty('confidence_band')
        expect(result).toHaveProperty('quality_indicators')
        
        // Confidence interval should be [lower, upper]
        expect(result.confidence_interval).toHaveLength(2)
        expect(result.confidence_interval[0]).toBeLessThan(result.confidence_interval[1])
        
        // Quality indicators should be reasonable
        expect(result.quality_indicators.sample_size).toBeGreaterThan(0)
        expect(result.quality_indicators.data_freshness_months).toBeGreaterThanOrEqual(0)
        expect(result.quality_indicators.dispersion_bps).toBeGreaterThanOrEqual(0)
      }
    }
  })

  test('Confidence bands properly reflect data quality', async ({ request }) => {
    // Test that low sample size results in wider bands
    const response = await request.post('/api/value', {
      data: {
        market_slug: 'sav', // Smallest market, likely fewer comps
        noi_annual: 600000,
        building_sf: 60000
      }
    })
    
    if (response.ok()) {
      const result = await response.json()
      
      if (result.quality_indicators.sample_size < 10) {
        // Low sample size should trigger wider bands or fallback
        expect(
          result.confidence_band.width_pct > 0.08 || 
          result.quality_indicators.fallback_reason
        ).toBeTruthy()
      }
    }
  })

  test('Top comps have required audit fields', async ({ request }) => {
    const response = await request.post('/api/value', {
      data: {
        market_slug: 'dfw',
        noi_annual: 1500000,
        building_sf: 150000
      }
    })
    
    expect(response.ok()).toBeTruthy()
    const result = await response.json()
    
    // Each comp should have audit fields
    for (const comp of result.top_comps) {
      expect(comp).toHaveProperty('address_masked')
      expect(comp).toHaveProperty('sale_date')
      expect(comp).toHaveProperty('adjusted_cap_rate')
      expect(comp).toHaveProperty('weight')
      expect(comp).toHaveProperty('distance_mi')
      
      // Address should be masked but readable
      expect(comp.address_masked).toContain('***')
      
      // Weight should be between 0 and 1
      expect(comp.weight).toBeGreaterThan(0)
      expect(comp.weight).toBeLessThanOrEqual(1)
      
      // Sale date should be recent (within 5 years)
      const saleDate = new Date(comp.sale_date)
      const yearsAgo = (Date.now() - saleDate.getTime()) / (1000 * 60 * 60 * 24 * 365)
      expect(yearsAgo).toBeLessThan(5)
    }
  })

  test('Rate limiting works correctly', async ({ request }) => {
    // Make multiple rapid requests to trigger rate limiting
    const promises = Array.from({ length: 65 }, (_, i) => 
      request.post('/api/value', {
        data: {
          market_slug: 'dfw',
          noi_annual: 1000000 + i * 1000, // Vary slightly to avoid caching
          building_sf: 100000
        }
      })
    )
    
    const responses = await Promise.all(promises)
    
    // Some requests should be rate limited
    const rateLimited = responses.filter(r => r.status() === 429)
    expect(rateLimited.length).toBeGreaterThan(0)
    
    // Rate limited responses should have proper headers
    for (const response of rateLimited) {
      expect(response.headers()['x-ratelimit-reset']).toBeTruthy()
    }
  })
})

test.describe('Accuracy Monitoring API', () => {
  
  test('Accuracy endpoint returns valid metrics', async ({ request }) => {
    const response = await request.get('/api/accuracy')
    
    if (response.ok()) {
      const metrics = await response.json()
      expect(Array.isArray(metrics)).toBeTruthy()
      
      for (const metric of metrics) {
        expect(metric).toHaveProperty('market_slug')
        expect(metric).toHaveProperty('mape')
        expect(metric).toHaveProperty('rmse_bps')
        expect(metric).toHaveProperty('coverage80')
        expect(metric).toHaveProperty('sla_status')
        
        // MAPE should be reasonable
        expect(metric.mape).toBeGreaterThan(0)
        expect(metric.mape).toBeLessThan(1) // < 100%
        
        // SLA status should be valid
        expect(['pass', 'fail']).toContain(metric.sla_status)
      }
    }
  })
  
  test('Health check responds correctly', async ({ request }) => {
    const response = await request.get('/api/health')
    
    expect(response.ok()).toBeTruthy()
    const health = await response.json()
    
    expect(health).toHaveProperty('status')
    expect(health).toHaveProperty('timestamp')
    expect(health).toHaveProperty('version')
    expect(health.version).toBe('1.0.0')
  })
})
