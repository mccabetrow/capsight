/**
 * ===== PORTFOLIO ANALYTICS V2 ENGINE =====
 * Batch property valuation with scenario analysis and sensitivity testing
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { randomUUID } from 'crypto'
import { getEnvConfig } from '../../../lib/env-config'
import { getLiveDataFetcher } from '../../../lib/live-data-fetcher'
import { ValuationMathEngine } from '../../../lib/valuation-math'
import { getWebhookClient, type PortfolioBatch } from '../../../lib/webhook-client'

interface Property {
  id: string
  address: string
  market: string
  building_sf: number
  noi_annual?: number
  asset_type: 'office' | 'retail' | 'industrial' | 'multifamily'
  year_built?: number
  lat?: number
  lon?: number
}

interface ScenarioParameters {
  fed_funds_shock_bps?: number // e.g., +50 for 50 bps hike
  treasury_shock_bps?: number
  rent_growth_shock_pct?: number // e.g., -2.0 for 2% decline
  vacancy_shock_pct?: number // e.g., +5.0 for 5% increase
  cap_rate_shock_bps?: number // Direct cap rate adjustment
}

interface BatchValuationRequest {
  portfolio_id: string
  properties: Property[]
  baseline_scenario: ScenarioParameters
  stress_scenarios?: {
    name: string
    parameters: ScenarioParameters
  }[]
  export_format?: 'json' | 'webhook' | 'both'
  debug?: boolean
}

interface PropertyValuation {
  property: Property
  valuation: {
    estimated_value: number
    estimated_value_range: { low: number; high: number }
    cap_rate_applied: number
    price_per_sf: number
    confidence_score: number
    irr_10yr?: number
    mts_score?: number // Market Timing Score (0-100)
  }
  scenarios?: {
    [scenarioName: string]: {
      estimated_value: number
      value_change_pct: number
      irr_impact_bps: number
      cap_rate_applied: number
    }
  }
  drivers: string[]
  calculated_at: string
}

interface PortfolioAnalyticsResponse {
  portfolio_id: string
  total_properties: number
  total_value: number
  total_value_range: { low: number; high: number }
  avg_confidence: number
  avg_mts_score: number
  
  // Portfolio-level metrics
  portfolio_metrics: {
    value_weighted_cap_rate: number
    diversification_score: number // 0-100, based on market/asset type spread
    risk_adjusted_return: number
    duration_risk: number // Interest rate sensitivity
  }
  
  // Property-level results
  properties: PropertyValuation[]
  
  // Scenario analysis
  scenario_analysis?: {
    [scenarioName: string]: {
      portfolio_value: number
      value_change_pct: number
      properties_at_risk: number // Count of properties with >20% decline
      avg_irr_impact_bps: number
    }
  }
  
  // Processing metadata
  calculation_time_ms: number
  request_id: string
  webhook_delivered: boolean
  export_urls?: {
    pdf?: string
    excel?: string
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<PortfolioAnalyticsResponse | { error: string; request_id: string }>
) {
  const start_time = Date.now()
  const requestId = randomUUID()
  
  // Validate environment
  try {
    getEnvConfig()
  } catch (error) {
    console.error('❌ Environment validation failed:', error)
    return res.status(500).json({
      error: 'Server configuration error',
      request_id: requestId
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
    console.log(`🏢 Portfolio Analytics v2 started [${requestId}]`)
    
    const {
      portfolio_id,
      properties,
      baseline_scenario = {},
      stress_scenarios = [],
      export_format = 'json',
      debug = false
    }: BatchValuationRequest = req.body
    
    // Validation
    if (!portfolio_id || !properties || properties.length === 0) {
      return res.status(400).json({ 
        error: 'Missing required fields: portfolio_id, properties',
        request_id: requestId
      })
    }
    
    if (properties.length > 100) {
      return res.status(400).json({
        error: 'Portfolio size limited to 100 properties',
        request_id: requestId
      })
    }
    
    console.log(`📊 Processing ${properties.length} properties in portfolio ${portfolio_id}`)
    
    // Get shared data sources once
    const dataFetcher = getLiveDataFetcher()
    const { data: macroData } = await dataFetcher.getMacroData()
    
    if (!macroData) {
      return res.status(422).json({
        error: 'INSUFFICIENT_DATA: No macro data available',
        request_id: requestId
      })
    }
    
    // Apply baseline scenario adjustments to macro data
    const adjustedMacroData = applyScenarioToMacroData(macroData, baseline_scenario)
    
    // Process properties in parallel (with concurrency limit)
    const propertyValuations: PropertyValuation[] = []
    const batchSize = 10 // Process 10 properties at a time
    
    for (let i = 0; i < properties.length; i += batchSize) {
      const batch = properties.slice(i, i + batchSize)
      
      const batchResults = await Promise.allSettled(
        batch.map(property => processProperty(property, adjustedMacroData, dataFetcher, stress_scenarios, baseline_scenario))
      )
      
      for (const result of batchResults) {
        if (result.status === 'fulfilled') {
          propertyValuations.push(result.value)
        } else {
          console.error(`Property valuation failed:`, result.reason)
          // Add failed property with default values
          const failedProperty = batch.find(p => p.id === result.reason?.property_id)
          if (failedProperty) {
            propertyValuations.push(createFailedPropertyValuation(failedProperty, result.reason))
          }
        }
      }
      
      // Brief pause between batches to avoid overwhelming external APIs
      if (i + batchSize < properties.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
    
    // Calculate portfolio-level metrics
    const portfolioMetrics = calculatePortfolioMetrics(propertyValuations)
    const scenarioAnalysis = calculateScenarioAnalysis(propertyValuations, stress_scenarios)
    
    // Build response
    const response: PortfolioAnalyticsResponse = {
      portfolio_id,
      total_properties: properties.length,
      total_value: portfolioMetrics.total_value,
      total_value_range: portfolioMetrics.total_value_range,
      avg_confidence: portfolioMetrics.avg_confidence,
      avg_mts_score: portfolioMetrics.avg_mts_score,
      
      portfolio_metrics: {
        value_weighted_cap_rate: portfolioMetrics.value_weighted_cap_rate,
        diversification_score: portfolioMetrics.diversification_score,
        risk_adjusted_return: portfolioMetrics.risk_adjusted_return,
        duration_risk: portfolioMetrics.duration_risk
      },
      
      properties: propertyValuations,
      scenario_analysis: scenarioAnalysis,
      
      calculation_time_ms: Date.now() - start_time,
      request_id: requestId,
      webhook_delivered: false
    }
    
    // Emit webhook if requested
    if (export_format === 'webhook' || export_format === 'both') {
      try {
        await emitPortfolioWebhook(requestId, response)
        response.webhook_delivered = true
      } catch (webhookError) {
        console.error(`❌ Portfolio webhook failed [${requestId}]:`, webhookError)
      }
    }
    
    console.log(`✅ Portfolio analytics complete [${requestId}]: ${properties.length} properties, $${response.total_value.toLocaleString()} total value`)
    
    res.setHeader('Cache-Control', 'no-cache, must-revalidate')
    res.setHeader('X-Calculation-Time', `${response.calculation_time_ms}ms`)
    res.setHeader('X-Request-Id', requestId)
    
    return res.status(200).json(response)
    
  } catch (error) {
    console.error(`❌ Portfolio Analytics error [${requestId}]:`, error)
    
    return res.status(500).json({ 
      error: `Portfolio analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      request_id: requestId
    })
  }
}

// ===== HELPER FUNCTIONS =====

function applyScenarioToMacroData(macroData: any, scenario: ScenarioParameters): any {
  return {
    ...macroData,
    fed_funds_rate: macroData.fed_funds_rate + (scenario.fed_funds_shock_bps || 0) / 100,
    ten_year_treasury: macroData.ten_year_treasury + (scenario.treasury_shock_bps || 0) / 100
  }
}

async function processProperty(
  property: Property,
  macroData: any,
  dataFetcher: any,
  stressScenarios: any[],
  baselineScenario: ScenarioParameters
): Promise<PropertyValuation> {
  try {
    // Get market fundamentals
    const { data: fundamentals } = await dataFetcher.getMarketFundamentals(property.market)
    const { data: comps } = await dataFetcher.getComparableSales(property.market, 10)
    
    if (!fundamentals) {
      throw new Error(`No fundamentals for market ${property.market}`)
    }
    
    // Apply scenario adjustments to fundamentals
    const adjustedFundamentals = {
      ...fundamentals,
      rent_growth_yoy_pct: fundamentals.rent_growth_yoy_pct + (baselineScenario.rent_growth_shock_pct || 0),
      vacancy_rate_pct: Math.max(0, fundamentals.vacancy_rate_pct + (baselineScenario.vacancy_shock_pct || 0)),
      avg_cap_rate_pct: fundamentals.avg_cap_rate_pct + (baselineScenario.cap_rate_shock_bps || 0) / 100
    }
    
    // Calculate NOI if not provided
    let noi = property.noi_annual
    if (!noi) {
      noi = ValuationMathEngine.calculateNOI(
        property.building_sf,
        adjustedFundamentals.avg_asking_rent_psf_yr_nnn,
        adjustedFundamentals.avg_asking_rent_psf_yr_nnn * 0.30,
        adjustedFundamentals.vacancy_rate_pct / 100
      )
    }
    
    // Base valuation
    const capRate = adjustedFundamentals.avg_cap_rate_pct + 
                   Math.max(0, (macroData.fed_funds_rate - 2.0) * 0.1)
    
    const currentValue = ValuationMathEngine.calculateCurrentValue(noi, capRate)
    const dualEngineResult = ValuationMathEngine.performDualEngineCheck(currentValue, comps || [], property.building_sf)
    
    // Calculate confidence and MTS score
    const confidence = ValuationMathEngine.calculateConfidence({
      comp_count: comps?.length || 0,
      macro_freshness_days: 1,
      fundamentals_freshness_days: 7,
      comps_freshness_days: 30,
      dual_engine_disagreement_pct: dualEngineResult.disagreement_pct,
      cap_rate_variance_from_market: 0
    })
    
    // Market Timing Score (0-100)
    const mtsScore = calculateMarketTimingScore(macroData, adjustedFundamentals, property.market)
    
    // IRR calculation (simplified 10-year hold)
    const futureNOI = ValuationMathEngine.calculateFutureNOI(noi, adjustedFundamentals.rent_growth_yoy_pct, 10)
    const exitCapRate = capRate + 0.5 // Assume 50bps cap rate expansion over 10 years
    const exitValue = futureNOI / (exitCapRate / 100)
    const irr10yr = Math.pow(exitValue / dualEngineResult.recommended_value, 1/10) - 1
    
    // Scenario analysis
    const scenarios: { [key: string]: any } = {}
    for (const stressScenario of stressScenarios) {
      const scenarioResult = calculatePropertyScenario(property, noi, macroData, adjustedFundamentals, stressScenario, dualEngineResult.recommended_value)
      scenarios[stressScenario.name] = scenarioResult
    }
    
    return {
      property,
      valuation: {
        estimated_value: Math.round(dualEngineResult.recommended_value),
        estimated_value_range: ValuationMathEngine.calculateValuationRange(dualEngineResult.recommended_value, confidence),
        cap_rate_applied: Math.round(capRate * 100) / 100,
        price_per_sf: Math.round(dualEngineResult.recommended_value / property.building_sf),
        confidence_score: Math.round(confidence * 100) / 100,
        irr_10yr: Math.round(irr10yr * 10000) / 100, // In basis points
        mts_score: Math.round(mtsScore)
      },
      scenarios,
      drivers: [
        `Cap rate: ${capRate.toFixed(2)}%`,
        `NOI: $${Math.round(noi).toLocaleString()}`,
        `Market: ${property.market.toUpperCase()}`,
        `MTS: ${Math.round(mtsScore)}/100`
      ],
      calculated_at: new Date().toISOString()
    }
    
  } catch (error) {
    throw { property_id: property.id, error: error instanceof Error ? error.message : 'Unknown error' }
  }
}

function calculateMarketTimingScore(macroData: any, fundamentals: any, market: string): number {
  // Market Timing Score algorithm (0-100)
  let score = 50 // Neutral baseline
  
  // Interest rate factor (lower rates = higher score)
  const rateFactor = Math.max(0, (6 - macroData.fed_funds_rate) * 5) // +/- 25 points
  score += rateFactor
  
  // Rent growth factor
  const rentGrowthFactor = Math.min(20, fundamentals.rent_growth_yoy_pct * 5) // Up to +20 points
  score += rentGrowthFactor
  
  // Vacancy factor (lower vacancy = higher score)
  const vacancyFactor = Math.max(-20, (10 - fundamentals.vacancy_rate_pct) * 2) // +/- 20 points
  score += vacancyFactor
  
  // Cap rate spread factor (wider spreads = better value)
  const spreadFactor = Math.max(0, (macroData.ten_year_treasury - macroData.fed_funds_rate - 1.5) * 10)
  score += spreadFactor
  
  return Math.max(0, Math.min(100, score))
}

function calculatePropertyScenario(
  property: Property,
  baseNOI: number,
  macroData: any,
  fundamentals: any,
  scenario: { parameters: ScenarioParameters },
  baseValue: number
): any {
  // Apply scenario shocks
  const shockedMacro = applyScenarioToMacroData(macroData, scenario.parameters)
  const shockedFundamentals = {
    ...fundamentals,
    rent_growth_yoy_pct: fundamentals.rent_growth_yoy_pct + (scenario.parameters.rent_growth_shock_pct || 0),
    vacancy_rate_pct: Math.max(0, fundamentals.vacancy_rate_pct + (scenario.parameters.vacancy_shock_pct || 0)),
    avg_cap_rate_pct: fundamentals.avg_cap_rate_pct + (scenario.parameters.cap_rate_shock_bps || 0) / 100
  }
  
  // Recalculate NOI with vacancy shock
  const shockedNOI = baseNOI * (1 - (scenario.parameters.vacancy_shock_pct || 0) / 100)
  
  // Recalculate cap rate with shocks
  const shockedCapRate = shockedFundamentals.avg_cap_rate_pct + 
                        Math.max(0, (shockedMacro.fed_funds_rate - 2.0) * 0.1)
  
  // New value
  const shockedValue = ValuationMathEngine.calculateCurrentValue(shockedNOI, shockedCapRate)
  
  // IRR impact (simplified)
  const valueChangePct = (shockedValue - baseValue) / baseValue * 100
  const irrImpactBps = valueChangePct * 10 // Rough approximation: 1% value change = 10bps IRR impact
  
  return {
    estimated_value: Math.round(shockedValue),
    value_change_pct: Math.round(valueChangePct * 100) / 100,
    irr_impact_bps: Math.round(irrImpactBps),
    cap_rate_applied: Math.round(shockedCapRate * 100) / 100
  }
}

function calculatePortfolioMetrics(properties: PropertyValuation[]): any {
  const totalValue = properties.reduce((sum, p) => sum + p.valuation.estimated_value, 0)
  const totalLow = properties.reduce((sum, p) => sum + p.valuation.estimated_value_range.low, 0)
  const totalHigh = properties.reduce((sum, p) => sum + p.valuation.estimated_value_range.high, 0)
  
  // Value-weighted cap rate
  const valueWeightedCapRate = properties.reduce((sum, p) => 
    sum + (p.valuation.cap_rate_applied * p.valuation.estimated_value), 0) / totalValue
  
  // Average metrics
  const avgConfidence = properties.reduce((sum, p) => sum + p.valuation.confidence_score, 0) / properties.length
  const avgMTS = properties.reduce((sum, p) => sum + (p.valuation.mts_score || 50), 0) / properties.length
  
  // Diversification score based on market/asset type spread
  const uniqueMarkets = new Set(properties.map(p => p.property.market)).size
  const uniqueAssetTypes = new Set(properties.map(p => p.property.asset_type)).size
  const diversificationScore = Math.min(100, (uniqueMarkets * 20) + (uniqueAssetTypes * 20))
  
  // Duration risk (interest rate sensitivity)
  const avgCapRate = valueWeightedCapRate
  const durationRisk = Math.max(1, 12 / avgCapRate) // Higher cap rates = lower duration
  
  return {
    total_value: Math.round(totalValue),
    total_value_range: { low: Math.round(totalLow), high: Math.round(totalHigh) },
    avg_confidence: Math.round(avgConfidence * 100) / 100,
    avg_mts_score: Math.round(avgMTS),
    value_weighted_cap_rate: Math.round(valueWeightedCapRate * 100) / 100,
    diversification_score: Math.round(diversificationScore),
    risk_adjusted_return: Math.round((valueWeightedCapRate - 2.0) * 100) / 100, // Spread over risk-free
    duration_risk: Math.round(durationRisk * 100) / 100
  }
}

function calculateScenarioAnalysis(properties: PropertyValuation[], stressScenarios: any[]): any {
  const analysis: any = {}
  
  for (const scenario of stressScenarios) {
    const scenarioName = scenario.name
    let portfolioValue = 0
    let propertiesAtRisk = 0
    let totalIRRImpact = 0
    
    for (const property of properties) {
      if (property.scenarios?.[scenarioName]) {
        const scenarioResult = property.scenarios[scenarioName]
        portfolioValue += scenarioResult.estimated_value
        
        if (scenarioResult.value_change_pct < -20) {
          propertiesAtRisk++
        }
        
        totalIRRImpact += scenarioResult.irr_impact_bps
      }
    }
    
    const basePortfolioValue = properties.reduce((sum, p) => sum + p.valuation.estimated_value, 0)
    const valueChangePct = (portfolioValue - basePortfolioValue) / basePortfolioValue * 100
    const avgIRRImpact = totalIRRImpact / properties.length
    
    analysis[scenarioName] = {
      portfolio_value: Math.round(portfolioValue),
      value_change_pct: Math.round(valueChangePct * 100) / 100,
      properties_at_risk: propertiesAtRisk,
      avg_irr_impact_bps: Math.round(avgIRRImpact)
    }
  }
  
  return analysis
}

function createFailedPropertyValuation(property: Property, error: any): PropertyValuation {
  return {
    property,
    valuation: {
      estimated_value: 0,
      estimated_value_range: { low: 0, high: 0 },
      cap_rate_applied: 0,
      price_per_sf: 0,
      confidence_score: 0,
      irr_10yr: 0,
      mts_score: 0
    },
    drivers: [`Error: ${error.error || 'Valuation failed'}`],
    calculated_at: new Date().toISOString()
  }
}

async function emitPortfolioWebhook(requestId: string, response: PortfolioAnalyticsResponse) {
  const webhookClient = getWebhookClient()
  
  const payload: PortfolioBatch = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    schema_version: '1.0',
    type: 'portfolio.batch',
    tenant_id: getEnvConfig().tenant_id,
    as_of: new Date().toISOString().split('T')[0],
    model: {
      name: 'portfolio-analytics-v2',
      version: '1.0.0'
    },
    portfolio_id: response.portfolio_id,
    property_count: response.total_properties,
    portfolio_value: {
      point: response.total_value,
      low: response.total_value_range.low,
      high: response.total_value_range.high,
      confidence: response.avg_confidence
    },
    portfolio_metrics: response.portfolio_metrics,
    scenario_analysis: response.scenario_analysis,
    top_performers: response.properties
      .sort((a, b) => (b.valuation.mts_score || 0) - (a.valuation.mts_score || 0))
      .slice(0, 5)
      .map(p => ({
        property_id: p.property.id,
        address: p.property.address,
        estimated_value: p.valuation.estimated_value,
        mts_score: p.valuation.mts_score || 0
      })),
    calculated_at: response.properties[0]?.calculated_at || new Date().toISOString()
  }
  
  return await webhookClient.send(payload, requestId)
}
