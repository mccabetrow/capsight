/**
 * ===== DATA INGESTION WEBHOOK CONTROLLER =====
 * Handles real-time data updates via webhooks with validation and cache invalidation
 */

import { NextRequest, NextResponse } from 'next/server'
import { createHmac, timingSafeEqual } from 'crypto'
import { getDataFetcher } from '../../../lib/data-fetcher'
import { createClient } from '@supabase/supabase-js'

interface IngestEvent {
  event_type: 'market.fundamentals.upsert' | 'comps.upsert' | 'macro.update'
  market_slug?: string
  data: Record<string, any>
  source: string
  timestamp: string
  checksum?: string
}

interface IngestResponse {
  success: boolean
  message: string
  processed_records?: number
  cache_invalidated?: string[]
  validation_errors?: string[]
  ingestion_id?: string
}

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'development-secret-change-in-production'
const MAX_CLOCK_SKEW_SECONDS = 300 // 5 minutes

export async function POST(request: NextRequest): Promise<NextResponse<IngestResponse | { error: string }>> {
  const start_time = Date.now()
  let ingestion_id: string | undefined

  try {
    // ===== WEBHOOK AUTHENTICATION =====
    const body_text = await request.text()
    const signature = request.headers.get('x-signature')
    const timestamp = request.headers.get('x-timestamp')
    
    if (!signature || !timestamp) {
      return NextResponse.json({ error: 'Missing required headers: x-signature, x-timestamp' }, { status: 401 })
    }

    // Verify timestamp (prevent replay attacks)
    const request_time = parseInt(timestamp)
    const current_time = Math.floor(Date.now() / 1000)
    
    if (Math.abs(current_time - request_time) > MAX_CLOCK_SKEW_SECONDS) {
      return NextResponse.json({ error: 'Request timestamp outside acceptable window' }, { status: 401 })
    }

    // Verify HMAC signature
    const expected_signature = 'sha256=' + createHmac('sha256', WEBHOOK_SECRET)
      .update(timestamp + '.' + body_text)
      .digest('hex')

    if (!timingSafeEqual(Buffer.from(signature), Buffer.from(expected_signature))) {
      return NextResponse.json({ error: 'Invalid signature' }, { status: 401 })
    }

    // Parse event data
    const event: IngestEvent = JSON.parse(body_text)
    ingestion_id = `ingest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    console.log(`📥 Processing ingest event: ${event.event_type} (${ingestion_id})`)

    // ===== VALIDATION =====
    const validation_errors = validateIngestEvent(event)
    if (validation_errors.length > 0) {
      return NextResponse.json({
        success: false,
        message: 'Validation failed',
        validation_errors,
        ingestion_id
      }, { status: 400 })
    }

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    )

    const dataFetcher = getDataFetcher()
    let processed_records = 0
    const cache_invalidated: string[] = []

    // ===== PROCESS BY EVENT TYPE =====
    switch (event.event_type) {
      case 'market.fundamentals.upsert':
        processed_records = await processMarketFundamentals(supabase, event)
        
        // Invalidate market-specific cache
        if (event.market_slug) {
          dataFetcher.invalidateCache(`fundamentals_${event.market_slug}`)
          cache_invalidated.push(`fundamentals_${event.market_slug}`)
        }
        break

      case 'comps.upsert':
        processed_records = await processComparables(supabase, event)
        
        // Invalidate comps cache for this market
        if (event.market_slug) {
          dataFetcher.invalidateCache(`comps_${event.market_slug}`)
          cache_invalidated.push(`comps_${event.market_slug}*`)
        }
        break

      case 'macro.update':
        // For macro updates, just invalidate the macro cache
        // The actual update is handled by FRED polling
        dataFetcher.invalidateCache('macro_data')
        cache_invalidated.push('macro_data')
        processed_records = 1
        break

      default:
        return NextResponse.json({
          success: false,
          message: `Unknown event type: ${event.event_type}`,
          ingestion_id
        }, { status: 400 })
    }

    // ===== LOG INGESTION EVENT =====
    try {
      await supabase.from('ingestion_events').insert({
        id: ingestion_id,
        event_type: event.event_type,
        market_slug: event.market_slug,
        source: event.source,
        processed_records,
        cache_invalidated: cache_invalidated,
        processing_time_ms: Date.now() - start_time,
        checksum: calculateChecksum(event.data),
        created_at: new Date().toISOString()
      })
    } catch (log_error) {
      console.error('Failed to log ingestion event:', log_error)
      // Don't fail the whole operation for logging issues
    }

    console.log(`✅ Ingestion complete: ${processed_records} records processed (${Date.now() - start_time}ms)`)

    return NextResponse.json({
      success: true,
      message: `Successfully processed ${event.event_type}`,
      processed_records,
      cache_invalidated,
      ingestion_id
    }, {
      status: 200,
      headers: {
        'X-Processing-Time': `${Date.now() - start_time}ms`,
        'X-Ingestion-ID': ingestion_id
      }
    })

  } catch (error) {
    console.error('Ingestion error:', error, ingestion_id)

    return NextResponse.json({
      success: false,
      message: `Ingestion failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      ingestion_id
    }, {
      status: 500,
      headers: {
        'X-Processing-Time': `${Date.now() - start_time}ms`,
        'X-Ingestion-ID': ingestion_id || 'unknown'
      }
    })
  }
}

function validateIngestEvent(event: IngestEvent): string[] {
  const errors: string[] = []

  if (!event.event_type) {
    errors.push('event_type is required')
  }

  if (!event.data || typeof event.data !== 'object') {
    errors.push('data must be a valid object')
  }

  if (!event.source) {
    errors.push('source is required')
  }

  if (!event.timestamp) {
    errors.push('timestamp is required')
  }

  // Event-specific validation
  switch (event.event_type) {
    case 'market.fundamentals.upsert':
      if (!event.market_slug) {
        errors.push('market_slug is required for market fundamentals')
      }
      
      const required_fields = ['vacancy_rate_pct', 'avg_asking_rent_psf_yr_nnn', 'yoy_rent_growth_pct', 'avg_cap_rate_pct']
      for (const field of required_fields) {
        if (!(field in event.data) || typeof event.data[field] !== 'number') {
          errors.push(`${field} is required and must be a number`)
        }
      }
      
      // Range validation
      if (event.data.vacancy_rate_pct < 0 || event.data.vacancy_rate_pct > 40) {
        errors.push('vacancy_rate_pct must be between 0 and 40')
      }
      if (event.data.avg_cap_rate_pct < 2 || event.data.avg_cap_rate_pct > 20) {
        errors.push('avg_cap_rate_pct must be between 2 and 20')
      }
      break

    case 'comps.upsert':
      if (!event.market_slug) {
        errors.push('market_slug is required for comparables')
      }
      
      if (!Array.isArray(event.data.comparables)) {
        errors.push('data.comparables must be an array')
      } else {
        event.data.comparables.forEach((comp: any, index: number) => {
          if (!comp.building_sf || comp.building_sf <= 0) {
            errors.push(`comparables[${index}].building_sf must be positive`)
          }
          if (!comp.price_per_sf_usd || comp.price_per_sf_usd <= 0) {
            errors.push(`comparables[${index}].price_per_sf_usd must be positive`)
          }
          if (!comp.sale_date) {
            errors.push(`comparables[${index}].sale_date is required`)
          }
        })
      }
      break
  }

  return errors
}

async function processMarketFundamentals(supabase: any, event: IngestEvent): Promise<number> {
  const { data, error } = await supabase
    .from('market_fundamentals')
    .upsert({
      market_slug: event.market_slug,
      ...event.data,
      updated_at: new Date().toISOString()
    }, {
      onConflict: 'market_slug',
      ignoreDuplicates: false
    })

  if (error) {
    throw new Error(`Failed to upsert market fundamentals: ${error.message}`)
  }

  return 1
}

async function processComparables(supabase: any, event: IngestEvent): Promise<number> {
  const comparables = event.data.comparables as any[]
  
  // Add market_slug to each comparable
  const comparables_with_market = comparables.map(comp => ({
    ...comp,
    market_slug: event.market_slug,
    created_at: new Date().toISOString()
  }))

  const { data, error } = await supabase
    .from('v_comps_trimmed')
    .insert(comparables_with_market)

  if (error) {
    throw new Error(`Failed to insert comparables: ${error.message}`)
  }

  return comparables_with_market.length
}

function calculateChecksum(data: any): string {
  const data_string = JSON.stringify(data, Object.keys(data).sort())
  return createHmac('sha256', 'checksum-key')
    .update(data_string)
    .digest('hex')
    .slice(0, 16)
}

// ===== GET ENDPOINT FOR INGESTION STATUS =====
export async function GET(request: NextRequest): Promise<NextResponse> {
  const url = new URL(request.url)
  const ingestion_id = url.searchParams.get('id')

  if (!ingestion_id) {
    return NextResponse.json({ error: 'ingestion_id parameter required' }, { status: 400 })
  }

  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    )

    const { data, error } = await supabase
      .from('ingestion_events')
      .select('*')
      .eq('id', ingestion_id)
      .single()

    if (error || !data) {
      return NextResponse.json({ error: 'Ingestion event not found' }, { status: 404 })
    }

    return NextResponse.json({
      success: true,
      event: data
    })

  } catch (error) {
    return NextResponse.json({
      error: `Failed to retrieve ingestion status: ${error}`
    }, { status: 500 })
  }
}
