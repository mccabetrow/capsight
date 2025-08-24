// API endpoint to handle city input triggers
import type { NextApiRequest, NextApiResponse } from 'next'

interface CityTriggerRequest {
  city: string
  timestamp: string
  action: string
  userId?: string
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { city, timestamp, action, userId }: CityTriggerRequest = req.body

    console.log(`City trigger: ${action} for ${city} at ${timestamp}`)

    // Here you can:
    // 1. Log to database
    // 2. Trigger external webhooks
    // 3. Send notifications
    // 4. Update analytics
    // 5. Fetch city-specific data

    // Example: Fetch property data for the city
    if (action === 'city_selected') {
      // Call your valuation API
      const valuationData = await fetchCityData(city)
      
      // Trigger external webhook (optional)
      await triggerExternalWebhook({
        event: 'city_selected',
        city,
        timestamp,
        userId,
        data: valuationData
      })

      return res.status(200).json({
        success: true,
        city,
        message: `Triggered for ${city}`,
        data: valuationData
      })
    }

    res.status(200).json({ success: true, city, action })

  } catch (error) {
    console.error('City trigger error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}

async function fetchCityData(city: string) {
  // Implement your city data fetching logic here
  // This could call your valuation API, fetch market data, etc.
  return {
    city,
    marketData: `Sample data for ${city}`,
    timestamp: new Date().toISOString()
  }
}

async function triggerExternalWebhook(payload: any) {
  // Optional: Trigger external services
  const webhookUrl = process.env.EXTERNAL_WEBHOOK_URL
  
  if (webhookUrl) {
    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
    } catch (error) {
      console.error('External webhook failed:', error)
    }
  }
}
