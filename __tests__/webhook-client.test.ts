/**
 * ===== WEBHOOK CLIENT CONTRACT TESTS =====
 * Validates webhook client behavior, payload generation, and N8N integration
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals'
import { N8NWebhookClient, createValuationPayload, createInsufficientEvidencePayload, getWebhookClient } from '../lib/webhook-client'

// Mock fetch globally
const mockFetch = jest.fn()
global.fetch = mockFetch as any

// Mock environment variables
process.env.N8N_INGEST_URL = 'https://test.n8n.cloud/webhook/test'
process.env.WEBHOOK_SECRET = 'test-secret-key'
process.env.CAPSIGHT_TENANT_ID = 'test-tenant'

describe('N8N Webhook Client', () => {
  let client: N8NWebhookClient

  beforeEach(() => {
    jest.clearAllMocks()
    client = new N8NWebhookClient()
  })

  describe('Payload Validation', () => {
    it('validates valuation payload schema correctly', async () => {
      const validPayload = createValuationPayload({
        address: '123 Test St',
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Downtown',
        building_sf: 50000,
        year_built: 2020,
        asset_type: 'office',
        rent_psf_yr: 28.5,
        opex_psf_yr: 8.5,
        vacancy_pct: 0.08,
        cap_rate_now_pct: 6.5,
        cap_rate_qoq_delta_bps: -25,
        current_value: {
          point: 21500000,
          low: 19350000,
          high: 23650000,
          confidence: 0.78
        },
        forecast_12m: {
          point: 22575000,
          low: 20318000,
          high: 24833000,
          confidence: 0.65
        },
        drivers: ['Market cap rate: 6.25%'],
        provenance: {
          macro: {
            source: 'FRED',
            as_of: '2024-01-15T10:00:00Z',
            from_cache: false
          },
          fundamentals: {
            source: 'supabase',
            as_of: '2024-01-10T00:00:00Z'
          },
          comps: {
            source: 'supabase',
            as_of: '2024-01-12T00:00:00Z'
          }
        }
      })

      // Mock successful response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Map()
      } as Response)

      const result = await client.send(validPayload)

      expect(result.success).toBe(true)
      expect(result.attempts).toBe(1)
      expect(mockFetch).toHaveBeenCalledTimes(1)
      
      const [url, options] = mockFetch.mock.calls[0]
      expect(url).toBe('https://test.n8n.cloud/webhook/test')
      expect(options.method).toBe('POST')
      expect(options.headers['Content-Type']).toBe('application/json')
      expect(options.headers['X-Capsight-Tenant']).toBe('test-tenant')
      expect(options.headers['X-Capsight-Signature']).toMatch(/^sha256=/)
    })

    it('validates insufficient evidence payload correctly', async () => {
      const insufficientPayload = createInsufficientEvidencePayload({
        address: '456 Test Ave',
        reason: ['stale_fundamentals', 'low_comp_count'],
        details: {
          comp_count: 1,
          fundamentals_as_of: '2023-12-01T00:00:00Z'
        },
        provenance: {
          macro: {
            source: 'FRED',
            as_of: '2024-01-15T10:00:00Z',
            from_cache: false
          },
          fundamentals: {
            source: 'supabase',
            as_of: '2023-12-01T00:00:00Z'
          },
          comps: {
            source: 'supabase',
            as_of: '2024-01-12T00:00:00Z'
          }
        }
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Map()
      } as Response)

      const result = await client.send(insufficientPayload)

      expect(result.success).toBe(true)
      expect(result.attempts).toBe(1)
      
      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body.type).toBe('valuation.insufficient')
      expect(body.reason).toEqual(['stale_fundamentals', 'low_comp_count'])
    })

    it('rejects invalid payload data', async () => {
      const invalidPayload = {
        schema_version: '1.0',
        type: 'valuation.upsert',
        tenant_id: 'test',
        as_of: '2024-01-15',
        model: { name: 'test', version: 'invalid-version' }, // Invalid semver
        provenance: {
          macro: { source: 'test', as_of: '2024-01-15T10:00:00Z', from_cache: false },
          fundamentals: { source: 'test', as_of: '2024-01-15T10:00:00Z' },
          comps: { source: 'test', as_of: '2024-01-15T10:00:00Z' }
        },
        address: '123 Test',
        inputs: {
          vacancy_pct: -0.5 // Invalid negative vacancy
        }
      } as any

      const result = await client.send(invalidPayload)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Validation failed')
      expect(mockFetch).not.toHaveBeenCalled()
    })
  })

  describe('HMAC Signature', () => {
    it('generates correct HMAC signature', async () => {
      const payload = createValuationPayload({
        address: '789 Signature Test',
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Downtown',
        building_sf: 25000,
        year_built: 2015,
        asset_type: 'retail',
        rent_psf_yr: 22.0,
        opex_psf_yr: 6.6,
        vacancy_pct: 0.12,
        cap_rate_now_pct: 7.2,
        cap_rate_qoq_delta_bps: 10,
        current_value: { point: 10000000, low: 9000000, high: 11000000, confidence: 0.7 },
        forecast_12m: { point: 10500000, low: 9450000, high: 11550000, confidence: 0.6 },
        drivers: ['Test driver'],
        provenance: {
          macro: { source: 'test', as_of: '2024-01-15T10:00:00Z', from_cache: false },
          fundamentals: { source: 'test', as_of: '2024-01-15T10:00:00Z' },
          comps: { source: 'test', as_of: '2024-01-15T10:00:00Z' }
        }
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Map()
      } as Response)

      await client.send(payload)

      const [, options] = mockFetch.mock.calls[0]
      const signature = options.headers['X-Capsight-Signature']
      
      expect(signature).toMatch(/^sha256=[a-f0-9]{64}$/)
      
      // Verify signature is consistent
      await client.send(payload)
      const signature2 = mockFetch.mock.calls[1][1].headers['X-Capsight-Signature']
      
      expect(signature).toBe(signature2) // Same payload = same signature
    })
  })

  describe('Retry Logic', () => {
    it('retries on 5xx server errors with exponential backoff', async () => {
      const payload = createValuationPayload({
        address: 'Retry Test',
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Test',
        building_sf: 30000,
        year_built: 2018,
        asset_type: 'industrial',
        rent_psf_yr: 15.0,
        opex_psf_yr: 4.5,
        vacancy_pct: 0.05,
        cap_rate_now_pct: 8.0,
        cap_rate_qoq_delta_bps: 0,
        current_value: { point: 5000000, low: 4500000, high: 5500000, confidence: 0.8 },
        forecast_12m: { point: 5250000, low: 4725000, high: 5775000, confidence: 0.7 },
        drivers: ['Retry test'],
        provenance: {
          macro: { source: 'test', as_of: '2024-01-15T10:00:00Z', from_cache: false },
          fundamentals: { source: 'test', as_of: '2024-01-15T10:00:00Z' },
          comps: { source: 'test', as_of: '2024-01-15T10:00:00Z' }
        }
      })

      // Mock 3 server errors, then success
      mockFetch
        .mockResolvedValueOnce({ ok: false, status: 500, statusText: 'Internal Server Error', headers: new Map() } as Response)
        .mockResolvedValueOnce({ ok: false, status: 502, statusText: 'Bad Gateway', headers: new Map() } as Response)
        .mockResolvedValueOnce({ ok: false, status: 503, statusText: 'Service Unavailable', headers: new Map() } as Response)
        .mockResolvedValueOnce({ ok: true, status: 200, headers: new Map() } as Response)

      const startTime = Date.now()
      const result = await client.send(payload)
      const duration = Date.now() - startTime

      expect(result.success).toBe(true)
      expect(result.attempts).toBe(4)
      expect(mockFetch).toHaveBeenCalledTimes(4)
      expect(duration).toBeGreaterThan(500) // Should have backoff delays
    }, 10000) // 10s timeout for backoff

    it('does not retry on 4xx client errors', async () => {
      const payload = createValuationPayload({
        address: 'Client Error Test',
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Test',
        building_sf: 20000,
        year_built: 2019,
        asset_type: 'multifamily',
        rent_psf_yr: 18.0,
        opex_psf_yr: 5.4,
        vacancy_pct: 0.03,
        cap_rate_now_pct: 5.5,
        cap_rate_qoq_delta_bps: -10,
        current_value: { point: 8000000, low: 7200000, high: 8800000, confidence: 0.85 },
        forecast_12m: { point: 8400000, low: 7560000, high: 9240000, confidence: 0.75 },
        drivers: ['Client error test'],
        provenance: {
          macro: { source: 'test', as_of: '2024-01-15T10:00:00Z', from_cache: false },
          fundamentals: { source: 'test', as_of: '2024-01-15T10:00:00Z' },
          comps: { source: 'test', as_of: '2024-01-15T10:00:00Z' }
        }
      })

      mockFetch.mockResolvedValueOnce({ 
        ok: false, 
        status: 400, 
        statusText: 'Bad Request',
        text: () => Promise.resolve('Invalid payload'),
        headers: new Map() 
      } as Response)

      const result = await client.send(payload)

      expect(result.success).toBe(false)
      expect(result.attempts).toBe(1) // Should not retry
      expect(result.finalStatusCode).toBe(400)
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('Circuit Breaker', () => {
    it('opens circuit breaker after repeated failures', async () => {
      const payload = createValuationPayload({
        address: 'Circuit Breaker Test',
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Test',
        building_sf: 40000,
        year_built: 2017,
        asset_type: 'office',
        rent_psf_yr: 32.0,
        opex_psf_yr: 9.6,
        vacancy_pct: 0.10,
        cap_rate_now_pct: 6.8,
        cap_rate_qoq_delta_bps: 5,
        current_value: { point: 12000000, low: 10800000, high: 13200000, confidence: 0.72 },
        forecast_12m: { point: 12600000, low: 11340000, high: 13860000, confidence: 0.62 },
        drivers: ['Circuit breaker test'],
        provenance: {
          macro: { source: 'test', as_of: '2024-01-15T10:00:00Z', from_cache: false },
          fundamentals: { source: 'test', as_of: '2024-01-15T10:00:00Z' },
          comps: { source: 'test', as_of: '2024-01-15T10:00:00Z' }
        }
      })

      // Mock repeated 500 errors to trigger circuit breaker
      mockFetch.mockResolvedValue({ 
        ok: false, 
        status: 500, 
        statusText: 'Internal Server Error',
        headers: new Map() 
      } as Response)

      // First few calls should attempt with retries
      const result1 = await client.send(payload)
      const result2 = await client.send(payload)
      const result3 = await client.send(payload)

      expect(result1.success).toBe(false)
      expect(result2.success).toBe(false)
      expect(result3.success).toBe(false)

      // After circuit breaker threshold, should fail immediately
      const result4 = await client.send(payload)
      
      expect(result4.success).toBe(false)
      expect(result4.error).toContain('Circuit breaker open')
      expect(result4.attempts).toBe(0)

      // Check metrics
      const metrics = client.getMetrics()
      expect(metrics.circuit_breaker.state).toBe('OPEN')
    }, 15000)
  })

  describe('Data Freshness Adjustments', () => {
    it('adjusts confidence for stale data', async () => {
      const stalePayload = createValuationPayload({
        address: 'Stale Data Test',
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Test',
        building_sf: 35000,
        year_built: 2016,
        asset_type: 'retail',
        rent_psf_yr: 24.0,
        opex_psf_yr: 7.2,
        vacancy_pct: 0.15,
        cap_rate_now_pct: 7.5,
        cap_rate_qoq_delta_bps: 20,
        current_value: { point: 9000000, low: 8100000, high: 9900000, confidence: 0.8 },
        forecast_12m: { point: 9450000, low: 8505000, high: 10395000, confidence: 0.7 },
        drivers: ['Stale data test'],
        provenance: {
          macro: { 
            source: 'FRED', 
            as_of: '2023-12-01T10:00:00Z', // Very stale macro data
            from_cache: false 
          },
          fundamentals: { 
            source: 'supabase', 
            as_of: '2023-10-01T00:00:00Z' // Very stale fundamentals
          },
          comps: { 
            source: 'supabase', 
            as_of: '2023-09-01T00:00:00Z' // Very stale comps
          }
        }
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Map()
      } as Response)

      const result = await client.send(stalePayload)

      expect(result.success).toBe(true)
      
      // Check that payload was adjusted for staleness
      const sentPayload = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(sentPayload.status).toBe('STALE_DATA')
      expect(sentPayload.current_value.confidence).toBeLessThan(0.8) // Should be reduced
    })
  })

  describe('Singleton Pattern', () => {
    it('returns same instance from getWebhookClient', () => {
      const client1 = getWebhookClient()
      const client2 = getWebhookClient()
      
      expect(client1).toBe(client2)
    })
  })

  describe('Metrics Collection', () => {
    it('collects and reports metrics correctly', async () => {
      const payload = createValuationPayload({
        address: 'Metrics Test',
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Test',
        building_sf: 45000,
        year_built: 2021,
        asset_type: 'mixed-use',
        rent_psf_yr: 30.0,
        opex_psf_yr: 9.0,
        vacancy_pct: 0.07,
        cap_rate_now_pct: 6.2,
        cap_rate_qoq_delta_bps: -5,
        current_value: { point: 15000000, low: 13500000, high: 16500000, confidence: 0.82 },
        forecast_12m: { point: 15750000, low: 14175000, high: 17325000, confidence: 0.72 },
        drivers: ['Metrics test'],
        provenance: {
          macro: { source: 'test', as_of: '2024-01-15T10:00:00Z', from_cache: false },
          fundamentals: { source: 'test', as_of: '2024-01-15T10:00:00Z' },
          comps: { source: 'test', as_of: '2024-01-15T10:00:00Z' }
        }
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Map()
      } as Response)

      await client.send(payload)
      
      const metrics = client.getMetrics()
      
      expect(metrics.total_requests).toBeGreaterThan(0)
      expect(metrics.webhook_success_ratio).toBeGreaterThan(0)
      expect(typeof metrics.webhook_post_latency_ms_p50).toBe('number')
      expect(typeof metrics.webhook_post_latency_ms_p95).toBe('number')
    })
  })
})
