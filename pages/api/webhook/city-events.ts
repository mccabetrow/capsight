// Webhook endpoint that external services can call
import type { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Verify webhook signature (recommended for security)
  const signature = req.headers['x-webhook-signature']
  const expectedSignature = process.env.WEBHOOK_SECRET
  
  if (signature !== expectedSignature) {
    return res.status(401).json({ error: 'Unauthorized' })
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { city, event, data } = req.body

    console.log(`External webhook received: ${event} for city ${city}`)

    // Process the webhook
    switch (event) {
      case 'city_data_updated':
        await handleCityDataUpdate(city, data)
        break
      case 'market_analysis_complete':
        await handleMarketAnalysis(city, data)
        break
      default:
        console.log(`Unknown event: ${event}`)
    }

    res.status(200).json({ 
      success: true, 
      message: `Webhook processed for ${city}` 
    })

  } catch (error) {
    console.error('Webhook error:', error)
    res.status(500).json({ error: 'Webhook processing failed' })
  }
}

async function handleCityDataUpdate(city: string, data: any) {
  // Update your database with new city data
  console.log(`Updating data for ${city}:`, data)
}

async function handleMarketAnalysis(city: string, data: any) {
  // Process market analysis results
  console.log(`Market analysis complete for ${city}:`, data)
}
