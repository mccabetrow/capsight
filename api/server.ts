import express from 'express'
import { Pool } from 'pg'
import dotenv from 'dotenv'
import cors from 'cors'

dotenv.config()

const app = express()
app.use(cors())
app.use(express.json())

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

// Initialize database pool with error handling
const pool = new Pool({ 
  connectionString: process.env.SUPABASE_DB_URL || 'postgresql://localhost:5432/capsight'
})

// Helper: Calculate months between dates
function monthsSince(date: Date): number {
  const now = new Date()
  return (now.getFullYear() - date.getFullYear()) * 12 + (now.getMonth() - date.getMonth())
}

// Helper: Weighted median cap rate calculation
function weightedMedianCapRate(comps: Array<{
  cap_rate: number
  months_since: number
  distance_mi: number
  same_submarket: boolean
}>): number {
  const weighted = comps.map(c => ({
    cap_rate: c.cap_rate,
    weight: Math.exp(-c.months_since / 6) * (1 / (1 + c.distance_mi)) * (c.same_submarket ? 1 : 0.7)
  }))
  
  weighted.sort((a, b) => a.cap_rate - b.cap_rate)
  
  const totalWeight = weighted.reduce((sum, c) => sum + c.weight, 0)
  let acc = 0
  
  for (const c of weighted) {
    acc += c.weight
    if (acc >= totalWeight / 2) {
      return c.cap_rate
    }
  }
  
  return weighted[weighted.length - 1].cap_rate
}

// Helper: Calculate price band with ±50 bps
function calcPriceBand(noi: number, capMid: number, bps: number = 50) {
  const capLow = capMid - bps / 100
  const capHigh = capMid + bps / 100
  
  return {
    value_low: Math.round(noi / (capHigh / 100)),
    value_mid: Math.round(noi / (capMid / 100)),
    value_high: Math.round(noi / (capLow / 100))
  }
}

// Main valuation endpoint
app.get('/api/value', async (req, res) => {
  try {
    const { market_slug, noi_annual } = req.query
    
    if (!market_slug || !noi_annual) {
      return res.status(400).json({ 
        error: 'market_slug and noi_annual required' 
      })
    }

    // Get market UUID from slug
    const { rows: markets } = await pool.query(
      'SELECT id FROM markets WHERE slug = $1',
      [market_slug]
    )
    
    if (markets.length === 0) {
      return res.status(400).json({ error: 'Invalid market_slug' })
    }
    
    const marketId = markets[0].id

    // Get verified comps (last 18 months, with cap_rate)
    const { rows: comps } = await pool.query(
      `SELECT cap_rate_pct, sale_date, submarket, address, building_sf, 
              price_total_usd, data_source_name, data_source_url
       FROM industrial_sales
       WHERE market = $1 AND cap_rate_pct IS NOT NULL 
         AND verification_status IN ('verified', 'broker-confirmed')
         AND sale_date >= (CURRENT_DATE - INTERVAL '18 months')
       ORDER BY sale_date DESC`,
      [marketId]
    )

    if (comps.length < 10) {
      return res.status(400).json({ 
        error: 'Not enough verified comps',
        found: comps.length,
        required: 10
      })
    }

    // Calculate weighted median cap rate
    const capRates = comps.map(c => ({
      cap_rate: c.cap_rate_pct,
      months_since: monthsSince(new Date(c.sale_date)),
      distance_mi: 0, // TODO: Add geodist if address provided
      same_submarket: true // TODO: Compare submarket if address provided
    }))

    const cap_rate_mid = weightedMedianCapRate(capRates)
    const { value_low, value_mid, value_high } = calcPriceBand(Number(noi_annual), cap_rate_mid, 50)

    res.json({
      cap_rate_mid: Number(cap_rate_mid.toFixed(2)),
      cap_rate_band_bps: 50,
      value_low,
      value_mid,
      value_high,
      n: comps.length,
      market_slug
    })

  } catch (error) {
    console.error('Value API error:', error)
    res.status(500).json({ 
      error: 'Internal server error',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`CapSight API running on port ${PORT}`)
})

export default app
