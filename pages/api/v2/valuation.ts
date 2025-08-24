/**
 * ===== PRODUCTION VALUATION API V2 =====
 * Live data, correct math, webhook emission with full observability
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { randomUUID } from 'crypto'
import { getEnvConfig } from '../../../lib/env-config'
import { getLiveDataFetcher } from '../../../lib/live-data-fetcher'
import { ValuationMathEngine } from '../../../lib/valuation-math'
import { getWebhookClient, type ValuationUpsert, type ValuationInsufficient } from '../../../lib/webhook-client-production'

interface ValuationRequest {
  market: string
  building_sf: number
  noi_annual?: number
  debug?: boolean
}

interface ValuationResponse {
  // Core valuation
  estimated_value: number
  estimated_value_range: {
    low: number
    high: number
  }
  cap_rate_applied: number
  cap_rate_forecast_12m: number
  price_per_sf: number
  
  // Forecast
  forecast_12m: {
    point: number
    low: number
    high: number
    confidence: number
  }
  
  // Confidence and status
  confidence_score: number
  valuation_status: 'FRESH' | 'STALE_DATA' | 'INSUFFICIENT_DATA'
  
  // Data sources and freshness  
  provenance: {
    macro: {
      source: string
      as_of: string
      from_cache: boolean
    }
    fundamentals: {
      source: string
      as_of: string
    }
    comps: {
      source: string
      as_of: string
    }
  }
  
  freshness_summary: {
    macro: { status: string, days_old: number }
    fundamentals: { status: string, days_old: number }
    comps: { status: string, days_old: number }
  }
  
  // Derived calculations
  derived: {
    noi_current: number
    noi_future_12m: number
    comp_count: number
    dual_engine_disagreement_pct?: number
    model_version: string
  }
  
  // Drivers explanation
  drivers: string[]
  
  // Metadata
  calculated_at: string
  calculation_time_ms: number
  request_id: string
  
  // Debug info (if requested)
  debug?: {
    macro_raw: any
    fundamentals_raw: any
    comps_raw: any[]
    math_breakdown: any
    webhook_result?: any
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ValuationResponse | { error: string; request_id: string; calculation_time_ms?: number }>
) {
  const start_time = Date.now()
  const requestId = randomUUID()
  
  // Validate environment on first use
  try {
    getEnvConfig()
  } catch (error) {
    console.error('❌ Environment validation failed:', error)
    return res.status(500).json({
      error: 'Server configuration error',
      request_id: requestId,
      calculation_time_ms: Date.now() - start_time
    })
  }
  
  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ 
      error: 'Method not allowed',
      request_id: requestId
    })
  }
  
  try {
    console.log(`🚀 Valuation request started [${requestId}]`)
    
    const { market, building_sf, noi_annual, debug }: ValuationRequest = req.body
    
    // Basic validation
    if (!market || !building_sf) {
      return res.status(400).json({ 
        error: 'Missing required fields: market, building_sf',
        request_id: requestId,
        calculation_time_ms: Date.now() - start_time
      })
    }
    
    if (building_sf < 1000 || building_sf > 10000000) {
      return res.status(400).json({
        error: 'building_sf must be between 1,000 and 10,000,000',
        request_id: requestId,
        calculation_time_ms: Date.now() - start_time
      })
    }
    
    console.log(`📊 Processing [${requestId}]: ${market}, ${building_sf} SF${noi_annual ? `, NOI $${noi_annual}` : ''}`)
    
    // ===== FETCH LIVE DATA =====
    const dataFetcher = getLiveDataFetcher()
    
    // 1. Macro data
    const { data: macroData, provenance: macroProvenance, freshness: macroFreshness } = 
      await dataFetcher.getMacroData()
    
    if (!macroData) {
      console.error(`❌ No macro data available [${requestId}]`)
      return res.status(422).json({
        error: 'INSUFFICIENT_DATA: No macro data available',
        request_id: requestId,
        calculation_time_ms: Date.now() - start_time
      })
    }
    
    // 2. Market fundamentals
    const { data: fundamentals, provenance: fundamentalsProvenance, freshness: fundamentalsFreshness } = 
      await dataFetcher.getMarketFundamentals(market)
    
    if (!fundamentals) {
      console.warn(`⚠️ No market fundamentals for ${market} [${requestId}]`)
      
      // Emit insufficient data webhook
      await emitInsufficientDataWebhook(requestId, {
        reason: ['no_macro_data'],
        details: { comp_count: 0 },
        macro: macroProvenance,
        fundamentals: { source: 'none', as_of: new Date().toISOString().split('T')[0] },
        comps: { source: 'none', as_of: new Date().toISOString().split('T')[0] }
      })
      
      return res.status(422).json({
        error: 'INSUFFICIENT_DATA: No market fundamentals available for this market',
        request_id: requestId,
        calculation_time_ms: Date.now() - start_time
      })
    }
    
    // 3. Comparable sales
    const { data: comps, provenance: compsProvenance, freshness: compsFreshness } = 
      await dataFetcher.getComparableSales(market, 15)
    
    const compCount = comps?.length || 0
    
    // ===== PERFORM CALCULATIONS =====
    console.log(`🧮 Calculating valuation [${requestId}]...`)
    
    // Determine NOI
    let currentNOI = noi_annual
    if (!currentNOI && fundamentals) {
      // Estimate from market data
      currentNOI = ValuationMathEngine.calculateNOI(
        building_sf,
        fundamentals.avg_asking_rent_psf_yr_nnn,
        fundamentals.avg_asking_rent_psf_yr_nnn * 0.30, // 30% opex estimate
        fundamentals.vacancy_rate_pct / 100
      )
    }
    
    if (!currentNOI || currentNOI <= 0) {
      await emitInsufficientDataWebhook(requestId, {
        reason: ['invalid_inputs'],
        details: { comp_count: compCount },
        macro: macroProvenance,
        fundamentals: fundamentalsProvenance,
        comps: compsProvenance
      })
      
      return res.status(422).json({
        error: 'INSUFFICIENT_DATA: Cannot determine NOI for valuation',
        request_id: requestId,
        calculation_time_ms: Date.now() - start_time
      })
    }
    
    // Cap rate analysis
    let capRateNow = fundamentals.avg_cap_rate_pct
    
    // Risk adjustments based on macro conditions
    const fedFundsPremium = Math.max(0, (macroData.fed_funds_rate - 2.0) * 0.1)
    const spreadRisk = Math.max(0, (macroData.ten_year_treasury - macroData.fed_funds_rate - 2.0) * 0.05)
    
    capRateNow += fedFundsPremium + spreadRisk
    
    // Calculate current value using income approach
    const currentValue = ValuationMathEngine.calculateCurrentValue(currentNOI, capRateNow)
    
    // Forecast calculations
    const rentGrowthAnn = fundamentals.rent_growth_yoy_pct || 2.5 // Default 2.5% if missing
    const futureNOI = ValuationMathEngine.calculateFutureNOI(currentNOI, rentGrowthAnn, 1.0)
    
    // Simple cap rate forecast (can be enhanced with the multi-factor model later)
    const capRateForecast = capRateNow - 0.1 // Assume 10bps compression over 12m
    const futureValue = ValuationMathEngine.calculateFutureValue(futureNOI, capRateForecast)
    
    // Dual-engine check with comps
    const dualEngineResult = ValuationMathEngine.performDualEngineCheck(
      currentValue,
      comps || [],
      building_sf
    )
    
    // Confidence calculation
    const confidenceScore = ValuationMathEngine.calculateConfidence({
      comp_count: compCount,
      macro_freshness_days: macroFreshness.days_old,
      fundamentals_freshness_days: fundamentalsFreshness.days_old,
      comps_freshness_days: compsFreshness.days_old,
      dual_engine_disagreement_pct: dualEngineResult.disagreement_pct,
      cap_rate_variance_from_market: 0 // Will calculate if have comp cap rates
    })
    
    // Valuation ranges
    const currentRange = ValuationMathEngine.calculateValuationRange(dualEngineResult.recommended_value, confidenceScore)
    const forecastRange = ValuationMathEngine.calculateValuationRange(futureValue, Math.max(0.3, confidenceScore - 0.15))
    
    // Determine overall status
    let valuationStatus: ValuationResponse['valuation_status'] = 'FRESH'
    if (!macroFreshness.is_fresh || !fundamentalsFreshness.is_fresh || !compsFreshness.is_fresh) {
      valuationStatus = 'STALE_DATA'
    }
    if (compCount < 2 || confidenceScore < 0.4) {
      valuationStatus = 'INSUFFICIENT_DATA'
    }
    
    // Build drivers explanation
    const drivers = [
      `Market cap rate: ${fundamentals.avg_cap_rate_pct.toFixed(2)}%`,
      `Fed funds adjustment: +${(fedFundsPremium * 100).toFixed(0)}bps`,
      `Treasury spread adjustment: +${(spreadRisk * 100).toFixed(0)}bps`,
      `${compCount} comparable sales`,
      `NOI: $${Math.round(currentNOI).toLocaleString()}`,
      `Rent growth: ${rentGrowthAnn.toFixed(1)}% annually`
    ]
    
    if (dualEngineResult.warning === 'engine_disagreement') {
      drivers.push(`⚠️ Income vs Sales disagreement: ${dualEngineResult.disagreement_pct.toFixed(1)}%`)
    }
    
    // Build response
    const response: ValuationResponse = {
      estimated_value: Math.round(dualEngineResult.recommended_value),
      estimated_value_range: currentRange,
      cap_rate_applied: Math.round(capRateNow * 100) / 100,
      cap_rate_forecast_12m: Math.round(capRateForecast * 100) / 100,
      price_per_sf: Math.round(dualEngineResult.recommended_value / building_sf),
      
      forecast_12m: {
        point: Math.round(futureValue),
        low: forecastRange.low,
        high: forecastRange.high,
        confidence: Math.max(0.3, confidenceScore - 0.15)
      },
      
      confidence_score: Math.round(confidenceScore * 100) / 100,
      valuation_status: valuationStatus,
      
      provenance: {
        macro: macroProvenance,
        fundamentals: fundamentalsProvenance,
        comps: compsProvenance
      },
      
      freshness_summary: {
        macro: { 
          status: macroFreshness.is_fresh ? 'FRESH' : 'STALE', 
          days_old: macroFreshness.days_old 
        },
        fundamentals: { 
          status: fundamentalsFreshness.is_fresh ? 'FRESH' : 'STALE', 
          days_old: fundamentalsFreshness.days_old 
        },
        comps: { 
          status: compsFreshness.is_fresh ? 'FRESH' : 'STALE', 
          days_old: compsFreshness.days_old 
        }
      },
      
      derived: {
        noi_current: Math.round(currentNOI),
        noi_future_12m: Math.round(futureNOI),
        comp_count: compCount,
        dual_engine_disagreement_pct: dualEngineResult.disagreement_pct,
        model_version: ValuationMathEngine.getModelMetadata().version
      },
      
      drivers,
      
      calculated_at: new Date().toISOString(),
      calculation_time_ms: Date.now() - start_time,
      request_id: requestId
    }
    
    // ===== EMIT WEBHOOK =====
    let webhookResult
    try {
      webhookResult = await emitValuationWebhook(requestId, response, {
        building_sf,
        market,
        asset_type: 'office', // Default to office, should be determined from inputs
        rent_psf_yr: fundamentals.avg_asking_rent_psf_yr_nnn,
        opex_psf_yr: fundamentals.avg_asking_rent_psf_yr_nnn * 0.30,
        vacancy_pct: fundamentals.vacancy_rate_pct / 100,
        cap_rate_now_pct: capRateNow,
        cap_rate_qoq_delta_bps: 0 // Would need historical data
      })
    } catch (webhookError) {
      console.error(`❌ Webhook failed [${requestId}]:`, webhookError)
      // Don't fail the API response for webhook errors
    }
    
    // Add debug info if requested
    if (debug) {
      response.debug = {
        macro_raw: macroData,
        fundamentals_raw: fundamentals,
        comps_raw: comps || [],
        math_breakdown: {
          current_noi: currentNOI,
          fed_funds_premium: fedFundsPremium,
          spread_risk: spreadRisk,
          adjusted_cap_rate: capRateNow,
          income_approach_value: currentValue,
          sales_comp_value: dualEngineResult.sales_comp_value,
          recommended_value: dualEngineResult.recommended_value
        },
        webhook_result: webhookResult
      }
    }
    
    console.log(`✅ Valuation complete [${requestId}]: $${response.estimated_value.toLocaleString()} (${response.confidence_score} confidence)`)
    
    res.setHeader('Cache-Control', 'no-cache, must-revalidate')
    res.setHeader('X-Calculation-Time', `${response.calculation_time_ms}ms`)
    res.setHeader('X-Request-Id', requestId)
    
    return res.status(200).json(response)
    
  } catch (error) {
    console.error(`❌ Valuation API error [${requestId}]:`, error)
    
    return res.status(500).json({ 
      error: `Valuation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      request_id: requestId,
      calculation_time_ms: Date.now() - start_time
    })
  }
}

// ===== HELPER FUNCTIONS =====

async function emitValuationWebhook(
  requestId: string, 
  response: ValuationResponse,
  inputs: {
    building_sf: number
    market: string
    asset_type: string
    rent_psf_yr: number
    opex_psf_yr: number
    vacancy_pct: number
    cap_rate_now_pct: number
    cap_rate_qoq_delta_bps: number
  }
) {
  const webhookClient = getWebhookClient()
  
  const payload: ValuationUpsert = {
    schema_version: '1.0',
    type: 'valuation.upsert',
    tenant_id: getEnvConfig().tenant_id,
    as_of: new Date().toISOString().split('T')[0],
    model: {
      name: 'valuation-blend',
      version: '1.0.0'
    },
    provenance: response.provenance,
    address: `${inputs.building_sf} SF Building, ${inputs.market.toUpperCase()} Market`,
    geo: {
      lat: 32.7767, // Default Dallas coordinates
      lon: -96.7970,
      market: inputs.market.toUpperCase(),
      submarket: 'Unknown'
    },
    property_snapshot: {
      building_sf: inputs.building_sf,
      year_built: 2020 // Default
    },
    inputs: {
      asset_type: inputs.asset_type as any,
      rent_psf_yr: inputs.rent_psf_yr,
      opex_psf_yr: inputs.opex_psf_yr,
      vacancy_pct: inputs.vacancy_pct,
      cap_rate_now_pct: inputs.cap_rate_now_pct,
      cap_rate_qoq_delta_bps: inputs.cap_rate_qoq_delta_bps
    },
    current_value: {
      point: response.estimated_value,
      low: response.estimated_value_range.low,
      high: response.estimated_value_range.high,
      confidence: response.confidence_score
    },
    forecast_12m: response.forecast_12m,
    drivers: response.drivers
  }
  
  // Add status/warning if applicable
  if (response.valuation_status === 'STALE_DATA') {
    payload.status = 'STALE_DATA'
  }
  
  if (response.derived.dual_engine_disagreement_pct && response.derived.dual_engine_disagreement_pct > 15) {
    payload.warning = 'engine_disagreement'
  }
  
  return await webhookClient.send(payload, requestId)
}

async function emitInsufficientDataWebhook(
  requestId: string,
  data: {
    reason: Array<'stale_fundamentals' | 'low_comp_count' | 'no_macro_data' | 'invalid_inputs'>
    details: { comp_count: number }
    macro: any
    fundamentals: any
    comps: any
  }
) {
  const webhookClient = getWebhookClient()
  
  const payload: ValuationInsufficient = {
    schema_version: '1.0',
    type: 'valuation.insufficient',
    tenant_id: getEnvConfig().tenant_id,
    as_of: new Date().toISOString().split('T')[0],
    model: {
      name: 'valuation-blend',
      version: '1.0.0'
    },
    provenance: {
      macro: data.macro,
      fundamentals: data.fundamentals,
      comps: data.comps
    },
    address: 'Insufficient Data Property',
    reason: data.reason,
    details: data.details,
    status: 'INSUFFICIENT_DATA'
  }
  
  return await webhookClient.send(payload, requestId)
}
