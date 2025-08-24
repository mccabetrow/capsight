/**
 * ===== WEBHOOK METRICS ENDPOINT =====
 * Provides observability into webhook client performance and health
 */

import { NextRequest, NextResponse } from 'next/server'
import { getWebhookClient } from '../../../lib/webhook-client-production'

export async function GET(request: NextRequest) {
  try {
    const webhookClient = getWebhookClient()
    const metrics = webhookClient.getMetrics()
    
    const response = {
      timestamp: new Date().toISOString(),
      webhook_client: {
        ...metrics,
        url: process.env.N8N_INGEST_URL ? 'configured' : 'missing',
        secret: process.env.WEBHOOK_SECRET ? 'configured' : 'missing',
        tenant_id: process.env.CAPSIGHT_TENANT_ID || 'default'
      },
      health: {
        circuit_breaker_state: metrics.circuit_breaker.state,
        overall: metrics.circuit_breaker.state === 'CLOSED' ? 'healthy' : 'degraded'
      }
    }
    
    return NextResponse.json(response, {
      headers: {
        'Cache-Control': 'no-cache, must-revalidate'
      }
    })
    
  } catch (error) {
    console.error('Webhook metrics error:', error)
    
    return NextResponse.json({ 
      error: 'Failed to retrieve webhook metrics',
      timestamp: new Date().toISOString()
    }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    // Test webhook endpoint - sends a test payload
    const webhookClient = getWebhookClient()
    
    const testPayload = {
      schema_version: '1.0' as const,
      type: 'valuation.upsert' as const,
      tenant_id: process.env.CAPSIGHT_TENANT_ID || 'default',
      as_of: new Date().toISOString().split('T')[0],
      model: {
        name: 'CapSight-Valuation-Engine',
        version: '1.0.2'
      },
      provenance: {
        macro: {
          source: 'test',
          as_of: new Date().toISOString(),
          from_cache: false
        },
        fundamentals: {
          source: 'test',
          as_of: new Date().toISOString()
        },
        comps: {
          source: 'test',
          as_of: new Date().toISOString()
        }
      },
      address: 'Test Property - 123 Main St',
      geo: {
        lat: 32.7767,
        lon: -96.7970,
        market: 'DFW',
        submarket: 'Downtown'
      },
      property_snapshot: {
        building_sf: 50000,
        year_built: 2020
      },
      inputs: {
        asset_type: 'office' as const,
        rent_psf_yr: 28.5,
        opex_psf_yr: 8.5,
        vacancy_pct: 0.08,
        cap_rate_now_pct: 6.5,
        cap_rate_qoq_delta_bps: -25
      },
      current_value: {
        point: 21500000,
        low: 19350000,
        high: 23650000,
        confidence: 0.78
      },
      forecast_12m: {
        point: 22575000,
        low: 20318000,
        high: 24833000,
        confidence: 0.65
      },
      drivers: [
        'Market cap rate: 6.25%',
        'Fed funds adjustment: +15bps', 
        '8 comparable sales',
        'NOI: $1,400,000'
      ]
    }
    
    const result = await webhookClient.send(testPayload, 'test-webhook-' + Date.now())
    
    return NextResponse.json({
      test_result: result,
      metrics: webhookClient.getMetrics(),
      timestamp: new Date().toISOString()
    })
    
  } catch (error) {
    console.error('Test webhook error:', error)
    
    return NextResponse.json({ 
      error: 'Failed to send test webhook',
      timestamp: new Date().toISOString()
    }, { status: 500 })
  }
}
