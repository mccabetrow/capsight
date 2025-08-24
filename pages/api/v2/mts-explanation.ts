/**
 * ===== MTS EXPLANATION API =====
 * Provides detailed explanations for Market Timing Scores
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { createClient } from '@supabase/supabase-js'

interface MTSExplanationRequest {
  property_id: string
  include_recommendations?: boolean
  debug?: boolean
}

interface MTSExplanation {
  property_id: string
  mts_score: number
  grade: 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D'
  drivers: {
    factor: string
    score: number
    weight: number
    impact: 'positive' | 'negative' | 'neutral'
    explanation: string
  }[]
  market_conditions: {
    interest_rates: { score: number; trend: 'rising' | 'falling' | 'stable'; current_value: string }
    rent_growth: { score: number; trend: 'rising' | 'falling' | 'stable'; current_value: string }
    vacancy: { score: number; trend: 'rising' | 'falling' | 'stable'; current_value: string }
    cap_rate_spreads: { score: number; trend: 'rising' | 'falling' | 'stable'; current_value: string }
  }
  recommendations: string[]
  last_updated: string
  calculation_details?: any
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<MTSExplanation | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const property_id = req.query.property_id as string
    const include_recommendations = req.query.include_recommendations === 'true'
    const debug = req.query.debug === 'true'

    if (!property_id) {
      return res.status(400).json({ error: 'Missing required parameter: property_id' })
    }

    console.log(`🔍 Fetching MTS explanation for property: ${property_id}`)

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    )

    // Get property data
    const { data: property, error: propertyError } = await supabase
      .from('properties')
      .select(`
        *,
        market_fundamentals!inner(*)
      `)
      .eq('id', property_id)
      .single()

    if (propertyError || !property) {
      console.error('Property not found:', propertyError)
      return res.status(404).json({ error: 'Property not found' })
    }

    // Calculate MTS components
    const mtsExplanation = await calculateMTSExplanation(property, supabase, debug)

    console.log(`✅ MTS explanation calculated: ${mtsExplanation.mts_score}/100 (Grade ${mtsExplanation.grade})`)

    return res.status(200).json(mtsExplanation)

  } catch (error) {
    console.error('❌ MTS explanation error:', error)
    return res.status(500).json({ 
      error: `MTS explanation failed: ${error instanceof Error ? error.message : 'Unknown error'}` 
    })
  }
}

interface DriverResult {
  factor: string
  score: number
  weight: number
  impact: 'positive' | 'negative' | 'neutral'
  explanation: string
}

// ===== MTS CALCULATION ENGINE =====

async function calculateMTSExplanation(property: any, supabase: any, debug: boolean): Promise<MTSExplanation> {
  
  // Get current macro data
  const macroData = await fetchCurrentMacroData(supabase)
  const fundamentals = property.market_fundamentals
  
  // Calculate individual driver scores
  const drivers: DriverResult[] = [
    calculateInterestRateDriver(macroData),
    calculateRentGrowthDriver(fundamentals),
    calculateVacancyDriver(fundamentals),
    calculateSupplyDemandDriver(fundamentals),
    calculateCapRateSpreadDriver(macroData, fundamentals),
    calculateLiquidityDriver(fundamentals),
    calculateMarketSentimentDriver(fundamentals)
  ]

  // Calculate weighted MTS score
  const totalWeight = drivers.reduce((sum, driver) => sum + driver.weight, 0)
  const weightedScore = drivers.reduce((sum, driver) => sum + (driver.score * driver.weight), 0) / totalWeight
  const mtsScore = Math.round(weightedScore)

  // Determine grade
  const grade = getMTSGrade(mtsScore)

  // Get market conditions
  const marketConditions = {
    interest_rates: {
      score: drivers.find(d => d.factor === 'Interest Rates')?.score || 0,
      trend: getInterestRateTrend(macroData),
      current_value: `${macroData.fed_funds_rate?.toFixed(2) || 'N/A'}%`
    },
    rent_growth: {
      score: drivers.find(d => d.factor === 'Rent Growth')?.score || 0,
      trend: getRentGrowthTrend(fundamentals),
      current_value: `${fundamentals.rent_growth_yoy?.toFixed(1) || 'N/A'}%`
    },
    vacancy: {
      score: drivers.find(d => d.factor === 'Vacancy Rate')?.score || 0,
      trend: getVacancyTrend(fundamentals),
      current_value: `${fundamentals.vacancy_rate?.toFixed(1) || 'N/A'}%`
    },
    cap_rate_spreads: {
      score: drivers.find(d => d.factor === 'Cap Rate Spreads')?.score || 0,
      trend: getCapRateSpreadTrend(macroData, fundamentals),
      current_value: `${fundamentals.cap_rate_trend?.toFixed(0) || 'N/A'}bps`
    }
  }

  // Generate recommendations
  const recommendations = generateRecommendations(mtsScore, drivers, marketConditions)

  const explanation: MTSExplanation = {
    property_id: property.id,
    mts_score: mtsScore,
    grade,
    drivers,
    market_conditions: marketConditions,
    recommendations,
    last_updated: new Date().toISOString(),
    ...(debug && { calculation_details: { macroData, fundamentals, totalWeight, weightedScore } })
  }

  return explanation
}

// ===== DRIVER CALCULATIONS =====

function calculateInterestRateDriver(macroData: any): DriverResult {
  const fedRate = macroData.fed_funds_rate || 5.25
  const tenYear = macroData.treasury_10yr || 4.5
  
  // Lower rates = higher score (better for real estate)
  let score = Math.max(0, 100 - (fedRate * 15))
  
  // Bonus for inverted yield curve (recession protection)
  if (fedRate > tenYear) {
    score += 10
  }
  
  const impact: 'positive' | 'negative' | 'neutral' = fedRate < 4 ? 'positive' : fedRate > 6 ? 'negative' : 'neutral'
  
  return {
    factor: 'Interest Rates',
    score: Math.min(100, Math.round(score)),
    weight: 0.25,
    impact,
    explanation: `Fed funds rate at ${fedRate.toFixed(2)}%. ${
      fedRate < 4 ? 'Low rates support property values and financing accessibility.' :
      fedRate > 6 ? 'High rates create headwinds for valuations and transaction activity.' :
      'Moderate rates provide balanced investment environment.'
    }`
  }
}

function calculateRentGrowthDriver(fundamentals: any): DriverResult {
  const rentGrowth = fundamentals.rent_growth_yoy || 0
  const rentGrowth3yr = fundamentals.rent_growth_3yr_cagr || rentGrowth
  
  // Strong rent growth = higher score
  let score = Math.max(0, Math.min(100, 50 + (rentGrowth * 10)))
  
  // Bonus for consistent growth
  if (Math.abs(rentGrowth - rentGrowth3yr) < 2) {
    score += 10
  }
  
  const impact: 'positive' | 'negative' | 'neutral' = rentGrowth > 3 ? 'positive' : rentGrowth < 0 ? 'negative' : 'neutral'
  
  return {
    factor: 'Rent Growth',
    score: Math.round(score),
    weight: 0.20,
    impact,
    explanation: `Current rent growth of ${rentGrowth.toFixed(1)}% annually. ${
      rentGrowth > 5 ? 'Strong growth supports income expansion and asset appreciation.' :
      rentGrowth > 2 ? 'Moderate growth provides steady income increases.' :
      rentGrowth >= 0 ? 'Flat growth indicates market maturity or headwinds.' :
      'Declining rents signal oversupply or economic stress.'
    }`
  }
}

function calculateVacancyDriver(fundamentals: any): DriverResult {
  const vacancy = fundamentals.vacancy_rate || 8
  const vacancyTrend = fundamentals.vacancy_trend || 0
  
  // Lower vacancy = higher score
  let score = Math.max(0, Math.min(100, 100 - (vacancy * 8)))
  
  // Adjust for trend
  if (vacancyTrend < -0.5) score += 15 // Improving
  else if (vacancyTrend > 0.5) score -= 15 // Deteriorating
  
  const impact: 'positive' | 'negative' | 'neutral' = vacancy < 6 ? 'positive' : vacancy > 12 ? 'negative' : 'neutral'
  
  return {
    factor: 'Vacancy Rate',
    score: Math.round(score),
    weight: 0.15,
    impact,
    explanation: `Market vacancy at ${vacancy.toFixed(1)}% ${
      vacancyTrend < -0.5 ? 'and improving' :
      vacancyTrend > 0.5 ? 'and rising' : 'and stable'
    }. ${
      vacancy < 5 ? 'Tight market supports rental rate power and occupancy.' :
      vacancy < 8 ? 'Balanced market with reasonable availability.' :
      vacancy < 12 ? 'Elevated vacancy may pressure rents and concessions.' :
      'High vacancy indicates oversupply and competitive leasing environment.'
    }`
  }
}

function calculateSupplyDemandDriver(fundamentals: any): DriverResult {
  const construction = fundamentals.construction_pipeline || 5
  const absorption = fundamentals.absorption_12m || 0
  const netDemand = fundamentals.net_demand_12m || absorption
  
  // Strong absorption, limited supply = higher score
  let score = 50
  
  // Demand component (40% of score)
  if (netDemand > 0) score += Math.min(20, netDemand * 4)
  else score += Math.max(-20, netDemand * 4)
  
  // Supply component (40% of score)
  if (construction < 3) score += 20
  else if (construction < 6) score += 10
  else if (construction > 10) score -= 20
  else score -= 10
  
  const impact: 'positive' | 'negative' | 'neutral' = netDemand > construction ? 'positive' : netDemand < construction * 0.5 ? 'negative' : 'neutral'
  
  return {
    factor: 'Supply/Demand Balance',
    score: Math.max(0, Math.min(100, Math.round(score))),
    weight: 0.15,
    impact,
    explanation: `Net demand of ${netDemand.toFixed(1)}% vs ${construction.toFixed(1)}% under construction. ${
      netDemand > construction ? 'Demand exceeds new supply, supporting rent growth.' :
      netDemand > construction * 0.7 ? 'Balanced supply-demand dynamics.' :
      'Supply growth outpacing demand may pressure fundamentals.'
    }`
  }
}

function calculateCapRateSpreadDriver(macroData: any, fundamentals: any): DriverResult {
  const tenYear = macroData.treasury_10yr || 4.5
  const creditSpread = macroData.credit_spread_bbb || 1.2
  const capRate = fundamentals.cap_rate_current || 6.0
  
  const riskFreeRate = tenYear
  const spread = capRate - riskFreeRate
  
  // Wider spreads = higher score (better compensation for risk)
  let score = Math.max(0, Math.min(100, (spread - 1) * 25 + 50))
  
  const impact: 'positive' | 'negative' | 'neutral' = spread > 2 ? 'positive' : spread < 1 ? 'negative' : 'neutral'
  
  return {
    factor: 'Cap Rate Spreads',
    score: Math.round(score),
    weight: 0.10,
    impact,
    explanation: `Cap rate spread over 10-year Treasury: ${spread.toFixed(0)}bps. ${
      spread > 250 ? 'Wide spreads provide attractive risk premium.' :
      spread > 150 ? 'Moderate spreads offer reasonable compensation.' :
      'Tight spreads suggest limited upside potential.'
    }`
  }
}

function calculateLiquidityDriver(fundamentals: any): DriverResult {
  const salesVolume = fundamentals.sales_volume_12m || 50
  const salesVolumeChg = fundamentals.sales_volume_change_yoy || 0
  const avgDaysOnMarket = fundamentals.avg_days_on_market || 120
  
  // Higher volume, shorter marketing time = higher score
  let score = 50
  
  score += Math.min(25, (salesVolume - 50) * 0.5)
  score += Math.min(15, salesVolumeChg * 2)
  score += Math.min(10, (180 - avgDaysOnMarket) * 0.1)
  
  const impact: 'positive' | 'negative' | 'neutral' = 
    salesVolume > 70 && avgDaysOnMarket < 100 ? 'positive' : 
    salesVolume < 30 || avgDaysOnMarket > 180 ? 'negative' : 'neutral'
  
  return {
    factor: 'Market Liquidity',
    score: Math.max(0, Math.min(100, Math.round(score))),
    weight: 0.10,
    impact,
    explanation: `Sales volume index: ${salesVolume}, average ${avgDaysOnMarket} days on market. ${
      salesVolume > 80 ? 'High transaction volume indicates strong liquidity.' :
      salesVolume > 50 ? 'Moderate transaction activity.' :
      'Limited transaction volume may indicate pricing or financing challenges.'
    }`
  }
}

function calculateMarketSentimentDriver(fundamentals: any): DriverResult {
  const investorSentiment = fundamentals.investor_sentiment || 50
  const institutionalActivity = fundamentals.institutional_activity || 50
  const developmentStarts = fundamentals.development_starts || 50
  
  // Higher sentiment = higher score
  const score = (investorSentiment + institutionalActivity + developmentStarts) / 3
  
  const impact: 'positive' | 'negative' | 'neutral' = score > 70 ? 'positive' : score < 30 ? 'negative' : 'neutral'
  
  return {
    factor: 'Market Sentiment',
    score: Math.round(score),
    weight: 0.05,
    impact,
    explanation: `Market sentiment composite: ${score.toFixed(0)}/100. ${
      score > 75 ? 'Strong optimism driving investment activity.' :
      score > 50 ? 'Neutral sentiment with selective investment.' :
      score > 25 ? 'Cautious sentiment limiting new investment.' :
      'Pessimistic outlook restraining market participation.'
    }`
  }
}

// ===== TREND ANALYSIS =====

function getInterestRateTrend(macroData: any): 'rising' | 'falling' | 'stable' {
  const current = macroData.fed_funds_rate || 5.25
  const sixMonthsAgo = macroData.fed_funds_rate_6m || current
  
  if (current > sixMonthsAgo + 0.25) return 'rising'
  if (current < sixMonthsAgo - 0.25) return 'falling'
  return 'stable'
}

function getRentGrowthTrend(fundamentals: any): 'rising' | 'falling' | 'stable' {
  const current = fundamentals.rent_growth_yoy || 0
  const trailing = fundamentals.rent_growth_trailing_12m || current
  
  if (current > trailing + 1) return 'rising'
  if (current < trailing - 1) return 'falling'
  return 'stable'
}

function getVacancyTrend(fundamentals: any): 'rising' | 'falling' | 'stable' {
  const trend = fundamentals.vacancy_trend || 0
  
  if (trend > 0.5) return 'rising'
  if (trend < -0.5) return 'falling'
  return 'stable'
}

function getCapRateSpreadTrend(macroData: any, fundamentals: any): 'rising' | 'falling' | 'stable' {
  const trendBps = fundamentals.cap_rate_trend || 0
  
  if (trendBps > 25) return 'rising'
  if (trendBps < -25) return 'falling'
  return 'stable'
}

// ===== HELPER FUNCTIONS =====

function getMTSGrade(score: number): 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D' {
  if (score >= 95) return 'A+'
  if (score >= 90) return 'A'
  if (score >= 85) return 'B+'
  if (score >= 80) return 'B'
  if (score >= 70) return 'C+'
  if (score >= 60) return 'C'
  return 'D'
}

function generateRecommendations(score: number, drivers: any[], marketConditions: any): string[] {
  const recommendations: string[] = []
  
  // Score-based recommendations
  if (score >= 80) {
    recommendations.push('Strong market timing - consider accelerating acquisition timeline')
    recommendations.push('Market conditions favor both income and appreciation potential')
  } else if (score >= 60) {
    recommendations.push('Reasonable market entry point with selective opportunities')
    recommendations.push('Focus on high-quality assets with defensive characteristics')
  } else if (score >= 40) {
    recommendations.push('Cautious approach recommended - wait for better entry points')
    recommendations.push('Consider counter-cyclical strategies or distressed opportunities')
  } else {
    recommendations.push('Poor market timing - delay non-essential acquisitions')
    recommendations.push('Focus on capital preservation and defensive positioning')
  }
  
  // Interest rate specific
  if (marketConditions.interest_rates.score < 40) {
    recommendations.push('High interest rates: Focus on all-cash deals or assume existing financing')
  }
  
  // Rent growth specific
  if (marketConditions.rent_growth.score > 80) {
    recommendations.push('Strong rent growth: Prioritize properties with lease roll-over upside')
  } else if (marketConditions.rent_growth.score < 40) {
    recommendations.push('Weak rent growth: Focus on value-add and cost reduction opportunities')
  }
  
  // Vacancy specific
  if (marketConditions.vacancy.score > 80) {
    recommendations.push('Low vacancy environment: Push market rents and minimize concessions')
  } else if (marketConditions.vacancy.score < 40) {
    recommendations.push('High vacancy: Budget for tenant improvements and leasing costs')
  }
  
  return recommendations.slice(0, 5) // Limit to top 5 recommendations
}

async function fetchCurrentMacroData(supabase: any) {
  // In production, this would fetch from your macro data tables
  // For now, return default values that would typically come from FRED API
  return {
    fed_funds_rate: 5.25,
    fed_funds_rate_6m: 5.00,
    treasury_10yr: 4.50,
    credit_spread_bbb: 1.20,
    inflation_cpi: 3.2,
    unemployment_rate: 3.8,
    as_of: new Date().toISOString()
  }
}
