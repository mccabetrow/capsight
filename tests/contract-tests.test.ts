/**
 * ===== PRODUCTION CONTRACT TESTS =====
 * Golden tests for live data, math, and webhook integration
 */

import { test, expect } from '@jest/globals'
import { getEnvConfig } from '../lib/env-config'
import { getLiveDataFetcher } from '../lib/live-data-fetcher'
import { ValuationMathEngine } from '../lib/valuation-math'
import { getWebhookClient } from '../lib/webhook-client-production'
import type { ValuationUpsert } from '../lib/webhook-client-production'

// Golden test data - expected outputs for specific inputs
const GOLDEN_TESTS = [
  {
    name: 'dallas_office_100k_sf',
    input: { market: 'dallas', building_sf: 100000, noi_annual: 6500000 },
    expected: {
      estimated_value: { min: 80000000, max: 120000000 }, // $80-120M range
      cap_rate_applied: { min: 5.0, max: 7.5 },
      confidence_score: { min: 0.6, max: 1.0 }
    }
  },
  {
    name: 'austin_office_50k_sf',
    input: { market: 'austin', building_sf: 50000, noi_annual: 3200000 },
    expected: {
      estimated_value: { min: 40000000, max: 70000000 }, // $40-70M range
      cap_rate_applied: { min: 4.5, max: 7.0 },
      confidence_score: { min: 0.5, max: 1.0 }
    }
  }
]

describe('🏭 Production Contract Tests', () => {
  
  beforeAll(() => {
    // Ensure environment is valid
    expect(() => getEnvConfig()).not.toThrow()
  })

  describe('📊 Live Data Contracts', () => {
    
    test('macro data returns required fields', async () => {
      const dataFetcher = getLiveDataFetcher()
      const { data, provenance, freshness } = await dataFetcher.getMacroData()
      
      expect(data).toBeDefined()
      expect(data.fed_funds_rate).toBeTypeOf('number')
      expect(data.ten_year_treasury).toBeTypeOf('number')
      expect(data.cpi_yoy_pct).toBeTypeOf('number')
      
      expect(provenance.source).toBe('FRED')
      expect(provenance.from_cache).toBeTypeOf('boolean')
      
      expect(freshness.is_fresh).toBeTypeOf('boolean')
      expect(freshness.days_old).toBeGreaterThanOrEqual(0)
    })
    
    test('market fundamentals return required fields', async () => {
      const dataFetcher = getLiveDataFetcher()
      const { data, provenance, freshness } = await dataFetcher.getMarketFundamentals('dallas')
      
      expect(data).toBeDefined()
      expect(data.avg_cap_rate_pct).toBeTypeOf('number')
      expect(data.avg_asking_rent_psf_yr_nnn).toBeTypeOf('number')
      expect(data.vacancy_rate_pct).toBeTypeOf('number')
      expect(data.rent_growth_yoy_pct).toBeTypeOf('number')
      
      expect(provenance.source).toBe('Supabase')
      
      expect(freshness.is_fresh).toBeTypeOf('boolean')
      expect(freshness.days_old).toBeGreaterThanOrEqual(0)
    })
    
    test('comparable sales return valid structure', async () => {
      const dataFetcher = getLiveDataFetcher()
      const { data, provenance, freshness } = await dataFetcher.getComparableSales('dallas', 10)
      
      expect(Array.isArray(data)).toBe(true)
      
      if (data && data.length > 0) {
        const firstComp = data[0]
        expect(firstComp.sale_price).toBeTypeOf('number')
        expect(firstComp.price_per_sf).toBeTypeOf('number')
        expect(firstComp.building_sf).toBeTypeOf('number')
        expect(firstComp.cap_rate_implied).toBeTypeOf('number')
      }
      
      expect(provenance.source).toBe('Supabase')
      
      expect(freshness.is_fresh).toBeTypeOf('boolean')
      expect(freshness.days_old).toBeGreaterThanOrEqual(0)
    })
  })

  describe('🧮 Math Engine Contracts', () => {
    
    test('current value calculation is consistent', () => {
      const noi = 5000000 // $5M NOI
      const capRate = 0.06 // 6% cap rate
      
      const value = ValuationMathEngine.calculateCurrentValue(noi, capRate)
      
      expect(value).toBeCloseTo(83333333, -4) // $83.33M with tolerance
      expect(value).toBeGreaterThan(0)
      expect(value).toBeLessThan(1000000000) // Sanity check: < $1B
    })
    
    test('future NOI calculation follows growth model', () => {
      const currentNOI = 5000000
      const growthRate = 2.5 // 2.5% annual
      const yearsForward = 1
      
      const futureNOI = ValuationMathEngine.calculateFutureNOI(currentNOI, growthRate, yearsForward)
      
      expect(futureNOI).toBeCloseTo(5125000, -2) // $5.125M
      expect(futureNOI).toBeGreaterThan(currentNOI)
    })
    
    test('confidence scoring returns valid range', () => {
      const factors = {
        comp_count: 8,
        macro_freshness_days: 1,
        fundamentals_freshness_days: 7,
        comps_freshness_days: 14,
        dual_engine_disagreement_pct: 10,
        cap_rate_variance_from_market: 0.5
      }
      
      const confidence = ValuationMathEngine.calculateConfidence(factors)
      
      expect(confidence).toBeGreaterThanOrEqual(0)
      expect(confidence).toBeLessThanOrEqual(1)
    })
    
    test('dual engine check handles disagreement', () => {
      const incomeValue = 100000000 // $100M
      const comps = [
        { sale_price: 110000000, building_sf: 100000, price_per_sf: 1100, cap_rate_implied: 5.5 },
        { sale_price: 120000000, building_sf: 110000, price_per_sf: 1091, cap_rate_implied: 5.3 }
      ]
      const buildingSf = 100000
      
      const result = ValuationMathEngine.performDualEngineCheck(incomeValue, comps, buildingSf)
      
      expect(result.recommended_value).toBeGreaterThan(0)
      expect(result.disagreement_pct).toBeGreaterThanOrEqual(0)
      expect(result.sales_comp_value).toBeGreaterThan(0)
      
      if (result.disagreement_pct > 15) {
        expect(result.warning).toBe('engine_disagreement')
      }
    })
  })

  describe('🎯 Golden Test Suite', () => {
    
    test.each(GOLDEN_TESTS)('golden test: $name', async ({ input, expected }) => {
      // Skip if no live environment
      if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
        console.log('⏭️ Skipping golden test (no live environment)')
        return
      }
      
      // Mock API call
      const response = await fetch('http://localhost:3000/api/v2/valuation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input)
      })
      
      expect(response.status).toBe(200)
      const result = await response.json()
      
      // Validate core fields exist
      expect(result.estimated_value).toBeTypeOf('number')
      expect(result.cap_rate_applied).toBeTypeOf('number')
      expect(result.confidence_score).toBeTypeOf('number')
      expect(result.valuation_status).toMatch(/FRESH|STALE_DATA|INSUFFICIENT_DATA/)
      
      // Validate against golden ranges
      expect(result.estimated_value).toBeGreaterThanOrEqual(expected.estimated_value.min)
      expect(result.estimated_value).toBeLessThanOrEqual(expected.estimated_value.max)
      
      expect(result.cap_rate_applied).toBeGreaterThanOrEqual(expected.cap_rate_applied.min)
      expect(result.cap_rate_applied).toBeLessThanOrEqual(expected.cap_rate_applied.max)
      
      expect(result.confidence_score).toBeGreaterThanOrEqual(expected.confidence_score.min)
      expect(result.confidence_score).toBeLessThanOrEqual(expected.confidence_score.max)
    }, 30000) // 30s timeout for live API
  })

  describe('🔗 Webhook Transport Contracts', () => {
    
    test('webhook client validates schema', async () => {
      const webhookClient = getWebhookClient()
      
      const validPayload: ValuationUpsert = {
        schema_version: '1.0',
        type: 'valuation.upsert',
        tenant_id: 'test-tenant',
        as_of: new Date().toISOString().split('T')[0],
        model: { name: 'valuation-blend', version: '1.0.0' },
        provenance: {
          macro: { source: 'FRED', as_of: '2024-01-15', from_cache: false },
          fundamentals: { source: 'Supabase', as_of: '2024-01-14' },
          comps: { source: 'Supabase', as_of: '2024-01-13' }
        },
        address: '100 Main St, Dallas, TX',
        geo: { lat: 32.7767, lon: -96.7970, market: 'DALLAS', submarket: 'CBD' },
        property_snapshot: { building_sf: 100000, year_built: 2020 },
        inputs: {
          asset_type: 'office',
          rent_psf_yr: 28,
          opex_psf_yr: 12,
          vacancy_pct: 0.08,
          cap_rate_now_pct: 6.2,
          cap_rate_qoq_delta_bps: -15
        },
        current_value: { point: 100000000, low: 85000000, high: 115000000, confidence: 0.82 },
        forecast_12m: { point: 105000000, low: 88000000, high: 122000000, confidence: 0.75 },
        drivers: ['Market cap rate: 6.20%', 'Strong rent growth: 3.2%']
      }
      
      // This would normally send to n8n, but we'll test validation only
      expect(() => webhookClient.validatePayload(validPayload)).not.toThrow()
    })
    
    test('webhook client rejects invalid schema', async () => {
      const webhookClient = getWebhookClient()
      
      const invalidPayload = {
        schema_version: '1.0',
        // Missing required 'type' field
        tenant_id: 'test-tenant'
      } as any
      
      expect(() => webhookClient.validatePayload(invalidPayload)).toThrow()
    })
    
    test('webhook client generates correct HMAC signature', () => {
      const webhookClient = getWebhookClient()
      
      const payload = { test: 'data' }
      const requestId = 'test-request-123'
      
      const signature = webhookClient.generateSignature(JSON.stringify(payload), requestId)
      
      expect(signature).toMatch(/^sha256=/)
      expect(signature.length).toBeGreaterThan(10)
    })
  })

  describe('⚡ Performance Contracts', () => {
    
    test('valuation API responds within SLA', async () => {
      if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
        console.log('⏭️ Skipping performance test (no live environment)')
        return
      }
      
      const startTime = Date.now()
      
      const response = await fetch('http://localhost:3000/api/v2/valuation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          market: 'dallas', 
          building_sf: 100000, 
          noi_annual: 6000000 
        })
      })
      
      const endTime = Date.now()
      const duration = endTime - startTime
      
      expect(response.status).toBe(200)
      expect(duration).toBeLessThan(5000) // < 5s SLA
      
      const result = await response.json()
      expect(result.calculation_time_ms).toBeLessThan(5000)
    }, 10000)
    
    test('health endpoint responds quickly', async () => {
      const startTime = Date.now()
      
      const response = await fetch('http://localhost:3000/api/health/data-v2')
      
      const endTime = Date.now()
      const duration = endTime - startTime
      
      expect(response.status).toMatch(/200|503/) // OK or Service Unavailable
      expect(duration).toBeLessThan(2000) // < 2s for health check
    })
  })
})
