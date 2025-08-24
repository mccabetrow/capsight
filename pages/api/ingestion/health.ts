/**
 * ===== INGESTION PIPELINE HEALTH CHECK API =====
 * GET /api/ingestion/health - Health check for ingestion pipeline
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { ingestionOrchestrator } from '../../../lib/ingestion-orchestrator'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', ['GET'])
    res.status(405).json({ error: 'Method not allowed' })
    return
  }
  
  try {
    console.log('🏥 Ingestion health check requested')
    
    const health = await ingestionOrchestrator.healthCheck()
    
    const responseData = {
      healthy: health.healthy,
      timestamp: health.timestamp,
      services: {
        geocoding: {
          status: health.geocoding.cache_size >= 0 ? 'healthy' : 'unhealthy',
          cache_size: health.geocoding.cache_size,
          cache_hit_rate: Math.round(health.geocoding.cache_hit_rate * 100),
          total_requests: health.geocoding.total_requests
        },
        database: {
          status: health.supabase.properties_total >= 0 ? 'healthy' : 'unhealthy',
          properties_count: health.supabase.properties_total,
          valuations_count: health.supabase.valuations_total,
          scores_count: health.supabase.scores_total,
          features_count: health.supabase.features_total
        },
        webhooks: {
          status: health.webhook.healthy ? 'healthy' : 'unhealthy',
          latency_ms: health.webhook.latencyMs || null,
          reason: health.webhook.reason || null
        }
      },
      config: {
        max_batch_size: health.config.max_batch_size,
        node_version: health.config.node_version,
        environment: health.config.environment
      }
    }
    
    const statusCode = health.healthy ? 200 : 503
    res.status(statusCode).json(responseData)
    
  } catch (error) {
    console.error('❌ Health check failed:', error)
    
    res.status(503).json({
      healthy: false,
      error: 'Health check failed',
      message: error instanceof Error ? error.message : String(error),
      timestamp: new Date().toISOString()
    })
  }
}
