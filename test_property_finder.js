// Simple test script for the property finder API
const testPropertyFinder = async () => {
  const testCities = ['Dallas', 'Atlanta', 'Phoenix', 'Riverside', 'Savannah']
  
  console.log('🧪 Testing Property Finder API...\n')
  
  for (const city of testCities) {
    try {
      console.log(`Testing ${city}...`)
      
      const response = await fetch('http://localhost:3000/api/predict-properties', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          city,
          investment_criteria: {
            min_sf: 75000,
            max_sf: 500000,
            target_cap_rate: 7.0
          }
        })
      })

      const data = await response.json()
      
      if (data.success) {
        console.log(`✅ ${city}: Found ${data.recommendations.length} properties`)
        console.log(`   Market: ${data.market}`)
        console.log(`   Top property: ${data.recommendations[0]?.address} (Score: ${data.recommendations[0]?.investment_score})`)
        console.log(`   Market trend: ${data.market_insights.market_trend}\n`)
      } else {
        console.log(`❌ ${city}: ${data.error}\n`)
      }
    } catch (error) {
      console.log(`❌ ${city}: ${error.message}\n`)
    }
  }
}

// Test invalid city
const testInvalidCity = async () => {
  console.log('Testing invalid city...')
  try {
    const response = await fetch('http://localhost:3000/api/predict-properties', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city: 'UnknownCity' })
    })

    const data = await response.json()
    console.log(`Invalid city result: ${data.success ? 'SUCCESS' : 'ERROR - ' + data.error}\n`)
  } catch (error) {
    console.log(`Invalid city error: ${error.message}\n`)
  }
}

// Run tests
if (typeof window === 'undefined') {
  // Node.js environment
  const fetch = require('node-fetch')
  testPropertyFinder().then(() => testInvalidCity())
} else {
  // Browser environment
  console.log('Run this in Node.js with: node test_property_finder.js')
}

module.exports = { testPropertyFinder, testInvalidCity }
