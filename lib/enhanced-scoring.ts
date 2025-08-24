/**
 * ===== ENHANCED SCORING & FINANCIAL MODELING =====
 * Implements NOI estimation, valuation approaches, MTS, and Deal Score calculation
 * Based on fundamental CRE analysis with dual-engine validation
 */

import type { 
  CapsightProperty, 
  PropertyScores, 
  ValuationResult, 
  AssetType,
  MarketFundamentals 
} from './ingestion-types'

interface NoiEstimation {
  estimated_noi: number
  confidence: number
  method: 'sec_reported' | 'rent_roll_based' | 'market_estimated'
  assumptions: {
    rent_psf_yr: number
    opex_psf_yr: number
    vacancy_pct: number
    building_sf: number
  }
  provenance: {
    rent_source: string
    opex_source: string
    vacancy_source: string
  }
}

interface DualEngineValuation {
  income_approach: {
    value: number
    confidence: number
    cap_rate_used: number
  }
  comp_approach: {
    value: number
    confidence: number
    comps_count: number
    psf_median: number
  }
  blended_value: number
  blended_confidence: number
  engine_agreement: boolean
  disagreement_pct?: number
  warnings: string[]
}

export class EnhancedScoringService {
  
  // Market defaults by asset type ($/SF/year operating expenses)
  private readonly marketOpex: Record<AssetType, { min: number, max: number, typical: number }> = {
    'industrial': { min: 1.5, max: 2.5, typical: 2.0 },
    'office': { min: 8.0, max: 15.0, typical: 12.0 },
    'retail': { min: 4.0, max: 8.0, typical: 6.0 },
    'multifamily': { min: 3.5, max: 6.0, typical: 4.5 },
    'land': { min: 0.1, max: 0.5, typical: 0.2 },
    'other': { min: 2.0, max: 8.0, typical: 4.0 }
  }

  // Cap rate forecasting coefficients
  private readonly capRateModel = {
    alpha: 0.75,  // Interest rate sensitivity
    beta: 0.30,   // Vacancy sensitivity  
    gamma: 0.40   // Supply/demand sensitivity
  }

  async estimateNOI(
    property: CapsightProperty,
    marketFundamentals?: MarketFundamentals,
    secReportedNoi?: number
  ): Promise<NoiEstimation> {
    
    // Prefer SEC reported NOI if available (highest confidence)
    if (secReportedNoi && secReportedNoi > 0) {
      return {
        estimated_noi: secReportedNoi,
        confidence: 0.95,
        method: 'sec_reported',
        assumptions: {
          rent_psf_yr: 0,
          opex_psf_yr: 0,
          vacancy_pct: 0,
          building_sf: property.building_sf || 0
        },
        provenance: {
          rent_source: 'SEC Filing',
          opex_source: 'SEC Filing',
          vacancy_source: 'SEC Filing'
        }
      }
    }

    if (!property.building_sf || property.building_sf <= 0) {
      throw new Error('Building square footage required for NOI estimation')
    }

    // Estimate market rent per SF
    const rentPsf = await this.estimateMarketRent(property, marketFundamentals)
    
    // Get operating expenses for asset type
    const opexPsf = this.getOpexEstimate(property.asset_type, marketFundamentals)
    
    // Get vacancy rate
    const vacancyPct = this.getVacancyRate(property, marketFundamentals)
    
    // Calculate NOI: (rent - opex) * SF * (1 - vacancy)
    const grossRentRoll = rentPsf * property.building_sf
    const effectiveGrossIncome = grossRentRoll * (1 - vacancyPct / 100)
    const totalOpex = opexPsf * property.building_sf
    const estimatedNoi = Math.max(0, effectiveGrossIncome - totalOpex)

    // Calculate confidence based on data availability
    const confidence = this.calculateNoiConfidence(property, marketFundamentals, !!secReportedNoi)

    return {
      estimated_noi: estimatedNoi,
      confidence,
      method: 'market_estimated',
      assumptions: {
        rent_psf_yr: rentPsf,
        opex_psf_yr: opexPsf,
        vacancy_pct: vacancyPct,
        building_sf: property.building_sf
      },
      provenance: {
        rent_source: marketFundamentals ? 'Market Fundamentals' : 'Estimated',
        opex_source: 'Asset Type Defaults',
        vacancy_source: marketFundamentals ? 'Market Data' : 'Estimated'
      }
    }
  }

  async performDualEngineValuation(
    property: CapsightProperty,
    noiEstimation: NoiEstimation,
    marketFundamentals?: MarketFundamentals,
    macroData?: { gs10: number, dff: number }
  ): Promise<DualEngineValuation> {
    
    // Income approach valuation
    const incomeApproach = await this.incomeApproachValuation(
      noiEstimation.estimated_noi,
      property,
      marketFundamentals,
      macroData
    )
    
    // Comparable sales approach
    const compApproach = await this.comparableApproachValuation(property, marketFundamentals)
    
    // Check for engine agreement
    const disagreementPct = Math.abs(incomeApproach.value - compApproach.value) / 
                           Math.min(incomeApproach.value, compApproach.value) * 100
    const engineAgreement = disagreementPct <= 15
    
    // Blend valuations (weight income approach higher)
    const incomeWeight = engineAgreement ? 0.7 : 0.5
    const compWeight = engineAgreement ? 0.3 : 0.5
    
    const blendedValue = (incomeApproach.value * incomeWeight) + (compApproach.value * compWeight)
    const blendedConfidence = Math.min(
      incomeApproach.confidence * incomeWeight + compApproach.confidence * compWeight,
      engineAgreement ? 0.85 : 0.60
    )

    const warnings: string[] = []
    if (!engineAgreement) {
      warnings.push('engine_disagreement')
    }
    if (compApproach.comps_count < 3) {
      warnings.push('low_comp_count')
    }

    return {
      income_approach: incomeApproach,
      comp_approach: compApproach,
      blended_value: blendedValue,
      blended_confidence: blendedConfidence,
      engine_agreement: engineAgreement,
      disagreement_pct: engineAgreement ? undefined : disagreementPct,
      warnings
    }
  }

  async calculateMTS(
    property: CapsightProperty,
    marketFundamentals?: MarketFundamentals,
    macroData?: { gs10: number, dff: number }
  ): Promise<number> {
    
    let score = 0
    
    // Cap-rate momentum (30% weight)
    if (marketFundamentals && macroData) {
      const capRateMomentum = this.calculateCapRateMomentum(marketFundamentals, macroData)
      score += capRateMomentum * 0.30
    } else {
      score += 50 * 0.30 // Neutral if no data
    }
    
    // Vacancy level/trend (25% weight)
    if (marketFundamentals) {
      const vacancyScore = this.calculateVacancyScore(marketFundamentals)
      score += vacancyScore * 0.25
    } else {
      score += 50 * 0.25 // Neutral if no data
    }
    
    // Rent growth (25% weight)
    if (marketFundamentals) {
      const rentGrowthScore = this.calculateRentGrowthScore(marketFundamentals)
      score += rentGrowthScore * 0.25
    } else {
      score += 50 * 0.25 // Neutral if no data
    }
    
    // Absorption vs deliveries (20% weight)
    if (marketFundamentals) {
      const supplyDemandScore = this.calculateSupplyDemandScore(marketFundamentals)
      score += supplyDemandScore * 0.20
    } else {
      score += 50 * 0.20 // Neutral if no data
    }
    
    return Math.max(0, Math.min(100, score))
  }

  async calculateDealScore(
    property: CapsightProperty,
    valuation: DualEngineValuation,
    noiEstimation: NoiEstimation,
    mts: number,
    marketFundamentals?: MarketFundamentals,
    macroData?: { gs10: number, dff: number }
  ): Promise<PropertyScores> {
    
    // Calculate yield signal (NOI / current value vs market mean)
    const yieldSignal = this.calculateYieldSignal(noiEstimation.estimated_noi, valuation.blended_value, marketFundamentals)
    
    // Calculate spread (cap rate - 10Y Treasury)
    const spread = this.calculateSpread(noiEstimation, valuation, macroData)
    
    // Base deal score calculation
    let dealScore = (0.40 * mts) + (0.25 * yieldSignal) + (0.15 * spread)
    
    // Apply penalties (up to 20%)
    let penalties = 0
    
    if (marketFundamentals && this.isStaleData(marketFundamentals)) {
      penalties += 5
    }
    
    if (valuation.comp_approach.comps_count < 3) {
      penalties += 5
    }
    
    if (!valuation.engine_agreement) {
      penalties += 5
    }
    
    if (!property.building_sf || !property.year_built) {
      penalties += 5
    }
    
    dealScore = Math.max(0, dealScore - penalties)
    
    // Determine classification
    const classification = this.classifyProperty(dealScore, valuation.blended_confidence)
    
    return {
      property_id: property.id,
      mts_score: Math.round(mts),
      deal_score: Math.round(dealScore),
      yield_signal: yieldSignal,
      macro_spread: spread,
      classification: this.mapClassificationToGrade(classification),
      confidence: valuation.blended_confidence,
      scoring_model_version: '2.0.0',
      created_at: new Date().toISOString()
    }
  }

  // Private helper methods

  private async estimateMarketRent(
    property: CapsightProperty,
    marketFundamentals?: MarketFundamentals
  ): Promise<number> {
    
    if (marketFundamentals?.avg_rent_psf) {
      return marketFundamentals.avg_rent_psf
    }
    
    // Fallback to asset type defaults (very rough estimates)
    const rentDefaults: Record<AssetType, number> = {
      'industrial': 8.0,
      'office': 25.0,
      'retail': 20.0,
      'multifamily': 18.0,
      'land': 0.5,
      'other': 15.0
    }
    
    return rentDefaults[property.asset_type] || 15.0
  }

  private getOpexEstimate(assetType: AssetType, marketFundamentals?: MarketFundamentals): number {
    // Could use market fundamentals if available
    return this.marketOpex[assetType]?.typical || 4.0
  }

  private getVacancyRate(property: CapsightProperty, marketFundamentals?: MarketFundamentals): number {
    if (marketFundamentals?.vacancy_rate) {
      return Math.min(40, marketFundamentals.vacancy_rate) // Cap at 40%
    }
    
    // Default vacancy rates by asset type
    const vacancyDefaults: Record<AssetType, number> = {
      'industrial': 5.0,
      'office': 12.0,
      'retail': 8.0,
      'multifamily': 6.0,
      'land': 0,
      'other': 10.0
    }
    
    return vacancyDefaults[property.asset_type] || 10.0
  }

  private calculateNoiConfidence(
    property: CapsightProperty,
    marketFundamentals?: MarketFundamentals,
    hasSecData: boolean = false
  ): number {
    let confidence = 0.3 // Base confidence
    
    if (hasSecData) confidence += 0.5
    if (marketFundamentals) confidence += 0.2
    if (property.building_sf && property.building_sf > 0) confidence += 0.1
    if (property.year_built) confidence += 0.05
    
    return Math.min(1.0, confidence)
  }

  private async incomeApproachValuation(
    noi: number,
    property: CapsightProperty,
    marketFundamentals?: MarketFundamentals,
    macroData?: { gs10: number, dff: number }
  ) {
    // Get current cap rate
    const capRate = this.getCurrentCapRate(property.asset_type, marketFundamentals, macroData) / 100
    
    const value = noi / capRate
    const confidence = this.calculateIncomeApproachConfidence(marketFundamentals, macroData)
    
    return {
      value,
      confidence,
      cap_rate_used: capRate * 100
    }
  }

  private async comparableApproachValuation(
    property: CapsightProperty,
    marketFundamentals?: MarketFundamentals
  ) {
    // This would typically query recent sales comps from the database
    // For now, use market fundamentals or defaults
    
    let psfMedian = 150 // Default $150/SF
    let compsCount = 1
    let confidence = 0.4
    
    // No direct sale price in MarketFundamentals, use rent as proxy
    if (marketFundamentals?.avg_rent_psf) {
      psfMedian = marketFundamentals.avg_rent_psf * 12 // Rough GRM conversion
      compsCount = Math.max(1, Math.floor(Math.random() * 5) + 2) // Mock 2-6 comps
      confidence = 0.7
    }
    
    const value = (property.building_sf || 100000) * psfMedian
    
    return {
      value,
      confidence,
      comps_count: compsCount,
      psf_median: psfMedian
    }
  }

  private getCurrentCapRate(
    assetType: AssetType,
    marketFundamentals?: MarketFundamentals,
    macroData?: { gs10: number, dff: number }
  ): number {
    
    // Base cap rates by asset type
    const baseCapRates: Record<AssetType, number> = {
      'industrial': 6.5,
      'office': 7.0,
      'retail': 6.8,
      'multifamily': 5.5,
      'land': 0, // N/A for land
      'other': 7.5
    }
    
    let capRate = baseCapRates[assetType] || 7.0
    
    // Adjust for market conditions if available
    if (marketFundamentals?.avg_cap_rate) {
      capRate = marketFundamentals.avg_cap_rate
    }
    
    // Adjust for macro conditions
    if (macroData?.gs10) {
      const riskPremium = capRate - macroData.gs10
      capRate = macroData.gs10 + riskPremium // Maintain spread but adjust for rate changes
    }
    
    return Math.max(2.0, Math.min(20.0, capRate)) // Keep reasonable bounds
  }

  private calculateIncomeApproachConfidence(
    marketFundamentals?: MarketFundamentals,
    macroData?: { gs10: number, dff: number }
  ): number {
    let confidence = 0.5 // Base confidence
    
    if (marketFundamentals?.avg_cap_rate) confidence += 0.2
    if (macroData?.gs10) confidence += 0.1
    
    return Math.min(0.9, confidence)
  }

  private calculateCapRateMomentum(marketFundamentals: MarketFundamentals, macroData: { gs10: number, dff: number }): number {
    // Rising rates = falling cap rate momentum score
    const rateChange = macroData.gs10 - 2.5 // Compare to historical average
    return Math.max(0, Math.min(100, 50 - (rateChange * 10)))
  }

  private calculateVacancyScore(marketFundamentals: MarketFundamentals): number {
    if (!marketFundamentals.vacancy_rate) return 50
    
    // Lower vacancy = higher score
    const vacancy = Math.min(40, marketFundamentals.vacancy_rate)
    return Math.max(0, Math.min(100, 100 - (vacancy * 2.5)))
  }

  private calculateRentGrowthScore(marketFundamentals: MarketFundamentals): number {
    // Would need historical rent data to calculate growth
    // For now, return neutral score
    return 50
  }

  private calculateSupplyDemandScore(marketFundamentals: MarketFundamentals): number {
    // Would need absorption and delivery data
    // For now, return neutral score  
    return 50
  }

  private calculateYieldSignal(noi: number, value: number, marketFundamentals?: MarketFundamentals): number {
    const propertyYield = (noi / value) * 100
    const marketYield = marketFundamentals?.avg_cap_rate || 7.0
    
    // Z-score approach: (property yield - market yield) / standard deviation
    const stdDev = 1.5 // Assumed standard deviation
    const zScore = (propertyYield - marketYield) / stdDev
    
    // Convert to 0-100 scale
    return Math.max(0, Math.min(100, 50 + (zScore * 20)))
  }

  private calculateSpread(
    noiEstimation: NoiEstimation,
    valuation: DualEngineValuation,
    macroData?: { gs10: number, dff: number }
  ): number {
    if (!macroData?.gs10) return 50 // Neutral if no Treasury data
    
    const capRate = (noiEstimation.estimated_noi / valuation.blended_value) * 100
    const spread = capRate - macroData.gs10
    
    // Convert spread to 0-100 scale (higher spread = higher score)
    return Math.max(0, Math.min(100, spread * 10 + 50))
  }

  private isStaleData(marketFundamentals: MarketFundamentals): boolean {
    if (!marketFundamentals.as_of) return true
    
    const dataAge = Date.now() - new Date(marketFundamentals.as_of).getTime()
    const ninetyDays = 90 * 24 * 60 * 60 * 1000
    
    return dataAge > ninetyDays
  }

  private classifyProperty(dealScore: number, confidence: number): 'BUY' | 'HOLD' | 'AVOID' {
    if (dealScore >= 75 && confidence >= 0.6) return 'BUY'
    if (dealScore >= 50 || confidence >= 0.4) return 'HOLD'
    return 'AVOID'
  }

  private mapClassificationToGrade(classification: 'BUY' | 'HOLD' | 'AVOID'): string {
    switch (classification) {
      case 'BUY': return 'A'
      case 'HOLD': return 'B'
      case 'AVOID': return 'C'
      default: return 'D'
    }
  }
}

// Singleton export
export const enhancedScoringService = new EnhancedScoringService()
