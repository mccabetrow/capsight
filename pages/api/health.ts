import { NextApiRequest, NextApiResponse } from 'next'

interface HealthResponse {
  status: string
  timestamp: string
  version: string
  checks?: {
    database?: boolean
    accuracy_metrics?: boolean
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<HealthResponse>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({
      status: 'error',
      timestamp: new Date().toISOString(),
      version: '1.0.0'
    })
  }

  try {
    const health: HealthResponse = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: '1.0.0'
    }

    // Basic health check - API is responding
    res.status(200).json(health)
  } catch (error) {
    res.status(500).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      version: '1.0.0'
    })
  }
}
