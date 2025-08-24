#!/usr/bin/env node
/**
 * 🔗 N8N WEBHOOK MONITORING
 * Monitor webhook delivery and validate payloads
 */

const crypto = require('crypto')

// Configuration
const WEBHOOK_URL = process.env.N8N_WEBHOOK_URL || 'https://your-n8n-instance.com/webhook/capsight'
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'your-webhook-secret'
const API_BASE_URL = process.env.VERCEL_URL || 'https://capsight.vercel.app'

console.log('🔗 CapSight Webhook Monitoring')
console.log(`API Base: ${API_BASE_URL}`)
console.log(`Webhook: ${WEBHOOK_URL}`)
console.log('=' .repeat(60))

// Mock n8n webhook endpoint for testing
function createMockWebhookServer() {
  const express = require('express')
  const app = express()
  
  app.use(express.json({ limit: '10mb' }))
  
  const receivedWebhooks = []
  
  // Mock n8n webhook endpoint
  app.post('/webhook/capsight', (req, res) => {
    const signature = req.headers['x-webhook-signature']
    const requestId = req.headers['x-request-id']
    const idempotencyKey = req.headers['x-idempotency-key']
    
    console.log(`📨 Received webhook [${requestId}]:`)
    console.log(`  Type: ${req.body.type}`)
    console.log(`  Schema: ${req.body.schema_version}`)
    console.log(`  Tenant: ${req.body.tenant_id}`)
    console.log(`  Signature: ${signature}`)
    console.log(`  Idempotency: ${idempotencyKey}`)
    
    // Validate signature
    if (signature && WEBHOOK_SECRET) {
      const expectedSignature = 'sha256=' + crypto
        .createHmac('sha256', WEBHOOK_SECRET)
        .update(JSON.stringify(req.body))
        .digest('hex')
        
      if (signature === expectedSignature) {
        console.log('  ✅ Signature valid')
      } else {
        console.log('  ❌ Signature invalid')
      }
    }
    
    // Store webhook for analysis
    receivedWebhooks.push({
      timestamp: new Date().toISOString(),
      requestId,
      idempotencyKey,
      signature,
      payload: req.body
    })
    
    // Respond to webhook
    res.json({ 
      status: 'received',
      timestamp: new Date().toISOString(),
      requestId
    })
  })
  
  // Status endpoint
  app.get('/status', (req, res) => {
    res.json({
      webhooks_received: receivedWebhooks.length,
      latest_webhook: receivedWebhooks[receivedWebhooks.length - 1]?.timestamp,
      webhook_types: [...new Set(receivedWebhooks.map(w => w.payload.type))]
    })
  })
  
  return { app, receivedWebhooks }
}

async function testWebhookDelivery() {
  console.log('\n🔗 Testing Webhook Delivery...')
  
  // Test cases that should trigger webhooks
  const testCases = [
    {
      name: 'Successful Valuation',
      payload: {
        market: 'dallas',
        building_sf: 100000,
        noi_annual: 6500000
      },
      expectedWebhookType: 'valuation.upsert'
    },
    {
      name: 'Insufficient Data Case',
      payload: {
        market: 'unknown-market',
        building_sf: 1000, // Very small building
        noi_annual: 10000  // Very low NOI
      },
      expectedWebhookType: 'valuation.insufficient'
    }
  ]
  
  for (const testCase of testCases) {
    console.log(`\n📊 ${testCase.name}:`)
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/valuation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testCase.payload)
      })
      
      const data = await response.json()
      
      console.log(`  API Status: ${response.status}`)
      console.log(`  Request ID: ${data.request_id}`)
      
      if (data.debug?.webhook_result) {
        console.log(`  Webhook Status: ${data.debug.webhook_result.status}`)
        console.log(`  Webhook Attempts: ${data.debug.webhook_result.attempts}`)
        console.log(`  Webhook Duration: ${data.debug.webhook_result.duration_ms}ms`)
        
        if (data.debug.webhook_result.status === 'delivered') {
          console.log('  ✅ Webhook delivered successfully')
        } else {
          console.log(`  ❌ Webhook failed: ${data.debug.webhook_result.error}`)
        }
      } else {
        console.log('  ⚠️ No webhook result in debug info')
      }
      
    } catch (error) {
      console.log(`  ❌ Test failed: ${error.message}`)
    }
    
    // Wait between requests to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 1000))
  }
}

async function monitorWebhookMetrics() {
  console.log('\n📊 Webhook Metrics...')
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/webhook/metrics`)
    const data = await response.json()
    
    console.log(`Total Sent: ${data.total_sent}`)
    console.log(`Total Delivered: ${data.total_delivered}`)
    console.log(`Success Rate: ${(data.success_rate * 100).toFixed(1)}%`)
    console.log(`Avg Response Time: ${data.avg_response_time_ms}ms`)
    console.log(`Circuit Breaker State: ${data.circuit_breaker_state}`)
    
    if (data.recent_failures?.length > 0) {
      console.log('Recent Failures:')
      data.recent_failures.forEach(failure => {
        console.log(`  - ${failure.timestamp}: ${failure.error}`)
      })
    }
    
  } catch (error) {
    console.log('❌ Failed to get webhook metrics:', error.message)
  }
}

async function validateWebhookSchema() {
  console.log('\n🔍 Webhook Schema Validation...')
  
  // Test with a known good payload
  const testPayload = {
    market: 'dallas',
    building_sf: 100000,
    noi_annual: 6500000,
    debug: true
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/v2/valuation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testPayload)
    })
    
    const data = await response.json()
    
    if (data.debug?.webhook_result?.payload) {
      const payload = data.debug.webhook_result.payload
      
      console.log('📋 Webhook Payload Structure:')
      console.log(`  Schema Version: ${payload.schema_version}`)
      console.log(`  Type: ${payload.type}`)
      console.log(`  Tenant ID: ${payload.tenant_id}`)
      console.log(`  Model: ${payload.model?.name} v${payload.model?.version}`)
      console.log(`  Address: ${payload.address}`)
      console.log(`  Current Value: $${payload.current_value?.point?.toLocaleString()}`)
      console.log(`  Confidence: ${(payload.current_value?.confidence * 100).toFixed(1)}%`)
      console.log(`  Forecast: $${payload.forecast_12m?.point?.toLocaleString()}`)
      console.log(`  Drivers Count: ${payload.drivers?.length}`)
      
      // Validate required fields
      const requiredFields = ['schema_version', 'type', 'tenant_id', 'model', 'current_value']
      const missingFields = requiredFields.filter(field => !payload[field])
      
      if (missingFields.length === 0) {
        console.log('  ✅ All required fields present')
      } else {
        console.log(`  ❌ Missing fields: ${missingFields.join(', ')}`)
      }
      
    } else {
      console.log('  ⚠️ No webhook payload found in debug info')
    }
    
  } catch (error) {
    console.log('❌ Schema validation failed:', error.message)
  }
}

// N8N Webhook Test Configuration
function generateN8nTestWorkflow() {
  const workflow = {
    name: 'CapSight Webhook Handler',
    nodes: [
      {
        parameters: {
          httpMethod: 'POST',
          path: '/webhook/capsight',
          responseMode: 'responseNode',
          options: {}
        },
        id: 'webhook-trigger',
        name: 'CapSight Webhook',
        type: 'n8n-nodes-base.webhook',
        position: [240, 300]
      },
      {
        parameters: {
          conditions: {
            string: [
              {
                value1: '={{$json.type}}',
                operation: 'equal',
                value2: 'valuation.upsert'
              }
            ]
          }
        },
        id: 'filter-valuation',
        name: 'Is Valuation?',
        type: 'n8n-nodes-base.if',
        position: [460, 300]
      },
      {
        parameters: {
          respondWith: 'json',
          responseBody: '={"status": "processed", "type": "{{$json.type}}", "value": {{$json.current_value.point}}}'
        },
        id: 'webhook-response',
        name: 'Response',
        type: 'n8n-nodes-base.respondToWebhook',
        position: [680, 200]
      }
    ],
    connections: {
      'CapSight Webhook': {
        main: [['Is Valuation?']]
      },
      'Is Valuation?': {
        main: [['Response'], ['Response']]
      }
    }
  }
  
  return JSON.stringify(workflow, null, 2)
}

// Run all monitoring tasks
async function runWebhookMonitoring() {
  await testWebhookDelivery()
  await monitorWebhookMetrics()
  await validateWebhookSchema()
  
  console.log('\n' + '='.repeat(60))
  console.log('🔗 Webhook Monitoring Complete!')
  console.log('\nN8N Setup:')
  console.log('1. Create webhook endpoint at /webhook/capsight')
  console.log('2. Configure HMAC signature validation')
  console.log('3. Handle valuation.upsert and valuation.insufficient events')
  console.log('4. Set up alerts for failed deliveries')
  
  console.log('\nSample n8n workflow:')
  console.log(generateN8nTestWorkflow())
}

// Execute if run directly
if (require.main === module) {
  runWebhookMonitoring().catch(console.error)
}

module.exports = {
  testWebhookDelivery,
  monitorWebhookMetrics,
  validateWebhookSchema,
  generateN8nTestWorkflow,
  runWebhookMonitoring
}
