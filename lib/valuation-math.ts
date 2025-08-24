/**
 * ===== VALUATION MATH ENGINE =====
 * Correct mathematical formulas for CRE valuation and forecasting
 */

interface ValuationInputs {
  building_sf: number
  rent_psf_yr: number
  opex_psf_yr: number
  vacancy_pct: number
  cap_rate_now_pct: number
  rent_growth_ann_pct: number
  cap_rate_spread_change_bps: number
  vacancy_change_bps: number
  absorption_to_deliveries_ratio: number
}

interface ValuationOutputs {
  noi_current: number
  noi_future_12m: number
  current_value: number
  future_value_12m: number
  cap_rate_forecast_12m: number
  price_per_sf: number
  confidence_factors: {
    data_freshness: number
    comp_count: number
    calculation_certainty: number
  }
}

interface DualEngineResult {
  income_approach_value: number
  sales_comp_value: number
  disagreement_pct: number
  recommended_value: number
  warning?: string
}

/**
 * Model coefficients for cap rate forecasting
 * cap_{t+1} = cap_t + α*ΔMacroSpread + β*ΔVacancy - γ*AbsorptionToDeliveries
 */
const CAP_RATE_MODEL_COEFFICIENTS = {
  alpha_macro_spread: 0.65,    // 65bps cap rate change per 100bps spread change
  beta_vacancy: 0.85,          // 85bps cap rate change per 100bps vacancy change  
  gamma_absorption: 0.25,      // 25bps cap rate reduction per 1.0 absorption ratio
  max_change_bps: 150,         // Cap annual cap rate changes at ±150bps
  model_version: '1.0.0'
}

export class ValuationMathEngine {
  
  /**
   * Calculate Net Operating Income (NOI)
   * Formula: (rent_psf_yr - opex_psf_yr) * building_sf * (1 - vacancy_pct)
   */
  static calculateNOI(building_sf: number, rent_psf_yr: number, opex_psf_yr: number, vacancy_pct: number): number {
    if (building_sf <= 0 || rent_psf_yr <= 0 || vacancy_pct < 0 || vacancy_pct > 0.4) {
      throw new Error('Invalid NOI calculation inputs')
    }
    
    const net_rent_psf = rent_psf_yr - opex_psf_yr
    const occupancy_rate = 1 - vacancy_pct
    const noi = net_rent_psf * building_sf * occupancy_rate
    
    return Math.max(0, noi)
  }
  
  /**
   * Calculate current property value using income approach
   * Formula: NOI / (cap_rate_now_pct / 100)
   */
  static calculateCurrentValue(noi: number, cap_rate_pct: number): number {
    if (noi <= 0 || cap_rate_pct <= 0 || cap_rate_pct > 20) {
      throw new Error('Invalid current value calculation inputs')
    }
    
    return noi / (cap_rate_pct / 100)
  }
  
  /**
   * Calculate future NOI with rent growth
   * Formula: NOI * (1 + rent_growth_ann)^t (t in years)
   */
  static calculateFutureNOI(current_noi: number, rent_growth_ann_pct: number, years: number): number {
    if (current_noi <= 0 || years < 0) {
      throw new Error('Invalid future NOI calculation inputs')
    }
    
    // Cap rent growth at realistic bounds
    const capped_growth = Math.max(-10, Math.min(20, rent_growth_ann_pct)) / 100
    
    return current_noi * Math.pow(1 + capped_growth, years)
  }
  
  /**
   * Forecast cap rate using multi-factor model
   * Formula: cap_{t+1} = cap_t + α*ΔMacroSpread + β*ΔVacancy - γ*AbsorptionToDeliveries
   */
  static forecastCapRate(inputs: {
    current_cap_rate_pct: number
    macro_spread_change_bps: number
    vacancy_change_bps: number
    absorption_to_deliveries_ratio: number
  }): number {
    const { alpha_macro_spread, beta_vacancy, gamma_absorption, max_change_bps } = CAP_RATE_MODEL_COEFFICIENTS
    
    // Calculate each component
    const macro_impact_bps = alpha_macro_spread * (inputs.macro_spread_change_bps / 100)
    const vacancy_impact_bps = beta_vacancy * (inputs.vacancy_change_bps / 100)
    const absorption_impact_bps = gamma_absorption * Math.max(0, inputs.absorption_to_deliveries_ratio - 1.0) * 100
    
    // Total change in basis points
    let total_change_bps = macro_impact_bps + vacancy_impact_bps - absorption_impact_bps
    
    // Cap the change
    total_change_bps = Math.max(-max_change_bps, Math.min(max_change_bps, total_change_bps))
    
    // Apply to current cap rate
    const forecast_cap_rate = inputs.current_cap_rate_pct + (total_change_bps / 100)
    
    // Ensure reasonable bounds
    return Math.max(2.0, Math.min(20.0, forecast_cap_rate))
  }
  
  /**
   * Calculate future property value
   * Formula: NOI_future / (cap_rate_future / 100)
   */
  static calculateFutureValue(future_noi: number, future_cap_rate_pct: number): number {
    return ValuationMathEngine.calculateCurrentValue(future_noi, future_cap_rate_pct)
  }
  
  /**
   * Perform dual-engine valuation check (Income vs Sales Comps)
   */
  static performDualEngineCheck(
    income_approach_value: number,
    comparable_sales: Array<{price_per_sf_usd: number, building_sf: number, sale_price_usd: number}>,
    subject_building_sf: number
  ): DualEngineResult {
    
    if (comparable_sales.length === 0) {
      return {
        income_approach_value,
        sales_comp_value: income_approach_value,
        disagreement_pct: 0,
        recommended_value: income_approach_value,
        warning: 'no_comps_available'
      }
    }
    
    // Calculate sales comp approach value
    const price_per_sf_values = comparable_sales.map(comp => comp.price_per_sf_usd)
    const median_price_per_sf = price_per_sf_values.sort((a, b) => a - b)[Math.floor(price_per_sf_values.length / 2)]
    const sales_comp_value = median_price_per_sf * subject_building_sf
    
    // Calculate disagreement percentage
    const disagreement_pct = Math.abs(income_approach_value - sales_comp_value) / income_approach_value
    
    let recommended_value = income_approach_value
    let warning: string | undefined
    
    // If disagreement > 15%, blend the values and add warning
    if (disagreement_pct > 0.15) {
      // Weighted average (60% income, 40% sales comp)
      recommended_value = (income_approach_value * 0.6) + (sales_comp_value * 0.4)
      warning = 'engine_disagreement'
    }
    
    return {
      income_approach_value,
      sales_comp_value,
      disagreement_pct: disagreement_pct * 100, // Convert to percentage
      recommended_value,
      warning
    }
  }
  
  /**
   * Calculate confidence score based on multiple factors
   */
  static calculateConfidence(factors: {
    comp_count: number
    macro_freshness_days: number
    fundamentals_freshness_days: number
    comps_freshness_days: number
    dual_engine_disagreement_pct: number
    cap_rate_variance_from_market: number
  }): number {
    let confidence = 0.85 // Base confidence
    
    // Reduce confidence for insufficient comps
    if (factors.comp_count < 3) {
      confidence -= 0.25
    } else if (factors.comp_count >= 5) {
      confidence += 0.1
    }
    
    // Reduce confidence for stale data
    if (factors.macro_freshness_days > 7) {
      confidence -= 0.15
    }
    if (factors.fundamentals_freshness_days > 90) {
      confidence -= 0.20
    }
    if (factors.comps_freshness_days > 180) {
      confidence -= 0.15
    }
    
    // Reduce confidence for dual-engine disagreement
    if (factors.dual_engine_disagreement_pct > 15) {
      confidence -= 0.15
    }
    
    // Reduce confidence for cap rate variance
    if (factors.cap_rate_variance_from_market > 1.5) {
      confidence -= 0.10
    }
    
    // Ensure bounds
    return Math.max(0.1, Math.min(1.0, confidence))
  }
  
  /**
   * Calculate valuation range based on confidence
   */
  static calculateValuationRange(point_value: number, confidence_score: number): {low: number, high: number} {
    // Lower confidence = wider range
    const range_factor = (1 - confidence_score) * 0.3 + 0.1 // 10% to 40% range
    
    const low = point_value * (1 - range_factor)
    const high = point_value * (1 + range_factor)
    
    return {
      low: Math.round(low),
      high: Math.round(high)
    }
  }
  
  /**
   * Full valuation calculation
   */
  static calculateFullValuation(inputs: ValuationInputs, comparables: Array<{
    price_per_sf_usd: number
    building_sf: number
    sale_price_usd: number
    cap_rate_pct: number
  }>, freshness: {
    macro_days: number
    fundamentals_days: number
    comps_days: number
  }): ValuationOutputs {
    
    // 1. Calculate current NOI
    const noi_current = this.calculateNOI(
      inputs.building_sf,
      inputs.rent_psf_yr,
      inputs.opex_psf_yr,
      inputs.vacancy_pct
    )
    
    // 2. Calculate current value
    const current_value_income = this.calculateCurrentValue(noi_current, inputs.cap_rate_now_pct)
    
    // 3. Forecast cap rate
    const cap_rate_forecast_12m = this.forecastCapRate({
      current_cap_rate_pct: inputs.cap_rate_now_pct,
      macro_spread_change_bps: inputs.cap_rate_spread_change_bps,
      vacancy_change_bps: inputs.vacancy_change_bps,
      absorption_to_deliveries_ratio: inputs.absorption_to_deliveries_ratio
    })
    
    // 4. Calculate future NOI and value
    const noi_future_12m = this.calculateFutureNOI(noi_current, inputs.rent_growth_ann_pct, 1.0)
    const future_value_12m = this.calculateFutureValue(noi_future_12m, cap_rate_forecast_12m)
    
    // 5. Dual-engine check
    const dualEngineResult = this.performDualEngineCheck(
      current_value_income,
      comparables,
      inputs.building_sf
    )
    
    // 6. Calculate confidence
    const market_cap_rate_avg = comparables.length > 0 
      ? comparables.reduce((sum, comp) => sum + comp.cap_rate_pct, 0) / comparables.length
      : inputs.cap_rate_now_pct
    
    const cap_rate_variance = Math.abs(inputs.cap_rate_now_pct - market_cap_rate_avg)
    
    const confidence_factors = {
      data_freshness: Math.max(0.5, 1 - (Math.max(freshness.macro_days, freshness.fundamentals_days, freshness.comps_days) / 180)),
      comp_count: Math.min(1.0, comparables.length / 5),
      calculation_certainty: Math.max(0.3, 1 - (dualEngineResult.disagreement_pct / 100))
    }
    
    const overall_confidence = this.calculateConfidence({
      comp_count: comparables.length,
      macro_freshness_days: freshness.macro_days,
      fundamentals_freshness_days: freshness.fundamentals_days,
      comps_freshness_days: freshness.comps_days,
      dual_engine_disagreement_pct: dualEngineResult.disagreement_pct,
      cap_rate_variance_from_market: cap_rate_variance
    })
    
    return {
      noi_current,
      noi_future_12m,
      current_value: Math.round(dualEngineResult.recommended_value),
      future_value_12m: Math.round(future_value_12m),
      cap_rate_forecast_12m: Math.round(cap_rate_forecast_12m * 100) / 100,
      price_per_sf: Math.round(dualEngineResult.recommended_value / inputs.building_sf),
      confidence_factors
    }
  }
  
  /**
   * Get model metadata
   */
  static getModelMetadata() {
    return {
      name: 'valuation-blend',
      version: '1.0.0',
      cap_rate_model: CAP_RATE_MODEL_COEFFICIENTS,
      formulas: {
        noi: '(rent_psf_yr - opex_psf_yr) * building_sf * (1 - vacancy_pct)',
        current_value: 'NOI / (cap_rate_now_pct / 100)',
        future_noi: 'NOI * (1 + rent_growth_ann)^t',
        future_value: 'NOI_future / (cap_rate_future / 100)',
        cap_rate_forecast: 'cap_t + α*ΔMacroSpread + β*ΔVacancy - γ*AbsorptionToDeliveries'
      }
    }
  }
}

export type { ValuationInputs, ValuationOutputs, DualEngineResult }
export { CAP_RATE_MODEL_COEFFICIENTS }
