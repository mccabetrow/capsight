import { Pool } from 'pg'
import dotenv from 'dotenv'

dotenv.config()

const pool = new Pool({ connectionString: process.env.SUPABASE_DB_URL })

interface CompData {
  cap_rate: number
  months_since: number  
  distance_mi: number
  same_submarket: boolean
  noi_annual?: number
  price_total_usd: number
}

// Helper: Calculate months between dates
function monthsSince(date: Date): number {
  const now = new Date()
  return (now.getFullYear() - date.getFullYear()) * 12 + (now.getMonth() - date.getMonth())
}

// Helper: Weighted median cap rate calculation
function weightedMedianCapRate(comps: CompData[]): number {
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

// MAPE calculation
function computeMAPE(yTrue: number[], yPred: number[]): number {
  if (yTrue.length === 0) return 0
  
  let sum = 0
  let count = 0
  
  for (let i = 0; i < yTrue.length; i++) {
    if (yTrue[i] !== 0) {
      sum += Math.abs((yTrue[i] - yPred[i]) / yTrue[i])
      count++
    }
  }
  
  return count > 0 ? (sum / count) * 100 : 0
}

// RMSE calculation in basis points
function computeRMSE(yTrue: number[], yPred: number[]): number {
  if (yTrue.length === 0) return 0
  
  const sumSquares = yTrue.reduce((sum, actual, i) => {
    const diff = actual - yPred[i]
    return sum + (diff * diff)
  }, 0)
  
  return Math.sqrt(sumSquares / yTrue.length) * 100 // Convert to basis points
}

// 80% Interval Coverage
function computeIntervalCoverage(yTrue: number[], lower: number[], upper: number[]): number {
  if (yTrue.length === 0) return 0
  
  const covered = yTrue.filter((val, i) => val >= lower[i] && val <= upper[i]).length
  return (covered / yTrue.length) * 100
}

// Main evaluation job
async function runEvaluation(): Promise<void> {
  try {
    console.log('Starting CapSight accuracy evaluation...')
    
    // Load holdout comps with NOI
    const { rows: comps } = await pool.query(`
      SELECT * FROM industrial_sales 
      WHERE verification_status IN ('verified', 'broker-confirmed') 
        AND cap_rate_pct IS NOT NULL 
        AND sale_date >= (CURRENT_DATE - INTERVAL '24 months')
      ORDER BY sale_date DESC
    `)

    if (comps.length < 20) {
      console.error(`Insufficient data: ${comps.length} comps found, need at least 20`)
      process.exit(1)
    }

    console.log(`Evaluating on ${comps.length} verified comps...`)

    const valuationErrors: number[] = []
    const capRateActuals: number[] = []
    const capRatePreds: number[] = []
    const coverageResults: number[] = []

    // Leave-one-out cross-validation
    for (let i = 0; i < comps.length; i++) {
      const testComp = comps[i]
      const trainComps = comps.filter((_, j) => j !== i && comps[j].market === testComp.market)
      
      if (trainComps.length < 10) continue // Need minimum training data

      // Prepare training data
      const capRates = trainComps.map(c => ({
        cap_rate: c.cap_rate_pct,
        months_since: monthsSince(new Date(c.sale_date)),
        distance_mi: 0,
        same_submarket: true
      }))

      const predictedCapRate = weightedMedianCapRate(capRates)
      
      // Valuation prediction (if NOI available)
      if (testComp.noi_annual) {
        const { value_low, value_mid, value_high } = calcPriceBand(testComp.noi_annual, predictedCapRate, 50)
        const actualPrice = testComp.price_total_usd
        
        // MAPE calculation
        const percentError = Math.abs((actualPrice - value_mid) / actualPrice)
        valuationErrors.push(percentError)
        
        // Coverage check (80% interval)
        const covered = actualPrice >= value_low && actualPrice <= value_high
        coverageResults.push(covered ? 1 : 0)
      }

      // Cap rate prediction (always computed)
      capRateActuals.push(testComp.cap_rate_pct)
      capRatePreds.push(predictedCapRate)
    }

    // Compute metrics
    const mape = valuationErrors.length > 0 ? computeMAPE(
      valuationErrors.map((_, i) => i < capRateActuals.length ? 100 : 0), // dummy actuals for MAPE calc
      valuationErrors.map(e => e * 100)
    ) / 100 : null

    const rmse = computeRMSE(capRateActuals, capRatePreds)
    
    const intervalCoverage = coverageResults.length > 0 ? 
      (coverageResults.reduce((a, b) => a + b, 0) / coverageResults.length) * 100 : null

    // Store results
    await pool.query(`
      INSERT INTO eval_metrics (mape, caprate_rmse_bps, interval_coverage, n)
      VALUES ($1, $2, $3, $4)
    `, [mape, rmse, intervalCoverage, comps.length])

    console.log('Evaluation Results:')
    console.log(`  MAPE: ${mape ? (mape * 100).toFixed(2) + '%' : 'N/A'} (target: ≤10%)`)
    console.log(`  Cap Rate RMSE: ${rmse.toFixed(0)} bps (target: ≤50 bps)`)
    console.log(`  80% Coverage: ${intervalCoverage ? intervalCoverage.toFixed(1) + '%' : 'N/A'} (target: 78-82%)`)
    console.log(`  Sample size: ${comps.length}`)

    // Check SLA breaches
    let failed = false
    
    if (mape !== null && mape > 0.10) {
      console.error(`❌ MAPE SLA breach: ${(mape * 100).toFixed(2)}% > 10%`)
      failed = true
    }
    
    if (rmse > 50) {
      console.error(`❌ RMSE SLA breach: ${rmse.toFixed(0)} bps > 50 bps`)
      failed = true
    }
    
    if (intervalCoverage !== null && (intervalCoverage < 78 || intervalCoverage > 82)) {
      console.error(`❌ Coverage SLA breach: ${intervalCoverage.toFixed(1)}% not in [78%, 82%]`)
      failed = true
    }

    if (failed) {
      console.error('❌ SLA targets not met - failing CI')
      process.exit(1)
    } else {
      console.log('✅ All SLA targets met')
      process.exit(0)
    }

  } catch (error) {
    console.error('Evaluation failed:', error)
    process.exit(1)
  }
}

// Run if called directly
if (require.main === module) {
  runEvaluation()
}

export { runEvaluation, computeMAPE, computeRMSE, computeIntervalCoverage }
