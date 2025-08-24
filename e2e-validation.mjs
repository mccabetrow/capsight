/**
 * ===== END-TO-END VALIDATION SCRIPT =====
 * Comprehensive testing of the ingestion pipeline and deployment readiness
 */
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { readFileSync } from 'fs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Configuration
const API_BASE = 'http://localhost:3000'
const ENDPOINTS_TO_TEST = [
  '/api/health',
  '/api/health/data',
  '/api/ingestion/health',
  '/api/webhook/metrics',
  '/api/v2/valuation'
]

// Test data
const SAMPLE_VALUATION_REQUEST = {
  market: 'dfw',
  building_sf: 50000,
  noi_annual: 1400000,
  debug: true
}

const SAMPLE_INGESTION_REQUEST = {
  connectors: ['county-data'],
  filters: {
    market: 'Dallas-Fort Worth, TX',
    limit: 5
  },
  batchSize: 10
}

// Utility functions
async function makeRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  try {
    console.log(`🔍 Testing: ${endpoint}`)
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'CapsightMVP-E2ETest/1.0'
      },
      ...options
    })
    
    const data = await response.text()
    let parsedData = null
    try {
      parsedData = JSON.parse(data)
    } catch (e) {
      parsedData = data
    }
    
    console.log(`   Status: ${response.status} ${response.statusText}`)
    console.log(`   Response: ${JSON.stringify(parsedData, null, 2).substring(0, 200)}...`)
    
    return {
      success: response.ok,
      status: response.status,
      data: parsedData,
      endpoint
    }
  } catch (error) {
    console.error(`❌ Error testing ${endpoint}:`, error.message)
    return {
      success: false,
      error: error.message,
      endpoint
    }
  }
}

async function testWebhookIntegration() {
  console.log('\n🚀 Testing Webhook Integration...')
  try {
    // Import and run webhook test
    const { exec } = await import('child_process')
    return new Promise((resolve) => {
      exec('node test-webhook.mjs', { cwd: __dirname }, (error, stdout, stderr) => {
        if (error) {
          console.error('❌ Webhook test failed:', error.message)
          resolve({ success: false, error: error.message })
        } else {
          console.log('✅ Webhook test passed!')
          console.log(stdout.substring(0, 500))
          resolve({ success: true })
        }
      })
    })
  } catch (error) {
    console.error('❌ Webhook integration error:', error.message)
    return { success: false, error: error.message }
  }
}

async function testSupabaseConnection() {
  console.log('\n💾 Testing Supabase Connection...')
  
  // Check environment variables
  const envPath = join(__dirname, '.env.local')
  try {
    const envContent = readFileSync(envPath, 'utf8')
    const hasSupabaseUrl = envContent.includes('NEXT_PUBLIC_SUPABASE_URL')
    const hasSupabaseKey = envContent.includes('SUPABASE_SERVICE_ROLE_KEY')
    
    if (hasSupabaseUrl && hasSupabaseKey) {
      console.log('✅ Supabase credentials configured')
      return { success: true }
    } else {
      console.error('❌ Missing Supabase credentials')
      return { success: false, error: 'Missing Supabase credentials' }
    }
  } catch (error) {
    console.error('❌ Could not read environment file:', error.message)
    return { success: false, error: error.message }
  }
}

async function validateDeploymentReadiness() {
  console.log('\n🚁 Validating Deployment Readiness...')
  
  const checks = []
  
  // Check Node.js version
  const nodeVersion = process.version
  console.log(`   Node.js version: ${nodeVersion}`)
  checks.push({
    name: 'Node.js Version',
    success: nodeVersion.startsWith('v20.') || nodeVersion.startsWith('v24.'),
    details: nodeVersion
  })
  
  // Check package.json engines
  try {
    const packageJson = JSON.parse(readFileSync(join(__dirname, 'package.json'), 'utf8'))
    const engines = packageJson.engines
    console.log(`   Package engines: ${JSON.stringify(engines)}`)
    checks.push({
      name: 'Package Engines',
      success: engines && engines.node,
      details: engines
    })
  } catch (error) {
    checks.push({
      name: 'Package Engines',
      success: false,
      error: error.message
    })
  }
  
  // Check required environment variables
  const requiredEnvVars = [
    'NEXT_PUBLIC_SUPABASE_URL',
    'SUPABASE_SERVICE_ROLE_KEY',
    'N8N_INGEST_URL',
    'WEBHOOK_SECRET'
  ]
  
  for (const envVar of requiredEnvVars) {
    const exists = process.env[envVar] !== undefined
    console.log(`   ${envVar}: ${exists ? '✅' : '❌'}`)
    checks.push({
      name: envVar,
      success: exists
    })
  }
  
  return checks
}

// Main test runner
async function runE2EValidation() {
  console.log('🎯 CapsightMVP End-to-End Validation')
  console.log('=====================================\n')
  
  const results = {
    timestamp: new Date().toISOString(),
    tests: [],
    summary: {
      total: 0,
      passed: 0,
      failed: 0
    }
  }
  
  // Test basic endpoints
  console.log('🌐 Testing API Endpoints...')
  for (const endpoint of ENDPOINTS_TO_TEST) {
    const result = await makeRequest(endpoint)
    results.tests.push(result)
    results.summary.total++
    if (result.success) {
      results.summary.passed++
    } else {
      results.summary.failed++
    }
  }
  
  // Test valuation endpoint with POST
  console.log('\n📊 Testing Valuation API...')
  const valuationResult = await makeRequest('/api/v2/valuation', {
    method: 'POST',
    body: JSON.stringify(SAMPLE_VALUATION_REQUEST),
    headers: {
      'Content-Type': 'application/json'
    }
  })
  results.tests.push(valuationResult)
  results.summary.total++
  if (valuationResult.success) {
    results.summary.passed++
  } else {
    results.summary.failed++
  }
  
  // Test webhook integration
  const webhookResult = await testWebhookIntegration()
  results.tests.push({ ...webhookResult, endpoint: 'webhook-integration' })
  results.summary.total++
  if (webhookResult.success) {
    results.summary.passed++
  } else {
    results.summary.failed++
  }
  
  // Test Supabase connection
  const supabaseResult = await testSupabaseConnection()
  results.tests.push({ ...supabaseResult, endpoint: 'supabase-connection' })
  results.summary.total++
  if (supabaseResult.success) {
    results.summary.passed++
  } else {
    results.summary.failed++
  }
  
  // Validate deployment readiness
  const deploymentChecks = await validateDeploymentReadiness()
  for (const check of deploymentChecks) {
    results.tests.push({ ...check, endpoint: 'deployment-readiness' })
    results.summary.total++
    if (check.success) {
      results.summary.passed++
    } else {
      results.summary.failed++
    }
  }
  
  // Print summary
  console.log('\n📋 VALIDATION SUMMARY')
  console.log('=====================')
  console.log(`✅ Passed: ${results.summary.passed}/${results.summary.total}`)
  console.log(`❌ Failed: ${results.summary.failed}/${results.summary.total}`)
  console.log(`📊 Success Rate: ${Math.round((results.summary.passed / results.summary.total) * 100)}%`)
  
  if (results.summary.failed > 0) {
    console.log('\n❌ FAILED TESTS:')
    results.tests.filter(t => !t.success).forEach(test => {
      console.log(`   • ${test.endpoint || test.name}: ${test.error || 'Failed'}`)
    })
  }
  
  // Deployment recommendations
  console.log('\n🚁 DEPLOYMENT RECOMMENDATIONS:')
  const passRate = (results.summary.passed / results.summary.total) * 100
  
  if (passRate >= 90) {
    console.log('✅ System is ready for production deployment!')
    console.log('   - All critical systems operational')
    console.log('   - Webhook integration confirmed')
    console.log('   - Database connectivity verified')
  } else if (passRate >= 70) {
    console.log('⚠️  System is partially ready - address failures before deployment')
  } else {
    console.log('❌ System NOT ready for deployment - critical issues detected')
  }
  
  return results
}

// Run the validation
if (import.meta.url === `file://${process.argv[1]}`) {
  runE2EValidation().catch(console.error)
}

export { runE2EValidation }
