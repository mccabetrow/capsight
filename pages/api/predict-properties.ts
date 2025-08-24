// Property prediction API with REAL CRE data
import type { NextApiRequest, NextApiResponse } from 'next'
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'
import path from 'path'

interface PropertyPrediction {
  id: string
  address: string
  building_sf: number
  estimated_value: number
  cap_rate: number
  investment_score: number
}

interface PredictionResponse {
  success: boolean
  city: string
  properties: PropertyPrediction[]
  data_source: string
}

// Load REAL CRE data
function loadRealCREData() {
  try {
    const dataPath = path.join(process.cwd(), 'real-cre-data.json')
    const jsonData = fs.readFileSync(dataPath, 'utf8')
    return JSON.parse(jsonData)
  } catch (error) {
    console.warn('Could not load real CRE data:', error)
    return null
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<PredictionResponse | { error: string }>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { city } = req.body

    if (!city) {
      return res.status(400).json({ error: 'City is required' })
    }

    console.log(`🔍 Predicting properties for: ${city}`)

    let dataSource = 'real_cre_data'
    let properties: PropertyPrediction[] = []

    // Map city to market
    const marketSlug = mapCityToMarket(city)
    console.log(`📍 Market mapped: ${city} → ${marketSlug}`)

    // Try Supabase first, then use real data from JSON
    try {
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.SUPABASE_SERVICE_ROLE_KEY!
      )

      console.log('🌐 Testing Supabase connection...')
      
      const { data, error } = await supabase
        .from('v_comps_trimmed')
        .select('*')
        .eq('market_slug', marketSlug)
        .limit(5)

      if (!error && data && data.length > 0) {
        console.log(`✅ Supabase connected! Found ${data.length} records`)
        dataSource = 'supabase_live'

        properties = data.map((comp) => ({
          id: comp.id,
          address: comp.address,
          building_sf: comp.building_sf,
          estimated_value: comp.price_per_sf_usd * comp.building_sf,
          cap_rate: comp.cap_rate_pct,
          investment_score: calculateInvestmentScore(comp)
        }))
      } else {
        throw new Error('No live data available')
      }
    } catch (error) {
      console.log('⚠️ Supabase unavailable, using REAL CRE data from file...')
      
      // Load real CRE data from JSON file
      const realData = loadRealCREData()
      
      if (realData && realData.comparables[marketSlug]) {
        const marketComps = realData.comparables[marketSlug]
        console.log(`📊 Using REAL ${marketSlug.toUpperCase()} market data (${marketComps.length} properties)`)
        
        properties = marketComps.map((comp: any, index: number) => ({
          id: comp.id,
          address: comp.address,
          building_sf: comp.building_sf,
          estimated_value: comp.price_per_sf_usd * comp.building_sf,
          cap_rate: comp.cap_rate_pct,
          investment_score: calculateInvestmentScore(comp, index)
        }))
        
        dataSource = 'real_market_data'
      } else {
        console.log('❌ No real data available for market:', marketSlug)
        // Use minimal fallback
        properties = generateMinimalFallback(city, marketSlug)
        dataSource = 'minimal_fallback'
      }
    }

    // Sort by investment score
    properties.sort((a, b) => b.investment_score - a.investment_score)

    const response: PredictionResponse = {
      success: true,
      city,
      properties: properties.slice(0, 5), // Top 5
      data_source: dataSource
    }

    console.log(`✅ Returning ${properties.length} properties from ${dataSource}`)
    return res.status(200).json(response)

  } catch (error) {
    console.error('❌ API Error:', error)
    return res.status(500).json({
      error: 'Failed to predict properties'
    })
  }
}

// City to market mapping
function mapCityToMarket(city: string): string {
  const cityLower = city.toLowerCase()
  
  if (cityLower.includes('dallas') || cityLower.includes('fort worth') || 
      cityLower.includes('plano') || cityLower.includes('frisco') || 
      cityLower.includes('irving') || cityLower.includes('dfw')) {
    return 'dfw'
  }
  
  if (cityLower.includes('phoenix') || cityLower.includes('scottsdale') || 
      cityLower.includes('tempe') || cityLower.includes('chandler')) {
    return 'phx'
  }
  
  if (cityLower.includes('atlanta') || cityLower.includes('marietta') || 
      cityLower.includes('alpharetta')) {
    return 'atl'
  }
  
  if (cityLower.includes('riverside') || cityLower.includes('san bernardino') || 
      cityLower.includes('ontario') || cityLower.includes('inland empire')) {
    return 'ie'
  }
  
  if (cityLower.includes('savannah')) {
    return 'sav'
  }
  
  // Default to Dallas for unknown cities
  return 'dfw'
}

// Calculate investment score based on real property metrics
function calculateInvestmentScore(comp: any, index: number = 0): number {
  let score = 50 // Base score

  // Cap rate scoring (30 points max)
  const capRate = comp.cap_rate_pct || comp.cap_rate
  if (capRate > 8.5) score += 25
  else if (capRate > 7.5) score += 20
  else if (capRate > 6.5) score += 15
  else if (capRate > 5.5) score += 10

  // Building quality (25 points max)
  if (comp.building_class === 'A') score += 25
  else if (comp.building_class === 'A-') score += 20
  else if (comp.building_class === 'B+') score += 15
  else if (comp.building_class === 'B') score += 10

  // Size scoring (20 points max) 
  if (comp.building_sf > 250000) score += 20
  else if (comp.building_sf > 200000) score += 15
  else if (comp.building_sf > 150000) score += 10
  else if (comp.building_sf > 100000) score += 5

  // Occupancy scoring (15 points max)
  if (comp.occupancy_pct > 90) score += 15
  else if (comp.occupancy_pct > 85) score += 10
  else if (comp.occupancy_pct > 80) score += 5

  // Age scoring (10 points max)
  const currentYear = new Date().getFullYear()
  const age = currentYear - (comp.year_built || 2010)
  if (age < 5) score += 10
  else if (age < 10) score += 8
  else if (age < 15) score += 5

  // Add some randomness to differentiate similar properties
  score += Math.floor(Math.random() * 5) - index * 2

  return Math.round(Math.min(100, Math.max(0, score)))
}

// Minimal fallback for unknown markets
function generateMinimalFallback(city: string, marketSlug: string): PropertyPrediction[] {
  return [
    {
      id: `${marketSlug}-fallback-1`,
      address: `1200 Business Plaza, ${city}`,
      building_sf: 185000,
      estimated_value: 28000000,
      cap_rate: 7.8,
      investment_score: 87
    },
    {
      id: `${marketSlug}-fallback-2`, 
      address: `1500 Corporate Center, ${city}`,
      building_sf: 225000,
      estimated_value: 32000000,
      cap_rate: 7.2,
      investment_score: 82
    },
    {
      id: `${marketSlug}-fallback-3`,
      address: `800 Industrial Way, ${city}`,
      building_sf: 165000,
      estimated_value: 24000000,
      cap_rate: 8.1,
      investment_score: 79
    }
  ]
}
