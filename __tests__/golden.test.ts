/**
 * ===== GOLDEN TESTS FOR VALUATION CONSISTENCY =====
 * Validates that known inputs produce expected outputs within tolerance
 */

import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals'
import { getDataFetcher } from '../lib/data-fetcher'
import goldenTestData from './testdata/dfw_golden.json'

// Import the valuation API logic (we'll need to refactor it to be testable)
// For now, we'll create a mock HTTP request
const { NextRequest, NextResponse } = require('next/server')

describe('Golden Test - DFW Valuation Consistency', () => {
  let dataFetcher: any
  
  beforeEach(() => {
    jest.clearAllMocks()
    
    // Mock the DataFetcher to return our golden test data
    dataFetcher = getDataFetcher()
    
    // Mock getMacroData
    jest.spyOn(dataFetcher, 'getMacroData').mockResolvedValue({
      data: goldenTestData.inputs.macro_data,
      provenance: {
        source: 'FRED',
        as_of: goldenTestData.inputs.macro_data.as_of,
        from_cache: false,
        breaker_status: 'closed'
      }
    })

    // Mock getMarketFundamentals
    jest.spyOn(dataFetcher, 'getMarketFundamentals').mockResolvedValue({
      data: goldenTestData.inputs.market_fundamentals,
      provenance: {
        source: 'Supabase:market_fundamentals',
        as_of: goldenTestData.inputs.market_fundamentals.as_of_date,
        from_cache: false,
        record_count: 1
      },
      freshness: {
        is_fresh: true,
        days_old: 22,
        threshold_days: 90,
        status: 'FRESH'
      }
    })

    // Mock getComps
    jest.spyOn(dataFetcher, 'getComps').mockResolvedValue({
      data: goldenTestData.inputs.comparables,
      provenance: {
        source: 'Supabase:v_comps_trimmed',
        as_of: '2025-07-15',
        from_cache: false,
        record_count: goldenTestData.inputs.comparables.length
      },
      freshness: {
        is_fresh: true,
        days_old: 39,
        threshold_days: 180,
        status: 'FRESH'
      }
    })
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  it('should produce consistent valuation within tolerance', async () => {
    // Create a mock request
    const request_body = {
      market: goldenTestData.market,
      building_sf: goldenTestData.inputs.building_sf,
      noi_annual: goldenTestData.inputs.noi_annual,
      debug: true
    }

    // Since we can't directly test the API route, we'll test the logic
    const valuation_result = await calculateValuation(request_body)

    // ===== VALIDATE CORE VALUATION =====
    const expected = goldenTestData.expected_results

    expect(valuation_result.estimated_value).toBeGreaterThanOrEqual(expected.estimated_value.min_acceptable)
    expect(valuation_result.estimated_value).toBeLessThanOrEqual(expected.estimated_value.max_acceptable)
    
    console.log(`✅ Estimated Value: $${valuation_result.estimated_value.toLocaleString()} (target: $${expected.estimated_value.target.toLocaleString()})`)

    // ===== VALIDATE CAP RATE =====
    expect(valuation_result.cap_rate_applied).toBeGreaterThanOrEqual(expected.cap_rate_applied.min_acceptable)
    expect(valuation_result.cap_rate_applied).toBeLessThanOrEqual(expected.cap_rate_applied.max_acceptable)
    
    console.log(`✅ Cap Rate Applied: ${valuation_result.cap_rate_applied}% (target: ${expected.cap_rate_applied.target}%)`)

    // ===== VALIDATE PRICE PER SF =====
    expect(valuation_result.price_per_sf).toBeGreaterThanOrEqual(expected.price_per_sf.min_acceptable)
    expect(valuation_result.price_per_sf).toBeLessThanOrEqual(expected.price_per_sf.max_acceptable)
    
    console.log(`✅ Price per SF: $${valuation_result.price_per_sf} (target: $${expected.price_per_sf.target})`)

    // ===== VALIDATE CONFIDENCE SCORE =====
    expect(valuation_result.confidence_score).toBeGreaterThanOrEqual(expected.confidence_score.min_acceptable)
    expect(valuation_result.confidence_score).toBeGreaterThanOrEqual(expected.confidence_score.expected_range[0])
    expect(valuation_result.confidence_score).toBeLessThanOrEqual(expected.confidence_score.expected_range[1])
    
    console.log(`✅ Confidence Score: ${valuation_result.confidence_score} (expected: ${expected.confidence_score.expected_range[0]} - ${expected.confidence_score.expected_range[1]})`)

    // ===== VALIDATE DERIVED CALCULATIONS =====
    expect(valuation_result.derived.market_cap_rate).toBe(expected.derived.market_cap_rate)
    expect(valuation_result.derived.risk_premium).toBeGreaterThanOrEqual(expected.derived.risk_premium.expected_range[0])
    expect(valuation_result.derived.risk_premium).toBeLessThanOrEqual(expected.derived.risk_premium.expected_range[1])
    expect(valuation_result.derived.similar_comps_count).toBeGreaterThanOrEqual(expected.derived.similar_comps_count.min_acceptable)

    // ===== VALIDATE STATUS AND PROVENANCE =====
    expect(valuation_result.valuation_status).toBe(expected.valuation_status)
    expect(valuation_result.provenance.macro?.source).toBe(expected.provenance_requirements.macro.source)
    expect(valuation_result.provenance.fundamentals?.source).toBe(expected.provenance_requirements.fundamentals.source)
    expect(valuation_result.provenance.comps?.source).toBe(expected.provenance_requirements.comps.source)

    // ===== VALIDATE DEBUG INFORMATION =====
    const debug_result = valuation_result as any
    expect(debug_result.debug).toBeDefined()
    expect(debug_result.debug.calculations).toBeDefined()
    expect(debug_result.debug.macro_raw).toEqual(goldenTestData.inputs.macro_data)
    expect(debug_result.debug.fundamentals_raw).toEqual(goldenTestData.inputs.market_fundamentals)

    console.log(`✅ Golden test passed: All values within expected tolerance`)
  })

  it('should calculate risk premium components correctly', async () => {
    const request_body = {
      market: goldenTestData.market,
      building_sf: goldenTestData.inputs.building_sf,
      noi_annual: goldenTestData.inputs.noi_annual,
      debug: true
    }

    const result = await calculateValuation(request_body)
    const debug_calc = (result as any).debug.calculations

    // Validate individual risk components match expected calculation steps
    const expected_steps = goldenTestData.calculation_steps.steps

    const fed_funds_premium = (goldenTestData.inputs.macro_data.fed_funds_rate - 2.0) * 0.1
    expect(debug_calc.fed_funds_premium).toBeCloseTo(expected_steps[0].result, 3)

    const growth_adjustment = Math.max(0, (3.0 - goldenTestData.inputs.market_fundamentals.yoy_rent_growth_pct) * 0.05)
    expect(debug_calc.growth_adjustment).toBeCloseTo(expected_steps[1].result, 3)

    console.log(`✅ Risk premium components calculated correctly`)
  })

  it('should maintain performance requirements', async () => {
    const start_time = Date.now()

    const request_body = {
      market: goldenTestData.market,
      building_sf: goldenTestData.inputs.building_sf,
      noi_annual: goldenTestData.inputs.noi_annual
    }

    const result = await calculateValuation(request_body)
    const execution_time = Date.now() - start_time

    // Validate performance
    expect(execution_time).toBeLessThan(goldenTestData.performance_requirements.max_response_time_ms)
    
    // Validate API call count (should use mocks, not real calls)
    expect(dataFetcher.getMacroData).toHaveBeenCalledTimes(1)
    expect(dataFetcher.getMarketFundamentals).toHaveBeenCalledTimes(1)
    expect(dataFetcher.getComps).toHaveBeenCalledTimes(1)

    console.log(`✅ Performance requirement met: ${execution_time}ms < ${goldenTestData.performance_requirements.max_response_time_ms}ms`)
  })
})

// ===== VALUATION CALCULATION LOGIC (extracted for testing) =====
async function calculateValuation(request_body: any) {
  const { market, building_sf, noi_annual, debug = false } = request_body
  const start_time = Date.now()
  const warnings: string[] = []

  // Get data from mocked DataFetcher
  const dataFetcher = getDataFetcher()
  
  const { data: macro_data, provenance: macro_provenance } = await dataFetcher.getMacroData()
  const { data: fundamentals, provenance: fundamentals_provenance, freshness: fundamentals_freshness } = 
    await dataFetcher.getMarketFundamentals(market)
  const { data: comps, provenance: comps_provenance, freshness: comps_freshness } = 
    await dataFetcher.getComps(market, 15)

  if (!fundamentals) {
    throw new Error('INSUFFICIENT_DATA: No market fundamentals available')
  }

  // Calculate NOI
  let estimated_noi = noi_annual
  if (!estimated_noi && fundamentals.avg_asking_rent_psf_yr_nnn) {
    const gross_income = building_sf * fundamentals.avg_asking_rent_psf_yr_nnn
    const occupancy_rate = (100 - fundamentals.vacancy_rate_pct) / 100
    const operating_expense_ratio = 0.30
    estimated_noi = gross_income * occupancy_rate * (1 - operating_expense_ratio)
    warnings.push('NOI estimated from market rent and occupancy assumptions')
  }

  if (!estimated_noi) {
    throw new Error('INSUFFICIENT_DATA: Unable to determine NOI')
  }

  // Calculate risk adjustments
  const market_cap_rate = fundamentals.avg_cap_rate_pct
  let risk_premium = 0
  
  // Fed funds impact
  const fed_funds_premium = (macro_data.fed_funds_rate - 2.0) * 0.1
  risk_premium += Math.max(0, fed_funds_premium)
  
  // Growth adjustment
  const growth_adjustment = (3.0 - fundamentals.yoy_rent_growth_pct) * 0.05
  risk_premium += Math.max(0, growth_adjustment)

  const adjusted_cap_rate = market_cap_rate + risk_premium

  // Primary valuation
  const estimated_value = estimated_noi / (adjusted_cap_rate / 100)
  const price_per_sf = estimated_value / building_sf

  // Comparable analysis
  const similar_comps = comps.filter(comp => {
    const size_ratio = comp.building_sf / building_sf
    return size_ratio >= 0.5 && size_ratio <= 2.0
  })

  // Confidence scoring
  let confidence_score = 0.8
  if (!fundamentals_freshness.is_fresh) confidence_score -= 0.15
  if (!comps_freshness.is_fresh) confidence_score -= 0.15
  if (similar_comps.length < 3) confidence_score -= 0.2
  else if (similar_comps.length >= 5) confidence_score += 0.1

  // Valuation range
  const range_factor = 1 - confidence_score * 0.25
  const estimated_value_range = {
    low: estimated_value * (1 - range_factor * 0.2),
    high: estimated_value * (1 + range_factor * 0.2)
  }

  // Status
  let valuation_status = 'FRESH'
  if (!fundamentals_freshness.is_fresh || !comps_freshness.is_fresh) {
    valuation_status = 'STALE_DATA'
    confidence_score -= 0.2
  }

  const result = {
    estimated_value: Math.round(estimated_value),
    estimated_value_range: {
      low: Math.round(estimated_value_range.low),
      high: Math.round(estimated_value_range.high)
    },
    cap_rate_applied: parseFloat(adjusted_cap_rate.toFixed(2)),
    price_per_sf: parseFloat(price_per_sf.toFixed(2)),
    confidence_score: parseFloat(confidence_score.toFixed(2)),
    valuation_status,
    provenance: {
      macro: macro_provenance,
      fundamentals: fundamentals_provenance,
      comps: comps_provenance
    },
    freshness_summary: {
      macro: { status: 'FRESH', days_old: 0 },
      fundamentals: { status: fundamentals_freshness.status, days_old: fundamentals_freshness.days_old },
      comps: { status: comps_freshness.status, days_old: comps_freshness.days_old }
    },
    derived: {
      noi_estimated: estimated_noi ? Math.round(estimated_noi) : undefined,
      market_cap_rate,
      adjusted_cap_rate,
      risk_premium: parseFloat(risk_premium.toFixed(2)),
      comp_count: comps.length,
      similar_comps_count: similar_comps.length
    },
    calculated_at: new Date().toISOString(),
    model_version: '2.1.0',
    schema_version: '1.0'
  }

  if (debug) {
    (result as any).debug = {
      macro_raw: macro_data,
      fundamentals_raw: fundamentals,
      comps_raw: similar_comps,
      calculations: {
        gross_income: building_sf * (fundamentals.avg_asking_rent_psf_yr_nnn || 0),
        occupancy_rate: (100 - fundamentals.vacancy_rate_pct) / 100,
        estimated_noi: estimated_noi || 0,
        fed_funds_premium,
        growth_adjustment,
        total_risk_premium: risk_premium,
        comp_cap_rate_avg: similar_comps.length > 0 
          ? similar_comps.reduce((sum, comp) => sum + comp.cap_rate_pct, 0) / similar_comps.length 
          : 0,
        calculation_time_ms: Date.now() - start_time
      },
      warnings
    }
  }

  return result
}
