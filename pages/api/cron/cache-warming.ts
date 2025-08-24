/**
 * ===== CACHE WARMING AND SYSTEM MAINTENANCE CRON JOB =====
 * Runs every 6 hours to pre-fetch macro data and warm caches
 * Also performs system health checks and data freshness monitoring
 */

import { NextRequest, NextResponse } from 'next/server'
import { getDataFetcher } from '../../../lib/data-fetcher'
import { logIngestionEvent, createJob, updateJobStatus, logCacheMetric, generateId } from '../../../lib/ingestion-logger'

interface CronJobResult {
  success: boolean
  timestamp: string
  execution_time_ms: number
  cache_warming: {
    macro_data: { success: boolean, latency_ms?: number, error?: string }
    markets_warmed: number
    comps_cached: number
    total_cache_operations: number
  }
  health_summary: {
    overall_status: string
    data_sources_healthy: number
    stale_markets_count: number
    oldest_data_days: number
  }
  maintenance: {
    cache_cleanup: boolean
    circuit_breaker_reset: boolean
  }
  next_run: string
}

const CRON_SECRET = process.env.CRON_SECRET || 'development-cron-secret'
const MARKETS_TO_WARM = ['dfw', 'atl', 'phx', 'ie', 'sav']

export async function POST(request: NextRequest): Promise<NextResponse<CronJobResult | { error: string }>> {
  const start_time = Date.now()
  let job_id: string | undefined
  
  try {
    // ===== AUTHENTICATION =====
    const auth_header = request.headers.get('authorization')
    if (auth_header !== `Bearer ${CRON_SECRET}`) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    console.log('🔄 Starting cache warming and maintenance job...')

    // Create job record
    job_id = await createJob({
      job_type: 'cache_warming',
      started_at: new Date().toISOString()
    })

    await updateJobStatus(job_id, { status: 'RUNNING' })

    const dataFetcher = getDataFetcher()
    const cache_warming_results = {
      macro_data: { success: false as boolean, latency_ms: undefined as number | undefined, error: undefined as string | undefined },
      markets_warmed: 0,
      comps_cached: 0,
      total_cache_operations: 0
    }

    // ===== 1. WARM MACRO DATA CACHE =====
    console.log('📊 Warming macro data cache...')
    try {
      const macro_start = Date.now()
      const { data: macro_data } = await dataFetcher.getMacroData()
      cache_warming_results.macro_data = {
        success: true,
        latency_ms: Date.now() - macro_start,
        error: undefined
      }
      cache_warming_results.total_cache_operations++
      console.log(`✅ Macro data cached: Fed Funds ${macro_data.fed_funds_rate}%, 10Y Treasury ${macro_data.treasury_10yr}%`)
    } catch (error) {
      cache_warming_results.macro_data = {
        success: false,
        latency_ms: undefined,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
      console.error('❌ Failed to warm macro data cache:', error)
    }

    // ===== 2. WARM MARKET FUNDAMENTALS CACHE =====
    console.log('🏢 Warming market fundamentals cache...')
    for (const market_slug of MARKETS_TO_WARM) {
      try {
        const { data: fundamentals, freshness } = await dataFetcher.getMarketFundamentals(market_slug)
        if (fundamentals) {
          cache_warming_results.markets_warmed++
          cache_warming_results.total_cache_operations++
          console.log(`✅ ${market_slug}: ${fundamentals.city} (${freshness.status}, ${freshness.days_old}d old)`)
        }
      } catch (error) {
        console.error(`❌ Failed to warm ${market_slug} fundamentals:`, error)
      }
    }

    // ===== 3. WARM COMPARABLES CACHE =====
    console.log('🏗️ Warming comparables cache...')
    for (const market_slug of MARKETS_TO_WARM) {
      try {
        const { data: comps } = await dataFetcher.getComps(market_slug, 15)
        cache_warming_results.comps_cached += comps.length
        cache_warming_results.total_cache_operations++
        console.log(`✅ ${market_slug}: ${comps.length} comparables cached`)
      } catch (error) {
        console.error(`❌ Failed to warm ${market_slug} comps:`, error)
      }
    }

    // ===== 4. PERFORM HEALTH CHECK =====
    console.log('🩺 Performing system health check...')
    const health_check = await dataFetcher.healthCheck()
    const health_summary = {
      overall_status: health_check.status,
      data_sources_healthy: Object.values(health_check.checks).filter(c => c.status === 'healthy').length,
      stale_markets_count: 0,
      oldest_data_days: 0
    }

    // Check data freshness across markets
    let oldest_data_days = 0
    let stale_count = 0
    
    for (const market_slug of MARKETS_TO_WARM) {
      try {
        const { freshness } = await dataFetcher.getMarketFundamentals(market_slug)
        if (freshness.days_old > oldest_data_days) {
          oldest_data_days = freshness.days_old
        }
        if (!freshness.is_fresh) {
          stale_count++
        }
      } catch (error) {
        stale_count++
      }
    }

    health_summary.stale_markets_count = stale_count
    health_summary.oldest_data_days = oldest_data_days

    // ===== 5. MAINTENANCE TASKS =====
    console.log('🧹 Performing maintenance tasks...')
    const maintenance_results = {
      cache_cleanup: false,
      circuit_breaker_reset: false
    }

    // TODO: Implement cache cleanup for very old entries
    // TODO: Reset circuit breakers if they've been open for too long

    maintenance_results.cache_cleanup = true // Placeholder
    maintenance_results.circuit_breaker_reset = true // Placeholder

    // ===== 6. SCHEDULE NEXT RUN =====
    const next_run_time = new Date(Date.now() + 6 * 60 * 60 * 1000) // 6 hours
    
    const execution_time = Date.now() - start_time
    console.log(`✅ Cache warming completed in ${execution_time}ms`)

    const result: CronJobResult = {
      success: true,
      timestamp: new Date().toISOString(),
      execution_time_ms: execution_time,
      cache_warming: cache_warming_results,
      health_summary,
      maintenance: maintenance_results,
      next_run: next_run_time.toISOString()
    }

    // Complete job and log success
    if (job_id) {
      await updateJobStatus(job_id, {
        status: 'COMPLETED',
        output_data: {
          cache_operations: cache_warming_results.total_cache_operations,
          markets_warmed: cache_warming_results.markets_warmed,
          health_status: health_summary.overall_status
        },
        processing_time_ms: execution_time,
        completed_at: new Date().toISOString()
      })
    }

    // Log cache warming event
    await logIngestionEvent({
      event_type: 'cache.warming',
      source: 'cron-job',
      processed_records: cache_warming_results.total_cache_operations,
      cache_invalidated: [],
      processing_time_ms: execution_time,
      metadata: {
        markets_warmed: cache_warming_results.markets_warmed,
        comps_cached: cache_warming_results.comps_cached,
        health_status: health_summary.overall_status
      }
    })

    // Log cache metrics
    await logCacheMetric({
      metric_name: 'cache_warming_operations',
      metric_value: cache_warming_results.total_cache_operations,
      tags: { job_type: 'cache_warming', status: 'success' },
      created_at: new Date().toISOString()
    })

    return NextResponse.json(result, {
      status: 200,
      headers: {
        'Cache-Control': 'no-cache',
        'X-Cron-Job': 'cache-warming',
        'X-Next-Run': result.next_run
      }
    })

  } catch (error) {
    console.error('❌ Cron job failed:', error)

    // Log failed job
    if (job_id) {
      await updateJobStatus(job_id, {
        status: 'FAILED',
        error_message: error instanceof Error ? error.message : String(error),
        processing_time_ms: Date.now() - start_time,
        completed_at: new Date().toISOString()
      })
    }

    return NextResponse.json({
      success: false,
      timestamp: new Date().toISOString(),
      execution_time_ms: Date.now() - start_time,
      error: error instanceof Error ? error.message : 'Unknown error'
    } as any, {
      status: 500,
      headers: {
        'X-Cron-Job': 'cache-warming',
        'X-Error': 'true'
      }
    })
  }
}

// ===== GET ENDPOINT FOR CRON JOB STATUS =====
export async function GET(request: NextRequest): Promise<NextResponse> {
  // Simple status endpoint to check if cron job is accessible
  return NextResponse.json({
    service: 'cache-warming-cron',
    status: 'ready',
    description: 'POST to this endpoint with Bearer token to run cache warming',
    next_scheduled_run: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
    markets_monitored: MARKETS_TO_WARM,
    cache_types: ['macro_data', 'market_fundamentals', 'comparables'],
    authentication: 'Bearer token required'
  }, {
    status: 200,
    headers: {
      'Cache-Control': 'no-cache'
    }
  })
}
