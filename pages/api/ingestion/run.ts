/**
 * ===== INGESTION PIPELINE API ENDPOINT =====
 * Provides HTTP API access to the ingestion pipeline
 * 
 * POST /api/ingestion/run - Run the full pipeline
 * GET /api/ingestion/health - Health check
 * GET /api/ingestion/status/:runId - Get run status
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { ingestionOrchestrator } from '../../../lib/ingestion-orchestrator'
import type { PipelineOptions } from '../../../lib/ingestion-orchestrator'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, query } = req
  
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  
  if (method === 'OPTIONS') {
    res.status(200).end()
    return
  }
  
  try {
    switch (method) {
      case 'POST':
        await handleRunPipeline(req, res)
        break
        
      case 'GET':
        if (query.action === 'health') {
          await handleHealthCheck(req, res)
        } else if (query.action === 'status' && query.runId) {
          await handleRunStatus(req, res)
        } else {
          res.status(400).json({ 
            error: 'Invalid request', 
            message: 'Use GET /api/ingestion?action=health or POST /api/ingestion/run' 
          })
        }
        break
        
      default:
        res.setHeader('Allow', ['GET', 'POST', 'OPTIONS'])
        res.status(405).json({ error: 'Method not allowed' })
        break
    }
  } catch (error) {
    console.error('❌ Ingestion API error:', error)
    res.status(500).json({
      error: 'Internal server error',
      message: error instanceof Error ? error.message : String(error),
      timestamp: new Date().toISOString()
    })
  }
}

async function handleRunPipeline(req: NextApiRequest, res: NextApiResponse) {
  console.log('🚀 Pipeline run requested via API')
  
  // Parse request body
  const {
    max_properties,
    enable_webhooks = true,
    county_data_source,
    skip_stages = [],
    dry_run = false,
    run_id
  } = req.body || {}
  
  // Validate inputs
  if (max_properties && (typeof max_properties !== 'number' || max_properties <= 0)) {
    res.status(400).json({ error: 'max_properties must be a positive number' })
    return
  }
  
  if (skip_stages && !Array.isArray(skip_stages)) {
    res.status(400).json({ error: 'skip_stages must be an array' })
    return
  }
  
  const validStages = ['ingestion', 'normalization', 'enrichment', 'valuation', 'scoring', 'persistence', 'webhooks']
  const invalidStages = skip_stages.filter((stage: string) => !validStages.includes(stage))
  if (invalidStages.length > 0) {
    res.status(400).json({ 
      error: `Invalid stages: ${invalidStages.join(', ')}`, 
      valid_stages: validStages 
    })
    return
  }
  
  try {
    const options: PipelineOptions = {
      run_id,
      max_properties,
      enable_webhooks,
      county_data_source,
      skip_stages,
      dry_run
    }
    
    // For long-running processes, we should ideally run this in the background
    // and return a job ID, but for MVP we'll run synchronously
    const startTime = Date.now()
    
    // Send initial response with run information
    const runId = options.run_id || `api-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`
    
    console.log(`🔄 Starting pipeline run: ${runId}`)
    
    const summary = await ingestionOrchestrator.runFullPipeline(options)
    
    const duration = Date.now() - startTime
    
    // Return successful response
    res.status(200).json({
      success: true,
      message: 'Pipeline completed successfully',
      duration_ms: duration,
      summary: {
        run_id: summary.run_id,
        started_at: summary.started_at,
        completed_at: summary.completed_at,
        total_processed: summary.total_processed,
        successful_properties: summary.successful_properties,
        failed_properties: summary.failed_properties,
        webhook_events_sent: summary.webhook_events_sent,
        webhook_events_failed: summary.webhook_events_failed,
        success_rate: summary.total_processed > 0 
          ? Math.round((summary.successful_properties / summary.total_processed) * 100) 
          : 0,
        stages: summary.stages
      }
    })
    
  } catch (error) {
    console.error('❌ Pipeline execution failed:', error)
    
    res.status(500).json({
      success: false,
      error: 'Pipeline execution failed',
      message: error instanceof Error ? error.message : String(error),
      timestamp: new Date().toISOString()
    })
  }
}

async function handleHealthCheck(req: NextApiRequest, res: NextApiResponse) {
  console.log('🏥 Health check requested via API')
  
  try {
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

async function handleRunStatus(req: NextApiRequest, res: NextApiResponse) {
  const { runId } = req.query
  
  // For MVP, we don't have persistent job tracking
  // In production, this would query a job status table
  res.status(501).json({
    error: 'Not implemented',
    message: 'Run status tracking not implemented in MVP',
    run_id: runId
  })
}
