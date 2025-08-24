/**
 * ===== MINIMAL VALUATION API =====
 * Simple version to test basic functionality without dependencies that might crash
 */

import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  const start_time = Date.now()
  
  try {
    console.log('🔥 Valuation API called')
    
    // Parse request body
    const body = await request.json()
    const { market, building_sf, noi_annual, debug } = body
    
    // Basic validation
    if (!market || !building_sf || !noi_annual) {
      return NextResponse.json({ 
        error: 'Missing required fields: market, building_sf, noi_annual' 
      }, { status: 400 })
    }
    
    console.log(`📊 Processing: ${market}, ${building_sf} SF, NOI $${noi_annual}`)
    
    // Simple valuation calculation (no external dependencies)
    const cap_rate = 6.5 // Fixed 6.5% cap rate for testing
    const estimated_value = noi_annual / (cap_rate / 100)
    
    const response = {
      estimated_value: Math.round(estimated_value),
      estimated_value_range: {
        low: Math.round(estimated_value * 0.85),
        high: Math.round(estimated_value * 1.15)
      },
      cap_rate_applied: cap_rate,
      price_per_sf: Math.round(estimated_value / building_sf),
      confidence_score: 0.75,
      valuation_status: 'FRESH',
      calculated_at: new Date().toISOString(),
      calculation_time_ms: Date.now() - start_time,
      inputs: { market, building_sf, noi_annual },
      debug_enabled: !!debug
    }
    
    console.log(`✅ Valuation complete: $${response.estimated_value.toLocaleString()}`)
    
    return NextResponse.json(response, {
      status: 200,
      headers: {
        'Cache-Control': 'no-cache',
        'X-Calculation-Time': `${response.calculation_time_ms}ms`
      }
    })
    
  } catch (error) {
    console.error('❌ Valuation API error:', error)
    
    return NextResponse.json({ 
      error: `Valuation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      calculation_time_ms: Date.now() - start_time
    }, { status: 500 })
  }
}
