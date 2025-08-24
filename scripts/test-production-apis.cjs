#!/usr/bin/env node
/**
 * 🧪 PRODUCTION API TEST SUITE
 * Test live endpoints after Vercel deployment
 */

const BASE_URL = process.env.VERCEL_URL || 'https://capsight.vercel.app'

console.log('🚀 Testing Production CapSight APIs')
console.log(`Base URL: ${BASE_URL}`)
console.log('=' .repeat(60))

async function testHealthEndpoint() {
  console.log('\n🩺 Testing Health Endpoint...')
  
  try {
    const response = await fetch(`${BASE_URL}/api/health/data-v2`)
    const data = await response.json()
    
    console.log(`Status: ${response.status}`)
    console.log(`Overall Status: ${data.status}`)
    console.log(`Cache Hit Ratio: ${(data.cache?.hit_ratio_24h * 100).toFixed(1)}%`)
    console.log(`Circuit Breakers: Macro ${data.circuit_breakers?.macro?.state}, Supabase ${data.circuit_breakers?.supabase?.state}`)
    console.log(`Memory Usage: ${data.system?.memory_usage_mb}MB`)
    console.log(`Node Version: ${data.system?.node_version}`)
    
    if (data.status === 'HEALTHY') {
      console.log('✅ Health check PASSED')
    } else {
      console.log('⚠️ Health check shows degraded/down status')
    }
    
  } catch (error) {
    console.log('❌ Health check FAILED:', error.message)
  }
}

async function testValuationEndpoint() {
  console.log('\n💰 Testing Valuation Endpoint...')
  
  const testCases = [
    {
      name: 'Dallas Office Building',
      payload: {
        market: 'dallas',
        building_sf: 100000,
        noi_annual: 6500000,
        debug: true
      }
    },
    {
      name: 'Austin Office Building',
      payload: {
        market: 'austin', 
        building_sf: 75000,
        noi_annual: 4800000
      }
    },
    {
      name: 'Houston Office Building',
      payload: {
        market: 'houston',
        building_sf: 120000,
        noi_annual: 7200000
      }
    }
  ]
  
  for (const testCase of testCases) {
    console.log(`\n📊 ${testCase.name}:`)
    
    try {
      const startTime = Date.now()
      
      const response = await fetch(`${BASE_URL}/api/v2/valuation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testCase.payload)
      })
      
      const endTime = Date.now()
      const data = await response.json()
      
      if (response.ok) {
        console.log(`  ✅ Status: ${response.status}`)
        console.log(`  💵 Value: $${data.estimated_value?.toLocaleString()}`)
        console.log(`  📈 Range: $${data.estimated_value_range?.low?.toLocaleString()} - $${data.estimated_value_range?.high?.toLocaleString()}`)
        console.log(`  🎯 Cap Rate: ${data.cap_rate_applied}%`)
        console.log(`  📊 Confidence: ${(data.confidence_score * 100).toFixed(1)}%`)
        console.log(`  🏢 Price/SF: $${data.price_per_sf}`)
        console.log(`  ⏱️ Response Time: ${endTime - startTime}ms`)
        console.log(`  📊 Status: ${data.valuation_status}`)
        console.log(`  🔗 Request ID: ${data.request_id}`)
        
        if (data.debug) {
          console.log(`  🔍 Macro Data Source: ${data.debug.macro_raw ? 'FRED' : 'None'}`)
          console.log(`  🔍 Fundamentals: ${data.debug.fundamentals_raw ? 'Supabase' : 'None'}`)
          console.log(`  🔍 Comps Count: ${data.debug.comps_raw?.length || 0}`)
        }
        
      } else {
        console.log(`  ❌ Error ${response.status}: ${data.error}`)
      }
      
    } catch (error) {
      console.log(`  ❌ Request failed: ${error.message}`)
    }
  }
}

async function testDataFreshness() {
  console.log('\n📅 Testing Data Freshness...')
  
  try {
    // Test with debug enabled to see data sources
    const response = await fetch(`${BASE_URL}/api/v2/valuation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        market: 'dallas',
        building_sf: 50000,
        noi_annual: 3000000,
        debug: true
      })
    })
    
    const data = await response.json()
    
    if (data.provenance) {
      console.log('📊 Data Provenance:')
      console.log(`  Macro: ${data.provenance.macro.source} (${data.provenance.macro.as_of})`)
      console.log(`  Fundamentals: ${data.provenance.fundamentals.source} (${data.provenance.fundamentals.as_of})`)
      console.log(`  Comps: ${data.provenance.comps.source} (${data.provenance.comps.as_of})`)
    }
    
    if (data.freshness_summary) {
      console.log('⏰ Data Freshness:')
      console.log(`  Macro: ${data.freshness_summary.macro.status} (${data.freshness_summary.macro.days_old} days old)`)
      console.log(`  Fundamentals: ${data.freshness_summary.fundamentals.status} (${data.freshness_summary.fundamentals.days_old} days old)`)
      console.log(`  Comps: ${data.freshness_summary.comps.status} (${data.freshness_summary.comps.days_old} days old)`)
    }
    
  } catch (error) {
    console.log('❌ Data freshness test failed:', error.message)
  }
}

async function testPerformance() {
  console.log('\n⚡ Performance Test...')
  
  const requests = []
  const concurrency = 3
  
  console.log(`Making ${concurrency} concurrent requests...`)
  
  for (let i = 0; i < concurrency; i++) {
    const request = fetch(`${BASE_URL}/api/v2/valuation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        market: 'dallas',
        building_sf: 80000,
        noi_annual: 5000000
      })
    }).then(async (response) => {
      const start = Date.now()
      const data = await response.json()
      const end = Date.now()
      return { status: response.status, time: end - start, calculation_time: data.calculation_time_ms }
    })
    
    requests.push(request)
  }
  
  try {
    const results = await Promise.all(requests)
    
    const responseTimes = results.map(r => r.time)
    const calculationTimes = results.map(r => r.calculation_time).filter(t => t)
    
    console.log(`📊 Results (${results.length} requests):`)
    console.log(`  Response Times: ${responseTimes.join('ms, ')}ms`)
    console.log(`  Calculation Times: ${calculationTimes.join('ms, ')}ms`)
    console.log(`  Average Response: ${Math.round(responseTimes.reduce((a, b) => a + b) / responseTimes.length)}ms`)
    console.log(`  Max Response: ${Math.max(...responseTimes)}ms`)
    
    const slaPass = Math.max(...responseTimes) < 5000
    console.log(`  SLA (<5s): ${slaPass ? '✅ PASS' : '❌ FAIL'}`)
    
  } catch (error) {
    console.log('❌ Performance test failed:', error.message)
  }
}

// Run all tests
async function runAllTests() {
  await testHealthEndpoint()
  await testValuationEndpoint()
  await testDataFreshness()
  await testPerformance()
  
  console.log('\n' + '='.repeat(60))
  console.log('🎯 Production API Testing Complete!')
  console.log('\nNext steps:')
  console.log('1. ✅ Verify all endpoints are working')
  console.log('2. 🔗 Test webhook delivery to n8n')
  console.log('3. 📊 Monitor performance in Vercel dashboard')
  console.log('4. 🧪 Run contract tests: npm test')
}

// Execute if run directly
if (require.main === module) {
  runAllTests().catch(console.error)
}

module.exports = {
  testHealthEndpoint,
  testValuationEndpoint,
  testDataFreshness,
  testPerformance,
  runAllTests
}
