/**
 * ===== PROPERTY SCORING SERVICE =====
 * Computes CapSight Deal Score, MTS (Market Tension Score), and property classifications
 */

import { getIngestionConfig } from './ingestion-config'
import type { 
  CapsightProperty, 
  PropertyFeatures, 
  ValuationResult,
  PropertyScores,
  MarketFundamentals,
  EstimatedNOI
} from './ingestion-types'

export class PropertyScoringService {
  private config = getIngestionConfig()
  private readonly SCORING_MODEL_VERSION = '1.0.0'
  
  async scoreProperties(
    properties: CapsightProperty[], 
    features: PropertyFeatures[], 
    valuations: ValuationResult[]
  ): Promise<PropertyScores[]> {
    console.log(`🎯 Computing CapSight scores for ${properties.length} properties...`)
    
    const scores: PropertyScores[] = []
    const featureMap = new Map(features.map(f => [f.property_id, f]))
    const valuationMap = new Map(valuations.map(v => [v.property_id, v]))
    
    for (const property of properties) {
      try {
        const propertyFeatures = featureMap.get(property.id)
        const valuation = valuationMap.get(property.id)
        
        if (!propertyFeatures || !valuation) {
          console.warn(`⚠️ Missing data for property ${property.id}, skipping scoring`)
          continue
        }
        
        const score = this.computePropertyScore(property, propertyFeatures, valuation)
        scores.push(score)
        
      } catch (error) {
        console.error(`❌ Failed to score property ${property.id}:`, error)
      }
    }
    
    console.log(`🎯 Scoring complete: ${scores.length}/${properties.length} properties scored`)
    return scores
  }
  
  private computePropertyScore(
    property: CapsightProperty, 
    features: PropertyFeatures, 
    valuation: ValuationResult
  ): PropertyScores {
    
    // ===== DEAL SCORE COMPUTATION =====
    const dealScore = this.computeDealScore(property, features, valuation)
    
    // ===== MTS (MARKET TENSION SCORE) COMPUTATION =====
    const mtsScore = this.computeMTSScore(property, features, valuation)
    
    // ===== YIELD SIGNAL COMPUTATION =====
    const yieldSignal = this.computeYieldSignal(property, features, valuation)
    
    // ===== MACRO SPREAD COMPUTATION =====
    const macroSpread = this.computeMacroSpread(property, features)
    
    // ===== PROPERTY CLASSIFICATION =====
    const classification = this.classifyProperty(dealScore, mtsScore, yieldSignal)
    
    // ===== CONFIDENCE SCORING =====
    const confidence = this.computeConfidence(property, features, valuation)
    
    return {
      property_id: property.id,
      deal_score: Math.round(dealScore * 100) / 100,
      mts_score: Math.round(mtsScore * 100) / 100,
      yield_signal: Math.round(yieldSignal * 100) / 100,
      macro_spread: macroSpread ? Math.round(macroSpread * 10000) / 10000 : undefined,
      classification,
      confidence: Math.round(confidence * 100) / 100,
      scoring_model_version: this.SCORING_MODEL_VERSION,
      created_at: new Date().toISOString()
    }
  }
  
  // ===== DEAL SCORE: Value opportunity relative to market =====
  
  private computeDealScore(
    property: CapsightProperty, 
    features: PropertyFeatures, 
    valuation: ValuationResult
  ): number {
    let score = 50.0 // Base score (neutral)
    
    // Factor 1: Value vs Assessment (30% weight)
    if (property.assessed_value && valuation.current_value.point) {
      const valueToAssessment = valuation.current_value.point / property.assessed_value
      if (valueToAssessment > 1.2) score += 15 // Significantly undervalued by assessor
      else if (valueToAssessment > 1.1) score += 8
      else if (valueToAssessment < 0.9) score -= 8 // Overvalued
      else if (valueToAssessment < 0.8) score -= 15
    }
    
    // Factor 2: Cap Rate Spread to Market (25% weight)
    if (features.estimated_noi && valuation.current_value.point) {
      const impliedCapRate = features.estimated_noi.annual_noi / valuation.current_value.point
      const marketCapRate = features.market_fundamentals.avg_cap_rate / 100
      const capRateSpread = impliedCapRate - marketCapRate
      
      if (capRateSpread > 0.015) score += 12 // 150+ bps above market
      else if (capRateSpread > 0.01) score += 8 // 100+ bps above market
      else if (capRateSpread < -0.01) score -= 8 // 100+ bps below market
      else if (capRateSpread < -0.015) score -= 12 // 150+ bps below market
    }
    
    // Factor 3: Appreciation Potential (20% weight)
    const appreciationForecast = features.market_fundamentals.appreciation_forecast_1yr
    if (appreciationForecast > 5.0) score += 10 // Strong appreciation expected
    else if (appreciationForecast > 3.0) score += 6
    else if (appreciationForecast < 1.0) score -= 6 // Weak appreciation
    else if (appreciationForecast < 0) score -= 10 // Depreciation expected
    
    // Factor 4: Market Fundamentals (15% weight)
    const vacancyRate = features.market_fundamentals.vacancy_rate
    if (vacancyRate < 8) score += 6 // Tight market
    else if (vacancyRate < 12) score += 3
    else if (vacancyRate > 18) score -= 6 // Oversupplied market
    else if (vacancyRate > 25) score -= 9
    
    // Factor 5: Risk Adjustments (10% weight)
    if (features.flood_zone && features.flood_zone.flood_risk_level === 'high') score -= 5
    if (features.broadband_served && !features.broadband_served.fiber_available) score -= 2
    if (property.year_built && property.year_built < 1980) score -= 3 // Older building risk
    
    return Math.max(0, Math.min(100, score))
  }
  
  // ===== MTS: Market Tension Score (supply/demand imbalance) =====
  
  private computeMTSScore(
    property: CapsightProperty, 
    features: PropertyFeatures, 
    valuation: ValuationResult
  ): number {
    let score = 50.0 // Base score (equilibrium)
    
    // Factor 1: Vacancy Rate vs Historical (35% weight)
    const currentVacancy = features.market_fundamentals.vacancy_rate
    const historicalAvgVacancy = 12.0 // Long-term average (~12%)
    const vacancyDelta = historicalAvgVacancy - currentVacancy
    score += vacancyDelta * 2.5 // 1% below avg = +2.5 points
    
    // Factor 2: Supply Pipeline Impact (25% weight)
    if (features.market_fundamentals.supply_pipeline_sf && property.building_sf) {
      const marketSize = 50000000 // Estimate 50M SF market
      const supplyRatio = features.market_fundamentals.supply_pipeline_sf / marketSize
      if (supplyRatio > 0.15) score -= 12 // Heavy supply coming
      else if (supplyRatio > 0.10) score -= 8
      else if (supplyRatio < 0.05) score += 8 // Limited supply
      else if (supplyRatio < 0.02) score += 12
    }
    
    // Factor 3: Absorption vs Deliveries (25% weight)
    if (features.market_fundamentals.absorption_rate_sf_mo && features.market_fundamentals.supply_pipeline_sf) {
      const monthsToAbsorb = features.market_fundamentals.supply_pipeline_sf / (features.market_fundamentals.absorption_rate_sf_mo * 12)
      if (monthsToAbsorb < 12) score += 10 // Supply absorbed quickly
      else if (monthsToAbsorb < 18) score += 5
      else if (monthsToAbsorb > 36) score -= 10 // Oversupply
      else if (monthsToAbsorb > 48) score -= 15
    }
    
    // Factor 4: Demographics and Employment (15% weight)
    if (features.demographics) {
      const populationGrowth = features.demographics.population_trend_1yr
      const employmentGrowth = features.demographics.employment_yoy
      
      if (populationGrowth > 2.0 && employmentGrowth > 1.5) score += 8 // Strong fundamentals
      else if (populationGrowth > 1.0 && employmentGrowth > 0.5) score += 4
      else if (populationGrowth < 0 || employmentGrowth < -1.0) score -= 6 // Declining area
    }
    
    return Math.max(0, Math.min(100, score))
  }
  
  // ===== YIELD SIGNAL: Income generation potential =====
  
  private computeYieldSignal(
    property: CapsightProperty, 
    features: PropertyFeatures, 
    valuation: ValuationResult
  ): number {
    let score = 50.0 // Base score
    
    if (!features.estimated_noi || !valuation.current_value.point) {
      return score // Return neutral if missing NOI data
    }
    
    const currentYield = features.estimated_noi.annual_noi / valuation.current_value.point
    const marketCapRate = features.market_fundamentals.avg_cap_rate / 100
    
    // Factor 1: Current Yield vs Market (40% weight)
    const yieldSpread = currentYield - marketCapRate
    if (yieldSpread > 0.02) score += 20 // 200+ bps above market
    else if (yieldSpread > 0.01) score += 12 // 100+ bps above market
    else if (yieldSpread < -0.01) score -= 12 // 100+ bps below market
    else if (yieldSpread < -0.02) score -= 20 // 200+ bps below market
    
    // Factor 2: NOI Growth Potential (30% weight)
    const marketRentGrowth = features.market_fundamentals.appreciation_forecast_1yr / 2 // Assume rent grows at half of appreciation
    if (marketRentGrowth > 3.0) score += 12 // Strong rent growth expected
    else if (marketRentGrowth > 2.0) score += 8
    else if (marketRentGrowth < 0.5) score -= 8 // Weak rent growth
    else if (marketRentGrowth < 0) score -= 12 // Rent decline expected
    
    // Factor 3: Operating Efficiency (20% weight)
    const opexRatio = features.estimated_noi.operating_expenses / features.estimated_noi.gross_income
    if (opexRatio < 0.30) score += 8 // Efficient operations
    else if (opexRatio < 0.35) score += 4
    else if (opexRatio > 0.50) score -= 8 // High opex
    else if (opexRatio > 0.60) score -= 12
    
    // Factor 4: Vacancy Risk (10% weight)
    const vacancyRate = features.estimated_noi.vacancy_rate_applied / 100
    const marketVacancy = features.market_fundamentals.vacancy_rate / 100
    const vacancyDelta = marketVacancy - vacancyRate
    score += vacancyDelta * 25 // 1% better vacancy = +2.5 points
    
    return Math.max(0, Math.min(100, score))
  }
  
  // ===== MACRO SPREAD: Treasury spread analysis =====
  
  private computeMacroSpread(
    property: CapsightProperty, 
    features: PropertyFeatures
  ): number | null {
    if (!features.estimated_noi) return null
    
    const propertyCapRate = features.market_fundamentals.avg_cap_rate / 100
    const riskFreeRate = 0.045 // Assume 4.5% 10-year Treasury (would fetch real rate)
    const creditSpread = 0.015 // Assume 150bps credit spread for CRE
    
    const macroSpread = propertyCapRate - riskFreeRate - creditSpread
    return macroSpread
  }
  
  // ===== PROPERTY CLASSIFICATION =====
  
  private classifyProperty(dealScore: number, mtsScore: number, yieldSignal: number): string {
    const compositeScore = (dealScore + mtsScore + yieldSignal) / 3
    
    if (compositeScore >= 75) return 'A' // Premium opportunities
    else if (compositeScore >= 65) return 'B+' // Strong opportunities
    else if (compositeScore >= 55) return 'B' // Good opportunities
    else if (compositeScore >= 45) return 'B-' // Fair opportunities
    else if (compositeScore >= 35) return 'C' // Below-average opportunities
    else return 'D' // Poor opportunities
  }
  
  // ===== CONFIDENCE SCORING =====
  
  private computeConfidence(
    property: CapsightProperty, 
    features: PropertyFeatures, 
    valuation: ValuationResult
  ): number {
    let confidence = 50.0 // Base confidence
    
    // Data completeness (40% of confidence)
    let dataPoints = 0
    let totalPoints = 10
    
    if (property.building_sf) dataPoints++
    if (property.year_built) dataPoints++
    if (property.assessed_value) dataPoints++
    if (property.rent_psf_yr) dataPoints++
    if (property.opex_psf_yr) dataPoints++
    if (features.demographics) dataPoints++
    if (features.estimated_noi) dataPoints++
    if (features.flood_zone) dataPoints++
    if (features.broadband_served) dataPoints++
    if (valuation.current_value.confidence > 0.7) dataPoints++
    
    confidence += (dataPoints / totalPoints) * 20 // 0-20 points for data completeness
    
    // Valuation confidence (30% of confidence)
    confidence += valuation.current_value.confidence * 15 // 0-15 points from valuation model
    
    // Market data freshness (20% of confidence)
    const marketDataAge = this.calculateDataAge(features.market_fundamentals.as_of)
    if (marketDataAge <= 30) confidence += 10 // Fresh data
    else if (marketDataAge <= 90) confidence += 5
    else if (marketDataAge > 365) confidence -= 10 // Stale data
    
    // Consistency checks (10% of confidence)
    if (this.validateScoreConsistency(property, features, valuation)) {
      confidence += 5
    } else {
      confidence -= 5
    }
    
    return Math.max(0, Math.min(100, confidence))
  }
  
  // ===== HELPER METHODS =====
  
  private calculateDataAge(asOfDate: string): number {
    const dataDate = new Date(asOfDate)
    const now = new Date()
    return Math.floor((now.getTime() - dataDate.getTime()) / (1000 * 60 * 60 * 24))
  }
  
  private validateScoreConsistency(
    property: CapsightProperty, 
    features: PropertyFeatures, 
    valuation: ValuationResult
  ): boolean {
    // Basic consistency checks
    if (features.estimated_noi && valuation.current_value.point) {
      const impliedCapRate = features.estimated_noi.annual_noi / valuation.current_value.point
      // Cap rate should be reasonable (2% - 15%)
      if (impliedCapRate < 0.02 || impliedCapRate > 0.15) return false
    }
    
    // Building SF should be reasonable for asset type
    if (property.building_sf && property.building_sf < 1000) return false // Minimum commercial size
    if (property.building_sf && property.building_sf > 5000000) return false // Maximum reasonable size
    
    // Year built should be reasonable
    if (property.year_built && (property.year_built < 1800 || property.year_built > new Date().getFullYear())) return false
    
    return true
  }
}

// Export singleton instance
export const scoringService = new PropertyScoringService()
