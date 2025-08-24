/**
 * ===== CONTRACT TESTS FOR EXTERNAL APIs =====
 * Validates external API schemas and responses
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals'
import { getDataFetcher } from '../lib/data-fetcher'

// Mock the external APIs
global.fetch = jest.fn()

describe('External API Contract Tests', () => {
  let dataFetcher: any
  
  beforeEach(() => {
    jest.clearAllMocks()
    dataFetcher = getDataFetcher()
  })

  describe('FRED API Contract', () => {
    it('should handle valid FRED API response format', async () => {
      const mockFredResponse = {
        observations: [
          {
            realtime_start: "2025-08-23",
            realtime_end: "2025-08-23", 
            date: "2025-08-22",
            value: "5.33"
          }
        ]
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockFredResponse),
        status: 200,
        statusText: 'OK'
      } as Response)

      const result = await dataFetcher.getMacroData()
      
      expect(result).toMatchObject({
        data: {
          fed_funds_rate: expect.any(Number),
          treasury_10yr: expect.any(Number),
          as_of: expect.any(String),
          source: 'FRED'
        },
        provenance: {
          source: 'FRED',
          as_of: expect.any(String),
          from_cache: false,
          breaker_status: expect.any(String)
        }
      })
    })

    it('should fail gracefully on invalid FRED response', async () => {
      const mockInvalidResponse = {
        error_code: 400,
        error_message: "Bad Request"
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve(mockInvalidResponse),
        status: 400,
        statusText: 'Bad Request'
      } as Response)

      await expect(dataFetcher.getMacroData()).rejects.toThrow()
    })

    it('should validate required FRED response fields', async () => {
      const mockIncompleteResponse = {
        observations: [
          {
            date: "2025-08-22",
            // Missing 'value' field
          }
        ]
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockIncompleteResponse),
        status: 200,
        statusText: 'OK'
      } as Response)

      await expect(dataFetcher.getMacroData()).rejects.toThrow()
    })
  })

  describe('Supabase API Contract', () => {
    beforeEach(() => {
      // Mock Supabase client
      jest.mock('@supabase/supabase-js', () => ({
        createClient: jest.fn(() => ({
          from: jest.fn(() => ({
            select: jest.fn().mockReturnThis(),
            eq: jest.fn().mockReturnThis(),
            order: jest.fn().mockReturnThis(),
            limit: jest.fn().mockReturnThis(),
            single: jest.fn()
          }))
        }))
      }))
    })

    it('should validate market fundamentals schema', async () => {
      const mockSupabaseResponse = {
        data: {
          market_slug: 'dfw',
          city: 'Dallas-Fort Worth',
          vacancy_rate_pct: 6.2,
          avg_asking_rent_psf_yr_nnn: 28.50,
          yoy_rent_growth_pct: 5.4,
          under_construction_sf: 12500000,
          absorption_sf_ytd: 8200000,
          inventory_sf: 485000000,
          avg_cap_rate_pct: 7.8,
          as_of_date: '2025-08-01'
        },
        error: null
      }

      // Mock the Supabase response
      const mockSupabaseClient = {
        from: jest.fn(() => ({
          select: jest.fn().mockReturnThis(),
          eq: jest.fn().mockReturnThis(),
          order: jest.fn().mockReturnThis(),
          limit: jest.fn().mockReturnThis(),
          single: jest.fn().mockResolvedValue(mockSupabaseResponse)
        }))
      }

      // Temporarily replace the Supabase client
      ;(dataFetcher as any).supabase = mockSupabaseClient

      const result = await dataFetcher.getMarketFundamentals('dfw')

      expect(result.data).toMatchObject({
        market_slug: expect.any(String),
        city: expect.any(String),
        vacancy_rate_pct: expect.any(Number),
        avg_asking_rent_psf_yr_nnn: expect.any(Number),
        yoy_rent_growth_pct: expect.any(Number),
        avg_cap_rate_pct: expect.any(Number),
        as_of_date: expect.any(String)
      })

      // Validate numeric ranges
      expect(result.data.vacancy_rate_pct).toBeGreaterThanOrEqual(0)
      expect(result.data.vacancy_rate_pct).toBeLessThanOrEqual(40)
      expect(result.data.avg_cap_rate_pct).toBeGreaterThanOrEqual(2)
      expect(result.data.avg_cap_rate_pct).toBeLessThanOrEqual(20)
    })

    it('should validate comparables schema', async () => {
      const mockCompsResponse = {
        data: [
          {
            id: 'dfw-001',
            market_slug: 'dfw',
            address: '2100 Ross Avenue',
            building_sf: 285000,
            price_per_sf_usd: 165,
            cap_rate_pct: 7.2,
            noi_annual: 3365000,
            sale_date: '2025-07-15',
            submarket: 'CBD',
            building_class: 'A',
            year_built: 2019,
            occupancy_pct: 92.5
          }
        ],
        error: null
      }

      const mockSupabaseClient = {
        from: jest.fn(() => ({
          select: jest.fn().mockReturnThis(),
          eq: jest.fn().mockReturnThis(),
          order: jest.fn().mockReturnThis(),
          limit: jest.fn().mockResolvedValue(mockCompsResponse)
        }))
      }

      ;(dataFetcher as any).supabase = mockSupabaseClient

      const result = await dataFetcher.getComps('dfw', 10)

      expect(result.data).toBeInstanceOf(Array)
      if (result.data.length > 0) {
        const comp = result.data[0]
        expect(comp).toMatchObject({
          id: expect.any(String),
          market_slug: expect.any(String),
          address: expect.any(String),
          building_sf: expect.any(Number),
          price_per_sf_usd: expect.any(Number),
          cap_rate_pct: expect.any(Number),
          sale_date: expect.any(String)
        })

        expect(comp.building_sf).toBeGreaterThan(0)
        expect(comp.price_per_sf_usd).toBeGreaterThan(0)
        expect(comp.cap_rate_pct).toBeGreaterThanOrEqual(0)
      }
    })
  })

  describe('Circuit Breaker Contract', () => {
    it('should open circuit after threshold failures', async () => {
      // Mock consecutive failures
      for (let i = 0; i < 4; i++) {
        ;(global.fetch as jest.MockedFunction<typeof fetch>).mockRejectedValueOnce(new Error('Network error'))
        
        try {
          await dataFetcher.getMacroData()
        } catch (error) {
          // Expected to fail
        }
      }

      // Circuit should be open now
      await expect(dataFetcher.getMacroData()).rejects.toThrow(/circuit breaker/i)
    })
  })

  describe('Cache Contract', () => {
    it('should return cached data on subsequent calls', async () => {
      const mockFredResponse = {
        observations: [
          {
            date: "2025-08-22",
            value: "5.33"
          }
        ]
      }

      ;(global.fetch as jest.MockedFunction<typeof fetch>).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFredResponse),
        status: 200,
        statusText: 'OK'
      } as Response)

      // First call should hit API
      const result1 = await dataFetcher.getMacroData()
      expect(result1.provenance.from_cache).toBe(false)

      // Second call should return cached data
      const result2 = await dataFetcher.getMacroData()
      expect(result2.provenance.from_cache).toBe(true)

      // Should only have called fetch once (for DFF and GS10)
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })
  })
})
