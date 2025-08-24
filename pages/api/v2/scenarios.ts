/**
 * ===== SCENARIO SIMULATION ENGINE =====
 * "What-if" analysis for Fed rate hikes, market shocks, and sensitivity testing
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { randomUUID } from 'crypto'
import { getEnvConfig } from '../../../lib/env-config'
import { getLiveDataFetcher } from '../../../lib/live-data-fetcher'
import { ValuationMathEngine } from '../../../lib/valuation-math'

interface ScenarioDefinition {
  name: string
  description: string
  parameters: {
    // Macro shocks
    fed_funds_shock_bps?: number      // e.g., +50 for 50 bps hike
    treasury_shock_bps?: number       // e.g., +75 for 75 bps increase
    credit_spread_shock_bps?: number  // e.g., +100 for credit tightening
    
    // Market shocks  
    rent_growth_shock_pct?: number    // e.g., -2.0 for 2% decline in growth
    vacancy_shock_pct?: number        // e.g., +3.0 for 3% vacancy increase
    cap_rate_shock_bps?: number       // Direct cap rate adjustment
    
    // Economic shocks
    recession_probability?: number    // 0-1, impacts multiple factors
    inflation_shock_pct?: number      // CPI impact
    employment_shock_pct?: number     // Job market impact on demand
  }
}

interface PropertyInput {
  id: string
  market: string
  building_sf: number
  noi_annual: number
  asset_type: 'office' | 'retail' | 'industrial' | 'multifamily'
  current_value?: number // For comparison
}

interface ScenarioRequest {
  properties: PropertyInput[]
  scenarios: ScenarioDefinition[]
  sensitivity_analysis?: {
    variable: 'fed_funds' | 'cap_rate' | 'rent_growth' | 'vacancy'
    min_value: number
    max_value: number
    steps: number
  }
  output_format?: 'detailed' | 'summary'
}

interface ScenarioResult {
  scenario: ScenarioDefinition
  property_results: {
    property_id: string
    baseline_value: number
    scenario_value: number
    value_change_pct: number
    value_change_dollars: number
    irr_impact_bps: number
    new_cap_rate: number
    risk_metrics: {
      duration_risk: number
      volatility_score: number
      stress_test_rank: 'LOW' | 'MEDIUM' | 'HIGH' // Risk category
    }
  }[]
  portfolio_impact: {
    total_baseline_value: number
    total_scenario_value: number
    portfolio_change_pct: number
    portfolio_change_dollars: number
    properties_at_risk: number // Count with >20% decline
    avg_irr_impact_bps: number
    worst_performer: string // Property ID
    best_performer: string // Property ID
  }
}

interface SensitivityAnalysisResult {
  variable: string
  data_points: {
    input_value: number
    portfolio_value: number
    portfolio_change_pct: number
  }[]
  inflection_points: {
    value: number
    description: string
  }[]
}

interface ScenarioResponse {
  request_id: string
  total_properties: number
  total_scenarios: number
  baseline_portfolio_value: number
  
  scenario_results: ScenarioResult[]
  sensitivity_analysis?: SensitivityAnalysisResult
  
  // Risk summary
  risk_summary: {
    most_vulnerable_scenario: string
    max_portfolio_decline_pct: number
    stress_test_grade: 'A' | 'B' | 'C' | 'D' | 'F'
    key_risks: string[]
    recommendations: string[]
  }
  
  calculation_time_ms: number
  calculated_at: string
}

// Pre-defined scenario templates
const SCENARIO_TEMPLATES: ScenarioDefinition[] = [
  {
    name: 'Fed Hikes 50bps',
    description: 'Federal Reserve raises rates by 50 basis points',
    parameters: {
      fed_funds_shock_bps: 50,
      treasury_shock_bps: 40,
      credit_spread_shock_bps: 20
    }
  },
  {
    name: 'Fed Hikes 100bps (Aggressive)',
    description: 'Aggressive Fed tightening cycle - 100 bps increase',
    parameters: {
      fed_funds_shock_bps: 100,
      treasury_shock_bps: 75,
      credit_spread_shock_bps: 50,
      recession_probability: 0.3
    }
  },
  {
    name: 'Mild Recession',
    description: 'Economic downturn with employment and demand impacts',
    parameters: {
      recession_probability: 0.7,
      employment_shock_pct: -3.0,
      rent_growth_shock_pct: -1.5,
      vacancy_shock_pct: 2.0,
      cap_rate_shock_bps: 25
    }
  },
  {
    name: 'Severe Recession',
    description: '2008-style economic crisis scenario',
    parameters: {
      recession_probability: 0.9,
      employment_shock_pct: -7.0,
      rent_growth_shock_pct: -3.0,
      vacancy_shock_pct: 5.0,
      cap_rate_shock_bps: 75,
      credit_spread_shock_bps: 200
    }
  },
  {
    name: 'Inflation Spike',
    description: 'Persistent high inflation scenario',
    parameters: {
      inflation_shock_pct: 3.0,
      fed_funds_shock_bps: 150,
      treasury_shock_bps: 100,
      rent_growth_shock_pct: 2.0 // Some rent growth from inflation
    }
  },
  {
    name: 'Credit Crisis',
    description: 'Banking sector stress and credit tightening',
    parameters: {
      credit_spread_shock_bps: 300,
      cap_rate_shock_bps: 100,
      recession_probability: 0.5
    }
  }
]

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ScenarioResponse | { error: string; request_id: string }>
) {
  const start_time = Date.now()
  const requestId = randomUUID()
  
  // Validate environment
  try {
    getEnvConfig()
  } catch (error) {
    return res.status(500).json({
      error: 'Server configuration error',
      request_id: requestId
    })
  }
  
  if (req.method !== 'POST') {
    return res.status(405).json({ 
      error: 'Method not allowed',
      request_id: requestId
    })
  }
  
  try {
    console.log(`🎯 Scenario simulation started [${requestId}]`)
    
    let { properties, scenarios, sensitivity_analysis, output_format = 'detailed' }: ScenarioRequest = req.body
    
    // Validation
    if (!properties || properties.length === 0) {
      return res.status(400).json({ 
        error: 'Missing required field: properties',
        request_id: requestId
      })
    }
    
    if (properties.length > 50) {
      return res.status(400).json({
        error: 'Maximum 50 properties allowed for scenario analysis',
        request_id: requestId
      })
    }
    
    // Use templates if no custom scenarios provided
    if (!scenarios || scenarios.length === 0) {
      scenarios = SCENARIO_TEMPLATES
    }
    
    console.log(`📊 Running ${scenarios.length} scenarios on ${properties.length} properties`)
    
    // Get baseline macro data
    const dataFetcher = getLiveDataFetcher()
    const { data: baseMacroData } = await dataFetcher.getMacroData()
    
    if (!baseMacroData) {
      return res.status(422).json({
        error: 'INSUFFICIENT_DATA: No macro data available',
        request_id: requestId
      })
    }
    
    // Calculate baseline portfolio value
    let baselinePortfolioValue = 0
    const baselineValues: { [propertyId: string]: number } = {}
    
    for (const property of properties) {
      const baseValue = property.current_value || 
                       await calculatePropertyBaseline(property, baseMacroData, dataFetcher)
      baselineValues[property.id] = baseValue
      baselinePortfolioValue += baseValue
    }
    
    // Run scenario analysis
    const scenarioResults: ScenarioResult[] = []
    
    for (const scenario of scenarios) {
      console.log(`🔬 Running scenario: ${scenario.name}`)
      
      const propertyResults = []
      let totalScenarioValue = 0
      let propertiesAtRisk = 0
      let totalIRRImpact = 0
      let worstDecline = 0
      let bestPerformance = 0
      let worstPerformer = ''
      let bestPerformer = ''
      
      for (const property of properties) {
        const baselineValue = baselineValues[property.id]
        const scenarioValue = await calculatePropertyScenario(property, scenario, baseMacroData, dataFetcher)
        
        const valueChangePct = (scenarioValue - baselineValue) / baselineValue * 100
        const valueChangeDollars = scenarioValue - baselineValue
        const irrImpactBps = estimateIRRImpact(valueChangePct, property.asset_type)
        
        // Track worst/best performers
        if (valueChangePct < worstDecline) {
          worstDecline = valueChangePct
          worstPerformer = property.id
        }
        if (valueChangePct > bestPerformance) {
          bestPerformance = valueChangePct
          bestPerformer = property.id
        }
        
        // Risk assessment
        if (valueChangePct < -20) {
          propertiesAtRisk++
        }
        
        // Calculate new cap rate
        const newCapRate = calculateScenarioCapRate(property, scenario, baseMacroData)
        
        // Risk metrics
        const riskMetrics = calculateRiskMetrics(property, scenario, valueChangePct)
        
        propertyResults.push({
          property_id: property.id,
          baseline_value: Math.round(baselineValue),
          scenario_value: Math.round(scenarioValue),
          value_change_pct: Math.round(valueChangePct * 100) / 100,
          value_change_dollars: Math.round(valueChangeDollars),
          irr_impact_bps: Math.round(irrImpactBps),
          new_cap_rate: Math.round(newCapRate * 100) / 100,
          risk_metrics: riskMetrics
        })
        
        totalScenarioValue += scenarioValue
        totalIRRImpact += irrImpactBps
      }
      
      const portfolioChangePct = (totalScenarioValue - baselinePortfolioValue) / baselinePortfolioValue * 100
      
      scenarioResults.push({
        scenario,
        property_results: propertyResults,
        portfolio_impact: {
          total_baseline_value: Math.round(baselinePortfolioValue),
          total_scenario_value: Math.round(totalScenarioValue),
          portfolio_change_pct: Math.round(portfolioChangePct * 100) / 100,
          portfolio_change_dollars: Math.round(totalScenarioValue - baselinePortfolioValue),
          properties_at_risk: propertiesAtRisk,
          avg_irr_impact_bps: Math.round(totalIRRImpact / properties.length),
          worst_performer: worstPerformer,
          best_performer: bestPerformer
        }
      })
    }
    
    // Sensitivity analysis (if requested)
    let sensitivityResult: SensitivityAnalysisResult | undefined
    if (sensitivity_analysis) {
      sensitivityResult = await runSensitivityAnalysis(
        properties, 
        sensitivity_analysis, 
        baseMacroData, 
        dataFetcher, 
        baselinePortfolioValue
      )
    }
    
    // Risk summary and grading
    const riskSummary = calculateRiskSummary(scenarioResults)
    
    const response: ScenarioResponse = {
      request_id: requestId,
      total_properties: properties.length,
      total_scenarios: scenarios.length,
      baseline_portfolio_value: Math.round(baselinePortfolioValue),
      
      scenario_results: scenarioResults,
      sensitivity_analysis: sensitivityResult,
      risk_summary: riskSummary,
      
      calculation_time_ms: Date.now() - start_time,
      calculated_at: new Date().toISOString()
    }
    
    console.log(`✅ Scenario analysis complete [${requestId}]: ${scenarios.length} scenarios, max decline ${riskSummary.max_portfolio_decline_pct.toFixed(1)}%`)
    
    res.setHeader('Cache-Control', 'no-cache, must-revalidate')
    res.setHeader('X-Request-Id', requestId)
    
    return res.status(200).json(response)
    
  } catch (error) {
    console.error(`❌ Scenario simulation error [${requestId}]:`, error)
    
    return res.status(500).json({ 
      error: `Scenario simulation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      request_id: requestId
    })
  }
}

// ===== HELPER FUNCTIONS =====

async function calculatePropertyBaseline(property: PropertyInput, macroData: any, dataFetcher: any): Promise<number> {
  const { data: fundamentals } = await dataFetcher.getMarketFundamentals(property.market)
  
  if (!fundamentals) {
    return property.noi_annual / 0.06 // Default 6% cap rate
  }
  
  const capRate = fundamentals.avg_cap_rate_pct + Math.max(0, (macroData.fed_funds_rate - 2.0) * 0.1)
  return ValuationMathEngine.calculateCurrentValue(property.noi_annual, capRate)
}

async function calculatePropertyScenario(
  property: PropertyInput, 
  scenario: ScenarioDefinition, 
  baseMacroData: any, 
  dataFetcher: any
): Promise<number> {
  const { data: baseFundamentals } = await dataFetcher.getMarketFundamentals(property.market)
  
  if (!baseFundamentals) {
    return property.noi_annual / 0.08 // Default higher cap rate for scenario
  }
  
  // Apply macro shocks
  const shockedMacro = {
    ...baseMacroData,
    fed_funds_rate: baseMacroData.fed_funds_rate + (scenario.parameters.fed_funds_shock_bps || 0) / 100,
    ten_year_treasury: baseMacroData.ten_year_treasury + (scenario.parameters.treasury_shock_bps || 0) / 100
  }
  
  // Apply market shocks
  const shockedFundamentals = {
    ...baseFundamentals,
    rent_growth_yoy_pct: baseFundamentals.rent_growth_yoy_pct + (scenario.parameters.rent_growth_shock_pct || 0),
    vacancy_rate_pct: Math.max(0, baseFundamentals.vacancy_rate_pct + (scenario.parameters.vacancy_shock_pct || 0)),
    avg_cap_rate_pct: baseFundamentals.avg_cap_rate_pct + (scenario.parameters.cap_rate_shock_bps || 0) / 100
  }
  
  // Calculate shocked NOI (vacancy impact)
  const vacancyImpact = (scenario.parameters.vacancy_shock_pct || 0) / 100
  const shockedNOI = property.noi_annual * (1 - vacancyImpact)
  
  // Calculate shocked cap rate
  const fedPremium = Math.max(0, (shockedMacro.fed_funds_rate - 2.0) * 0.1)
  const creditSpread = (scenario.parameters.credit_spread_shock_bps || 0) / 100
  const recessionRisk = (scenario.parameters.recession_probability || 0) * 0.5 // Up to 50bps recession premium
  
  const shockedCapRate = shockedFundamentals.avg_cap_rate_pct + fedPremium + creditSpread + recessionRisk
  
  return ValuationMathEngine.calculateCurrentValue(shockedNOI, shockedCapRate)
}

function calculateScenarioCapRate(property: PropertyInput, scenario: ScenarioDefinition, baseMacroData: any): number {
  const baseCapRate = 6.0 // Default assumption
  const fedShock = (scenario.parameters.fed_funds_shock_bps || 0) / 100 * 0.7 // ~70% pass-through
  const directShock = (scenario.parameters.cap_rate_shock_bps || 0) / 100
  const creditSpread = (scenario.parameters.credit_spread_shock_bps || 0) / 100 * 0.5 // 50% pass-through
  const recessionPremium = (scenario.parameters.recession_probability || 0) * 0.5
  
  return baseCapRate + fedShock + directShock + creditSpread + recessionPremium
}

function estimateIRRImpact(valueChangePct: number, assetType: string): number {
  // Rough approximation: value impact to IRR impact varies by asset type
  const multipliers: Record<string, number> = {
    'office': 12,      // More sensitive to value changes
    'retail': 10,      // Moderate sensitivity 
    'industrial': 8,   // Less sensitive, more stable
    'multifamily': 9   // Moderate sensitivity
  }
  
  const multiplier = multipliers[assetType] || 10
  return valueChangePct * multiplier // e.g., -10% value = -100bps IRR impact
}

function calculateRiskMetrics(property: PropertyInput, scenario: ScenarioDefinition, valueChangePct: number) {
  // Duration risk (interest rate sensitivity)
  const durationRisk = Math.abs((scenario.parameters.fed_funds_shock_bps || 0) * valueChangePct / 100)
  
  // Volatility score based on multiple shock impacts
  const shockCount = Object.values(scenario.parameters).filter(v => v && v !== 0).length
  const volatilityScore = Math.min(100, Math.abs(valueChangePct) * shockCount)
  
  // Risk category
  let stressTestRank: 'LOW' | 'MEDIUM' | 'HIGH'
  if (Math.abs(valueChangePct) < 10) {
    stressTestRank = 'LOW'
  } else if (Math.abs(valueChangePct) < 25) {
    stressTestRank = 'MEDIUM'
  } else {
    stressTestRank = 'HIGH'
  }
  
  return {
    duration_risk: Math.round(durationRisk * 100) / 100,
    volatility_score: Math.round(volatilityScore),
    stress_test_rank: stressTestRank
  }
}

async function runSensitivityAnalysis(
  properties: PropertyInput[],
  sensitivity: NonNullable<ScenarioRequest['sensitivity_analysis']>,
  baseMacroData: any,
  dataFetcher: any,
  baselineValue: number
): Promise<SensitivityAnalysisResult> {
  
  const dataPoints = []
  const step = (sensitivity.max_value - sensitivity.min_value) / sensitivity.steps
  
  for (let i = 0; i <= sensitivity.steps; i++) {
    const inputValue = sensitivity.min_value + (i * step)
    
    // Create scenario with this input value
    const scenario: ScenarioDefinition = {
      name: `Sensitivity Test ${i}`,
      description: `${sensitivity.variable} = ${inputValue}`,
      parameters: {}
    }
    
    // Map variable to parameter
    switch (sensitivity.variable) {
      case 'fed_funds':
        scenario.parameters.fed_funds_shock_bps = (inputValue - baseMacroData.fed_funds_rate) * 100
        break
      case 'cap_rate':
        scenario.parameters.cap_rate_shock_bps = inputValue * 100
        break
      case 'rent_growth':
        scenario.parameters.rent_growth_shock_pct = inputValue
        break
      case 'vacancy':
        scenario.parameters.vacancy_shock_pct = inputValue
        break
    }
    
    // Calculate portfolio value for this scenario
    let portfolioValue = 0
    for (const property of properties) {
      const scenarioValue = await calculatePropertyScenario(property, scenario, baseMacroData, dataFetcher)
      portfolioValue += scenarioValue
    }
    
    const portfolioChangePct = (portfolioValue - baselineValue) / baselineValue * 100
    
    dataPoints.push({
      input_value: Math.round(inputValue * 100) / 100,
      portfolio_value: Math.round(portfolioValue),
      portfolio_change_pct: Math.round(portfolioChangePct * 100) / 100
    })
  }
  
  // Find inflection points (where slope changes significantly)
  const inflectionPoints = []
  for (let i = 1; i < dataPoints.length - 1; i++) {
    const slope1 = dataPoints[i].portfolio_change_pct - dataPoints[i-1].portfolio_change_pct
    const slope2 = dataPoints[i+1].portfolio_change_pct - dataPoints[i].portfolio_change_pct
    
    if (Math.abs(slope2 - slope1) > 5) { // Significant slope change
      inflectionPoints.push({
        value: dataPoints[i].input_value,
        description: `Significant sensitivity change at ${sensitivity.variable} = ${dataPoints[i].input_value}`
      })
    }
  }
  
  return {
    variable: sensitivity.variable,
    data_points: dataPoints,
    inflection_points: inflectionPoints
  }
}

function calculateRiskSummary(scenarioResults: ScenarioResult[]) {
  let maxDecline = 0
  let mostVulnerableScenario = ''
  
  // Find worst-case scenario
  for (const result of scenarioResults) {
    if (result.portfolio_impact.portfolio_change_pct < maxDecline) {
      maxDecline = result.portfolio_impact.portfolio_change_pct
      mostVulnerableScenario = result.scenario.name
    }
  }
  
  // Grade based on maximum decline
  let grade: 'A' | 'B' | 'C' | 'D' | 'F'
  if (maxDecline > -10) grade = 'A'       // Less than 10% decline
  else if (maxDecline > -20) grade = 'B'  // 10-20% decline
  else if (maxDecline > -30) grade = 'C'  // 20-30% decline
  else if (maxDecline > -40) grade = 'D'  // 30-40% decline
  else grade = 'F'                        // More than 40% decline
  
  // Identify key risks
  const keyRisks = []
  for (const result of scenarioResults) {
    if (result.portfolio_impact.portfolio_change_pct < -15) {
      keyRisks.push(`${result.scenario.name}: ${result.portfolio_impact.portfolio_change_pct.toFixed(1)}% decline`)
    }
  }
  
  // Generate recommendations
  const recommendations = []
  if (maxDecline < -30) {
    recommendations.push('Consider portfolio rebalancing to reduce concentration risk')
    recommendations.push('Evaluate hedging strategies for interest rate exposure')
  }
  if (maxDecline < -20) {
    recommendations.push('Monitor credit markets closely for early warning signals')
    recommendations.push('Consider increasing cash reserves for opportunities')
  }
  recommendations.push('Stress test key assumptions quarterly')
  recommendations.push('Diversify across markets and asset types')
  
  return {
    most_vulnerable_scenario: mostVulnerableScenario,
    max_portfolio_decline_pct: Math.round(Math.abs(maxDecline) * 100) / 100,
    stress_test_grade: grade,
    key_risks: keyRisks.slice(0, 5), // Top 5 risks
    recommendations: recommendations.slice(0, 4) // Top 4 recommendations
  }
}

// Export scenario templates for frontend use
export { SCENARIO_TEMPLATES }
