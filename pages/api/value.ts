import { NextApiRequest, NextApiResponse } from 'next'
import { createServiceRoleClient } from '../../lib/supabase'

interface CompData {
  sale_date: string
  cap_rate_pct: number
  submarket: string
  noi_annual: number
}

interface ValuationResponse {
  market_slug: string
  noi_annual: number
  cap_rate_mid: number
  cap_rate_band_bps: number
  value_low: number
  value_mid: number
  value_high: number
  n: number
  confidence: 'low' | 'medium' | 'high'
}

// Initialize Supabase with service role for API operations
const supabase = createServiceRoleClient()

// Calculate months since a date
function monthsSince(dateString: string): number {
  const saleDate = new Date(dateString)
  const now = new Date()
  const diffTime = Math.abs(now.getTime() - saleDate.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return Math.round(diffDays / 30.44) // Average days per month
}

// Calculate weighted median cap rate
function calculateWeightedMedianCapRate(comps: CompData[], targetSubmarket?: string): number {
  if (comps.length === 0) return 6.5 // Default fallback

  // Calculate weights for each comp
  const weightedComps = comps.map(comp => {
    const months = monthsSince(comp.sale_date)
    const timeWeight = Math.exp(-months / 6) // Decay over 6 months
    const submarketWeight = comp.submarket === targetSubmarket ? 1.2 : 1.0
    
    return {
      cap_rate: comp.cap_rate_pct,
      weight: timeWeight * submarketWeight
    }
  })

  // Sort by cap rate
  weightedComps.sort((a, b) => a.cap_rate - b.cap_rate)

  // Find weighted median
  const totalWeight = weightedComps.reduce((sum, comp) => sum + comp.weight, 0)
  let cumulativeWeight = 0
  
  for (const comp of weightedComps) {
    cumulativeWeight += comp.weight
    if (cumulativeWeight >= totalWeight / 2) {
      return comp.cap_rate
    }
  }

  return weightedComps[Math.floor(weightedComps.length / 2)].cap_rate
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { market_slug, noi_annual } = req.query

  // Validate inputs
  if (!market_slug || !noi_annual) {
    return res.status(400).json({ 
      error: 'Missing required parameters',
      required: ['market_slug', 'noi_annual']
    })
  }

  const noiValue = parseFloat(noi_annual as string)
  if (isNaN(noiValue) || noiValue <= 0) {
    return res.status(400).json({ error: 'Invalid NOI value' })
  }

  const validMarkets = ['dfw', 'ie', 'atl', 'phx', 'sav']
  if (!validMarkets.includes(market_slug as string)) {
    return res.status(400).json({ 
      error: 'Invalid market',
      valid_markets: validMarkets
    })
  }

  try {
    // Fetch verified comps from last 18 months
    const { data: comps, error } = await supabase
      .from('v_verified_sales_18mo')
      .select(`
        sale_date,
        cap_rate_pct,
        submarket,
        noi_annual
      `)
      .eq('market_slug', market_slug)
      .not('cap_rate_pct', 'is', null)
      .not('noi_annual', 'is', null)
      .order('sale_date', { ascending: false })

    if (error) {
      console.error('Supabase error:', error)
      return res.status(500).json({ error: 'Failed to fetch comparable data' })
    }

    if (!comps || comps.length === 0) {
      return res.status(404).json({ 
        error: 'No verified comps found for market',
        market_slug
      })
    }

    // Calculate weighted median cap rate
    const capRateMid = calculateWeightedMedianCapRate(comps)
    const bandBps = 50 // ±50 basis points
    
    // Calculate valuation band
    const capRateLow = capRateMid - (bandBps / 100)
    const capRateHigh = capRateMid + (bandBps / 100)
    
    const valueMid = Math.round(noiValue / (capRateMid / 100))
    const valueLow = Math.round(noiValue / (capRateHigh / 100))
    const valueHigh = Math.round(noiValue / (capRateLow / 100))

    // Determine confidence based on number of comps
    let confidence: 'low' | 'medium' | 'high' = 'low'
    if (comps.length >= 10) confidence = 'high'
    else if (comps.length >= 5) confidence = 'medium'

    const response: ValuationResponse = {
      market_slug: market_slug as string,
      noi_annual: noiValue,
      cap_rate_mid: Math.round(capRateMid * 10) / 10, // 1 decimal
      cap_rate_band_bps: bandBps,
      value_low: valueLow,
      value_mid: valueMid,
      value_high: valueHigh,
      n: comps.length,
      confidence
    }

    // Set cache headers for performance
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
    
    return res.status(200).json(response)

  } catch (error) {
    console.error('Valuation API error:', error)
    return res.status(500).json({ 
      error: 'Internal server error',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
}
