#!/usr/bin/env node

/**
 * 🚀 CapsightMVP → n8n Webhook Integration Test
 * 
 * Sends a production-grade valuation event to n8n with:
 * - HMAC-SHA256 signature authentication
 * - Idempotency keys and payload hashing
 * - Exponential backoff retry logic
 * - Comprehensive logging and error handling
 * 
 * Usage: node test-webhook.mjs
 */

import crypto from 'crypto'
import fs from 'fs'
import path from 'path'

// ===== ENVIRONMENT LOADER =====

/**
 * Simple .env file parser (no external dependencies)
 */
function loadEnvironment() {
  const envPath = path.join(process.cwd(), '.env')
  
  if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf8')
    const envLines = envContent.split('\n')
    
    for (const line of envLines) {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=')
        if (key && valueParts.length > 0) {
          const value = valueParts.join('=').trim()
          process.env[key.trim()] = value
        }
      }
    }
    
    console.log('📁 Loaded environment from .env file')
  } else {
    console.log('📁 No .env file found, using system environment variables')
  }
}

// Load environment on startup
loadEnvironment()

// ===== CONFIGURATION =====

const WEBHOOK_URL = process.env.N8N_WEBHOOK_URL || 'https://walkerb.app.n8n.cloud/webhook/450e72ce-45e9-4aa6-bb10-90ca044164c6'
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'fallback-secret-for-testing'
const MAX_RETRIES = 5
const BASE_DELAY_MS = 500

// ===== UTILITY FUNCTIONS =====

/**
 * Generate UUID v4
 */
function generateUUID() {
  return crypto.randomUUID()
}

/**
 * Generate ISO-8601 timestamp
 */
function getCurrentTimestamp() {
  return new Date().toISOString()
}

/**
 * Generate SHA-256 hash of string
 */
function sha256Hash(data) {
  return crypto.createHash('sha256').update(data, 'utf8').digest('hex')
}

/**
 * Generate HMAC-SHA256 signature
 */
function generateHMAC(secret, data) {
  return crypto.createHmac('sha256', secret).update(data, 'utf8').digest('hex')
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// ===== PAYLOAD GENERATION =====

/**
 * Generate production-grade valuation event payload
 */
function createValuationPayload() {
  const timestamp = getCurrentTimestamp()
  
  return {
    schema_version: "1.0",
    type: "valuation.upsert",
    tenant_id: "demo",
    as_of: timestamp,
    model: { 
      name: "valuation-blend", 
      version: "1.0.0" 
    },
    provenance: {
      macro: { 
        source: "FRED", 
        as_of: "2025-08-23", 
        from_cache: false 
      },
      fundamentals: { 
        source: "Supabase:markets", 
        as_of: "2025-07-15" 
      },
      comps: { 
        source: "Supabase:comps", 
        as_of: "2025-06-30" 
      }
    },
    address: "2100 Logistics Pkwy, Dallas, TX",
    geo: { 
      lat: 32.79, 
      lon: -96.80, 
      market: "Dallas–Fort Worth, TX", 
      submarket: "South Stemmons" 
    },
    inputs: {
      asset_type: "industrial",
      rent_psf_yr: 9.8,
      opex_psf_yr: 1.6,
      vacancy_pct: 0.032,
      cap_rate_now_pct: 5.9,
      cap_rate_qoq_delta_bps: -20
    },
    current_value: { 
      point: 32500000, 
      low: 30500000, 
      high: 34600000, 
      confidence: 0.72 
    },
    forecast_12m: { 
      point: 34400000, 
      low: 32800000, 
      high: 36300000, 
      confidence: 0.70 
    },
    drivers: [
      "Rent momentum +1.8% q/q", 
      "Vacancy 3.2% and falling", 
      "Cap rate −20 bps QoQ"
    ]
  }
}

// ===== HTTP CLIENT WITH RETRY LOGIC =====

/**
 * Send webhook with exponential backoff retry logic
 */
async function sendWebhookWithRetry(payload, headers) {
  const payloadJSON = JSON.stringify(payload, null, 2)
  
  console.log('🚀 Starting webhook delivery...')
  console.log('📍 URL:', WEBHOOK_URL)
  console.log('🔒 Headers:', JSON.stringify(headers, null, 2))
  console.log('📦 Payload size:', Buffer.byteLength(payloadJSON, 'utf8'), 'bytes')
  console.log('📋 Payload preview:')
  console.log(payloadJSON.substring(0, 200) + '...\n')
  
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    const startTime = Date.now()
    
    try {
      console.log(`🔄 Attempt ${attempt}/${MAX_RETRIES} - ${new Date().toISOString()}`)
      
      const response = await fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: payloadJSON
      })
      
      const duration = Date.now() - startTime
      const responseText = await response.text()
      
      if (response.ok) {
        console.log(`✅ Webhook delivered successfully!`)
        console.log(`   Status: ${response.status} ${response.statusText}`)
        console.log(`   Duration: ${duration}ms`)
        console.log(`   Response: ${responseText.substring(0, 100)}`)
        return { success: true, status: response.status, response: responseText }
      } else {
        console.log(`⚠️  HTTP ${response.status}: ${response.statusText}`)
        console.log(`   Duration: ${duration}ms`)
        console.log(`   Response: ${responseText}`)
        
        if (attempt === MAX_RETRIES) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      }
      
    } catch (error) {
      const duration = Date.now() - startTime
      console.log(`❌ Attempt ${attempt} failed after ${duration}ms:`, error.message)
      
      if (attempt === MAX_RETRIES) {
        throw error
      }
    }
    
    // Exponential backoff: 0.5s, 1s, 2s, 4s, 8s
    const delayMs = BASE_DELAY_MS * Math.pow(2, attempt - 1)
    console.log(`⏳ Waiting ${delayMs}ms before retry...\n`)
    await sleep(delayMs)
  }
  
  throw new Error(`Failed to deliver webhook after ${MAX_RETRIES} attempts`)
}

// ===== MAIN EXECUTION =====

async function main() {
  try {
    console.log('🎯 CapsightMVP → n8n Webhook Integration Test')
    console.log('=' .repeat(50))
    console.log()
    
    // Generate payload
    const payload = createValuationPayload()
    const payloadJSON = JSON.stringify(payload)
    
    // Generate security headers
    const requestId = generateUUID()
    const timestamp = getCurrentTimestamp()
    const payloadHash = sha256Hash(payloadJSON)
    const signature = generateHMAC(WEBHOOK_SECRET, payloadJSON)
    
    const headers = {
      'X-Capsight-Tenant': 'demo',
      'X-Request-Id': requestId,
      'X-Timestamp': timestamp,
      'X-Payload-Hash': payloadHash,
      'X-Capsight-Signature': `sha256=${signature}`,
      'User-Agent': 'CapsightMVP-WebhookTest/1.0'
    }
    
    // Log security details
    console.log('🔐 Security Details:')
    console.log(`   Request ID: ${requestId}`)
    console.log(`   Timestamp: ${timestamp}`)
    console.log(`   Payload Hash: ${payloadHash}`)
    console.log(`   HMAC Signature: sha256=${signature.substring(0, 16)}...`)
    console.log(`   Secret Length: ${WEBHOOK_SECRET.length} chars`)
    console.log()
    
    // Send webhook
    const result = await sendWebhookWithRetry(payload, headers)
    
    console.log()
    console.log('🎉 SUCCESS: Webhook integration test completed!')
    console.log(`   Final Status: ${result.status}`)
    console.log(`   Response Size: ${Buffer.byteLength(result.response || '', 'utf8')} bytes`)
    
    process.exit(0)
    
  } catch (error) {
    console.log()
    console.log('💥 FAILURE: Webhook integration test failed!')
    console.log(`   Error: ${error.message}`)
    console.log(`   Stack: ${error.stack}`)
    
    process.exit(1)
  }
}

// ===== ENVIRONMENT VALIDATION =====

function validateEnvironment() {
  const issues = []
  
  if (!WEBHOOK_URL || !WEBHOOK_URL.startsWith('https://')) {
    issues.push('N8N_WEBHOOK_URL must be a valid HTTPS URL')
  }
  
  if (!WEBHOOK_SECRET || WEBHOOK_SECRET.length < 8) {
    issues.push('WEBHOOK_SECRET must be at least 8 characters')
  }
  
  if (issues.length > 0) {
    console.error('❌ Environment validation failed:')
    issues.forEach(issue => console.error(`   - ${issue}`))
    console.error()
    console.error('💡 Create a .env file with:')
    console.error('   WEBHOOK_SECRET=your-secret-here')
    console.error('   N8N_WEBHOOK_URL=https://your-n8n-webhook-url')
    process.exit(1)
  }
}

// ===== STARTUP =====

console.log('⚡ Initializing webhook test...')
validateEnvironment()
main().catch(error => {
  console.error('💥 Unhandled error:', error)
  process.exit(1)
})
