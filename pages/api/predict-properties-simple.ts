// Simple property prediction API for testing
import type { NextApiRequest, NextApiResponse } from 'next'
import { createClient } from '@supabase/supabase-js'

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

    let dataSource = 'fallback'
    let properties: PropertyPrediction[] = []

    // Test Supabase connection with the new valid keys
    try {
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.SUPABASE_SERVICE_ROLE_KEY!
      )

      console.log('🌐 Testing Supabase connection...')
      
      // Try to fetch some data
      const { data, error } = await supabase
        .from('v_comps_trimmed')
        .select('*')
        .limit(5)

      if (error) {
        console.log('⚠️ Supabase error:', error)
        throw error
      }

      console.log(`✅ Supabase connected! Found ${data?.length || 0} records`)
      dataSource = 'supabase'

      // Use real data if available
      if (data && data.length > 0) {
        properties = data.map((comp, i) => ({
          id: `prop-${i + 1}`,
          address: `${1000 + i * 200} Commerce St, ${city}`,
          building_sf: comp.building_sf || 150000,
          estimated_value: comp.price_per_sf_usd * comp.building_sf || 25000000,
          cap_rate: comp.cap_rate_pct || 7.5,
          investment_score: Math.round(75 + Math.random() * 20)
        }))
      }
    } catch (error) {
      console.log('⚠️ Using fallback data due to Supabase error:', error)
    }

    // Use fallback data if Supabase failed
    if (properties.length === 0) {
      properties = [
        {
          id: 'prop-1',
          address: `1200 Business Plaza, ${city}`,
          building_sf: 185000,
          estimated_value: 28000000,
          cap_rate: 7.8,
          investment_score: 87
        },
        {
          id: 'prop-2', 
          address: `1500 Corporate Center, ${city}`,
          building_sf: 225000,
          estimated_value: 32000000,
          cap_rate: 7.2,
          investment_score: 82
        },
        {
          id: 'prop-3',
          address: `800 Industrial Way, ${city}`,
          building_sf: 165000,
          estimated_value: 24000000,
          cap_rate: 8.1,
          investment_score: 79
        }
      ]
    }

    const response: PredictionResponse = {
      success: true,
      city,
      properties,
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
