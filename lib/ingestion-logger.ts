/**
 * ===== INGESTION EVENT LOGGER =====
 * Utility functions to log ingestion events and job status to Supabase
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { createHash } from 'crypto'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export interface IngestEventRecord {
  id: string
  event_type: 'market.fundamentals.upsert' | 'comps.upsert' | 'macro.update' | 'api.prediction' | 'cache.warming'
  market_slug?: string
  source: string
  processed_records: number
  cache_invalidated: string[]
  processing_time_ms: number
  checksum?: string
  metadata?: Record<string, any>
  created_at: string
}

export interface JobRecord {
  id: string
  job_type: 'prediction' | 'cache_warming' | 'accuracy_check' | 'data_sync'
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  market_slug?: string
  input_data?: Record<string, any>
  output_data?: Record<string, any>
  error_message?: string
  processing_time_ms?: number
  started_at?: string
  completed_at?: string
  created_at: string
}

export interface CacheMetric {
  metric_name: string
  metric_value: number
  tags: Record<string, string>
  created_at: string
}

export interface ApiRequest {
  id: string
  endpoint: string
  method: string
  status_code: number
  response_time_ms: number
  market_slug?: string
  input_size_bytes?: number
  output_size_bytes?: number
  cache_hit: boolean
  user_agent?: string
  ip_address?: string
  created_at: string
}

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2)}`
}

export function calculateChecksum(data: any): string {
  return createHash('sha256').update(JSON.stringify(data)).digest('hex').substring(0, 16)
}

export async function logIngestionEvent(event: Partial<IngestEventRecord>): Promise<void> {
  try {
    const record: IngestEventRecord = {
      id: event.id || generateId(),
      event_type: event.event_type!,
      market_slug: event.market_slug,
      source: event.source || 'API',
      processed_records: event.processed_records || 0,
      cache_invalidated: event.cache_invalidated || [],
      processing_time_ms: event.processing_time_ms || 0,
      checksum: event.checksum,
      metadata: event.metadata,
      created_at: new Date().toISOString()
    }

    const { error } = await supabase.from('ingestion_events').insert(record)
    if (error) {
      console.error('Failed to log ingestion event:', error)
    }
  } catch (error) {
    console.error('Ingestion event logging error:', error)
  }
}

export async function createJob(job: Partial<JobRecord>): Promise<string> {
  try {
    const job_id = job.id || generateId()
    const record: JobRecord = {
      id: job_id,
      job_type: job.job_type!,
      status: 'QUEUED',
      market_slug: job.market_slug,
      input_data: job.input_data,
      output_data: job.output_data,
      error_message: job.error_message,
      processing_time_ms: job.processing_time_ms,
      started_at: job.started_at,
      completed_at: job.completed_at,
      created_at: new Date().toISOString()
    }

    const { error } = await supabase.from('jobs').insert(record)
    if (error) {
      console.error('Failed to create job record:', error)
    }

    return job_id
  } catch (error) {
    console.error('Job creation error:', error)
    return generateId()
  }
}

export async function updateJobStatus(job_id: string, updates: Partial<JobRecord>): Promise<void> {
  try {
    const { error } = await supabase
      .from('jobs')
      .update(updates)
      .eq('id', job_id)

    if (error) {
      console.error('Failed to update job status:', error)
    }
  } catch (error) {
    console.error('Job status update error:', error)
  }
}

export async function logCacheMetric(metric: CacheMetric): Promise<void> {
  try {
    const record = {
      ...metric,
      created_at: new Date().toISOString()
    }

    const { error } = await supabase.from('cache_metrics').insert(record)
    if (error) {
      console.error('Failed to log cache metric:', error)
    }
  } catch (error) {
    console.error('Cache metric logging error:', error)
  }
}

export async function logApiRequest(request: ApiRequest): Promise<void> {
  try {
    const record = {
      ...request,
      created_at: new Date().toISOString()
    }

    const { error } = await supabase.from('api_requests').insert(record)
    if (error) {
      console.error('Failed to log API request:', error)
    }
  } catch (error) {
    console.error('API request logging error:', error)
  }
}

// Helper to wrap API handlers with automatic logging
export function withApiLogging(
  handler: (req: any, res: any) => Promise<any>,
  endpoint_name: string
) {
  return async (req: any, res: any) => {
    const start_time = Date.now()
    const request_id = generateId()

    try {
      await handler(req, res)
      
      // Log successful request
      await logApiRequest({
        id: request_id,
        endpoint: endpoint_name,
        method: req.method || 'GET',
        status_code: res.statusCode || 200,
        response_time_ms: Date.now() - start_time,
        market_slug: req.query?.market_slug || req.body?.market_slug,
        cache_hit: false, // TODO: wire up actual cache status
        created_at: new Date().toISOString()
      })

    } catch (error) {
      // Log failed request
      await logApiRequest({
        id: request_id,
        endpoint: endpoint_name,
        method: req.method || 'GET',
        status_code: 500,
        response_time_ms: Date.now() - start_time,
        market_slug: req.query?.market_slug || req.body?.market_slug,
        cache_hit: false,
        created_at: new Date().toISOString()
      })

      throw error
    }
  }
}
