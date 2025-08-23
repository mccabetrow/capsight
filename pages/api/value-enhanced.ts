import { NextApiRequest, NextApiResponse } from 'next'
import { createServiceRoleClient } from '../../lib/supabase'

interface CompData {
  sale_id: string
  market_slug: string
  address: string
  city: string
  sale_date: string
  price_total_usd: number
  building_sf: number
  cap_rate_pct: number
  price_per_sf_usd: number
  noi_annual: number
  submarket: string
  verification_status: string
}

interface WeightedComp extends CompData {
  months_since: number
  distance_mi: number
  weight_recency: number
  weight_distance: number
  weight_size: number
  weight_combined: number
  adjusted_cap_rate: number
}

interface ValuationRequest {
  market_slug: string
  noi_annual: number
  building_sf: number
  submarket?: string
}

interface ValuationResult {
  valuation_usd: number
  confidence_interval: [number, number]
  cap_rate_pct: number
  price_per_sf_usd: number
  methodology: string
  comp_count: number
  top_comps: Array<{
    address_masked: string
    sale_date: string
    adjusted_cap_rate: number
    weight: number
    distance_mi: number
  }>
  confidence_band: {
    width_pct: number
    label: string
    status: 'ok' | 'warn' | 'bad'
  }
  quality_indicators: {
    sample_size: number
    data_freshness_months: number
    dispersion_bps: number
    fallback_reason?: string
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ValuationResult | { error: string; retry_after?: string }>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { market_slug, noi_annual, building_sf, submarket }: ValuationRequest = req.body

    if (!market_slug || !noi_annual || !building_sf) {
      return res.status(400).json({ error: 'Missing required fields: market_slug, noi_annual, building_sf' })
    }

    const supabase = createServiceRoleClient()
    
    // Check market status (kill switch)
    const { data: marketStatus, error: statusError } = await supabase
      .from('market_status')
      .select('enabled, reason, updated_at')
      .eq('market_slug', market_slug)
      .single()
    
    if (statusError && statusError.code !== 'PGRST116') { // PGRST116 = no rows found
      console.error('Market status error:', statusError)
      return res.status(500).json({ error: 'Database query failed' })
    }
    
    // If market is disabled, return 422
    if (marketStatus && !marketStatus.enabled) {
      return res.status(422).json({ 
        error: `Market '${market_slug}' temporarily disabled: ${marketStatus.reason || 'Data quality issues'}`,
        retry_after: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 24 hours
      })
    }
    
    // Get trimmed comps (outliers already removed by view)
    const { data: comps, error } = await supabase
      .from('mv_comps_recent_12m') // Use materialized view for performance
      .select('*')
      .eq('market_slug', market_slug)
      .order('sale_date', { ascending: false })

    if (error) {
      console.error('Supabase error:', error)
      return res.status(500).json({ error: 'Database query failed' })
    }

    if (!comps || comps.length === 0) {
      return res.status(404).json({ error: 'No comparable sales found for this market' })
    }

    // Get accuracy metrics for confidence band calibration
    const { data: accuracy } = await supabase
      .from('latest_accuracy')
      .select('*')
      .eq('market_slug', market_slug)
      .single()

    // Calculate weighted comps with similarity scoring
    const weightedComps = calculateWeightedComps(comps, building_sf, submarket)
    
    // Apply fallback rules if needed
    const fallbackResult = checkFallbackRules(weightedComps, accuracy)
    
    // Calculate final valuation
    const capRate = calculateRobustCapRate(weightedComps, fallbackResult)
    const valuation = Math.round(noi_annual / (capRate / 100))
    
    // Determine confidence band
    const confidenceBand = determineConfidenceBand(accuracy, fallbackResult)
    const confidenceInterval: [number, number] = [
      Math.round(valuation * (1 - confidenceBand.width_pct)),
      Math.round(valuation * (1 + confidenceBand.width_pct))
    ]

    // Prepare top 5 comps for auditability
    const topComps = weightedComps
      .sort((a, b) => b.weight_combined - a.weight_combined)
      .slice(0, 5)
      .map(comp => ({
        address_masked: maskAddress(comp.address),
        sale_date: comp.sale_date,
        adjusted_cap_rate: comp.adjusted_cap_rate,
        weight: Math.round(comp.weight_combined * 100) / 100,
        distance_mi: Math.round(comp.distance_mi * 10) / 10
      }))

    // Quality indicators
    const dataFreshness = weightedComps.length > 0 
      ? Math.max(...weightedComps.map(c => c.months_since)) 
      : 0
    
    const dispersionBps = calculateDispersion(weightedComps) * 10000

    const result: ValuationResult = {
      valuation_usd: valuation,
      confidence_interval: confidenceInterval,
      cap_rate_pct: Math.round(capRate * 100) / 100,
      price_per_sf_usd: Math.round(valuation / building_sf),
      methodology: 'weighted_median_robust_v1.0',
      comp_count: weightedComps.length,
      top_comps: topComps,
      confidence_band: confidenceBand,
      quality_indicators: {
        sample_size: weightedComps.length,
        data_freshness_months: Math.round(dataFreshness * 10) / 10,
        dispersion_bps: Math.round(dispersionBps),
        fallback_reason: fallbackResult.reason
      }
    }

    res.status(200).json(result)
  } catch (error) {
    console.error('Valuation API error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}

// Similarity weighting with robust kernels
function calculateWeightedComps(comps: CompData[], subjectSf: number, subjectSubmarket?: string): WeightedComp[] {
  const now = new Date()
  
  return comps.map(comp => {
    const saleDate = new Date(comp.sale_date)
    const monthsSince = (now.getTime() - saleDate.getTime()) / (1000 * 60 * 60 * 24 * 30.44)
    
    // Recency weight: 12-month half-life
    const weightRecency = Math.exp(-Math.log(2) * monthsSince / 12)
    
    // Distance weight: 15-mile exponential decay + submarket bonus
    const distanceMi = 0 // TODO: Implement actual distance calculation
    const submktBonus = (subjectSubmarket && comp.submarket === subjectSubmarket) ? 2.0 : 1.0
    const weightDistance = Math.exp(-distanceMi / 15) * submktBonus
    
    // Size weight: Gaussian on log scale (σ = 0.35)
    const logSizeRatio = Math.log(comp.building_sf) - Math.log(subjectSf)
    const weightSize = Math.exp(-0.5 * Math.pow(logSizeRatio / 0.35, 2))
    
    // Combined weight (will be normalized later)
    const weightCombined = weightRecency * weightDistance * weightSize
    
    // Time-adjusted cap rate (simplified - would use market trend in production)
    const adjustedCapRate = comp.cap_rate_pct // TODO: Apply market trend adjustment
    
    return {
      ...comp,
      months_since: monthsSince,
      distance_mi: distanceMi,
      weight_recency: weightRecency,
      weight_distance: weightDistance,
      weight_size: weightSize,
      weight_combined: weightCombined,
      adjusted_cap_rate: adjustedCapRate
    }
  })
}

// Check for fallback conditions
function checkFallbackRules(comps: WeightedComp[], accuracy: any): { 
  useFallback: boolean
  reason?: string
  widthAdjustment: number 
} {
  // Low sample size
  if (comps.length < 8) {
    return { 
      useFallback: true, 
      reason: 'Low sample size',
      widthAdjustment: 0.05 // +5% width
    }
  }
  
  // High dispersion
  const dispersion = calculateDispersion(comps)
  if (dispersion > 0.015) { // 150 bps
    return {
      useFallback: false,
      reason: 'High dispersion',
      widthAdjustment: 0.025 // +2.5% width
    }
  }
  
  // Stale data
  const avgAge = comps.reduce((sum, c) => sum + c.months_since, 0) / comps.length
  if (avgAge > 18) {
    return {
      useFallback: false,
      reason: 'Stale data',
      widthAdjustment: 0.045 // +4.5% width
    }
  }
  
  return { useFallback: false, widthAdjustment: 0 }
}

// Calculate robust weighted median cap rate
function calculateRobustCapRate(comps: WeightedComp[], fallback: any): number {
  if (comps.length === 0) return 6.5 // Emergency fallback
  
  // Normalize weights
  const totalWeight = comps.reduce((sum, c) => sum + c.weight_combined, 0)
  comps.forEach(c => c.weight_combined /= totalWeight)
  
  // Sort by adjusted cap rate
  const sorted = comps.sort((a, b) => a.adjusted_cap_rate - b.adjusted_cap_rate)
  
  // Find weighted median
  let cumWeight = 0
  for (const comp of sorted) {
    cumWeight += comp.weight_combined
    if (cumWeight >= 0.5) {
      return comp.adjusted_cap_rate
    }
  }
  
  // Fallback to simple median
  return sorted[Math.floor(sorted.length / 2)].adjusted_cap_rate
}

// Calculate weighted dispersion (IQR)
function calculateDispersion(comps: WeightedComp[]): number {
  if (comps.length < 4) return 0
  
  const sorted = comps
    .sort((a, b) => a.adjusted_cap_rate - b.adjusted_cap_rate)
    .map(c => c.adjusted_cap_rate)
  
  const q1 = sorted[Math.floor(sorted.length * 0.25)]
  const q3 = sorted[Math.floor(sorted.length * 0.75)]
  
  return (q3 - q1) / 100 // Convert to decimal
}

// Determine dynamic confidence band based on accuracy metrics
function determineConfidenceBand(accuracy: any, fallback: any): {
  width_pct: number
  label: string
  status: 'ok' | 'warn' | 'bad'
} {
  // Default fallback
  let width = 0.10 // 10%
  let label = '±10% (default)'
  let status: 'ok' | 'warn' | 'bad' = 'bad'
  
  // If we have accuracy data, use conformal prediction
  if (accuracy && accuracy.ape_q80) {
    const slaOk = accuracy.mape <= 0.10 && 
                  accuracy.rmse_bps <= 50 && 
                  accuracy.coverage80 >= 0.78 && 
                  accuracy.coverage80 <= 0.82
    
    const conformalWidth = Math.max(0.05, accuracy.ape_q80) // Minimum 5%
    
    // Apply fallback adjustments
    width = conformalWidth + fallback.widthAdjustment
    
    if (slaOk && conformalWidth <= 0.05) {
      label = '±5% (SLA met)'
      status = 'ok'
    } else if (conformalWidth <= 0.08) {
      label = `±${Math.round(width * 100)}% (calibrated)`
      status = 'warn'
    } else {
      label = `±${Math.round(width * 100)}% (low data/high dispersion)`
      status = 'bad'
    }
  }
  
  return { width_pct: width, label, status }
}

// Mask address for privacy while maintaining auditability
function maskAddress(address: string): string {
  const parts = address.split(' ')
  if (parts.length > 2) {
    return `${parts[0]} ****** ${parts[parts.length - 1]}`
  }
  return `****** ${parts[parts.length - 1]}`
}
