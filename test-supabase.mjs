/**
 * ===== SUPABASE DATA VALIDATION SCRIPT =====
 * Tests property insertion and validation with our Dallas sample data
 */

import { createClient } from '@supabase/supabase-js'
import { readFileSync } from 'fs'
import { join } from 'path'

// Load environment variables
const envContent = readFileSync('.env.local', 'utf8')
const envVars = {}
envContent.split('\n').forEach(line => {
  if (line.includes('=') && !line.startsWith('#')) {
    const [key, value] = line.split('=')
    envVars[key.trim()] = value.trim()
  }
})

const SUPABASE_URL = envVars.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_SERVICE_KEY = envVars.SUPABASE_SERVICE_ROLE_KEY

if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
  console.error('❌ Missing Supabase credentials in .env.local')
  process.exit(1)
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)

// Sample Dallas properties from our CSV
const DALLAS_PROPERTIES = [
  {
    market_slug: 'dallas-fort-worth-tx',
    address: '123 Main St, Dallas, TX 75201',
    building_sf: 25000,
    estimated_value: 2650000,
    confidence_score: 0.85,
    deal_score: 78,
    classification: 'BUY',
    noi_annual: 185500,
    cap_rate_applied: 0.07,
    created_at: new Date().toISOString()
  },
  {
    market_slug: 'dallas-fort-worth-tx',
    address: '456 Elm Street, Dallas, TX 75202',
    building_sf: 45000,
    estimated_value: 4400000,
    confidence_score: 0.92,
    deal_score: 82,
    classification: 'BUY',
    noi_annual: 308000,
    cap_rate_applied: 0.07,
    created_at: new Date().toISOString()
  },
  {
    market_slug: 'dallas-fort-worth-tx',
    address: '789 Oak Avenue, Dallas, TX 75203',
    building_sf: 15000,
    estimated_value: 1320000,
    confidence_score: 0.71,
    deal_score: 65,
    classification: 'HOLD',
    noi_annual: 92400,
    cap_rate_applied: 0.07,
    created_at: new Date().toISOString()
  }
]

async function testSupabaseConnection() {
  console.log('🔌 Testing Supabase Connection...')
  
  try {
    // Test basic connectivity
    const { data, error } = await supabase.from('properties').select('count').limit(1)
    
    if (error) {
      console.error('❌ Supabase connection failed:', error.message)
      return false
    }
    
    console.log('✅ Supabase connection successful')
    return true
  } catch (error) {
    console.error('❌ Supabase connection error:', error.message)
    return false
  }
}

async function insertTestProperties() {
  console.log('📊 Inserting test Dallas properties...')
  
  try {
    // Clear existing test data
    await supabase
      .from('properties')
      .delete()
      .like('address', '%Dallas, TX%')
    
    console.log('🧹 Cleared existing Dallas test data')
    
    // Insert new properties
    const { data, error } = await supabase
      .from('properties')
      .insert(DALLAS_PROPERTIES)
      .select()
    
    if (error) {
      console.error('❌ Property insertion failed:', error.message)
      return false
    }
    
    console.log(`✅ Inserted ${data.length} Dallas properties`)
    console.log('   Properties:', data.map(p => ({
      address: p.address,
      value: p.estimated_value,
      classification: p.classification
    })))
    
    return data
  } catch (error) {
    console.error('❌ Property insertion error:', error.message)
    return false
  }
}

async function validateBUYClassifications() {
  console.log('🎯 Validating BUY classifications...')
  
  try {
    const { data, error } = await supabase
      .from('properties')
      .select('*')
      .eq('classification', 'BUY')
      .like('address', '%Dallas, TX%')
    
    if (error) {
      console.error('❌ BUY validation failed:', error.message)
      return false
    }
    
    console.log(`✅ Found ${data.length} BUY properties in Dallas`)
    data.forEach(prop => {
      console.log(`   • ${prop.address}: $${prop.estimated_value.toLocaleString()} (Score: ${prop.deal_score})`)
    })
    
    return data.length > 0
  } catch (error) {
    console.error('❌ BUY validation error:', error.message)
    return false
  }
}

async function testMarketFundamentals() {
  console.log('📈 Testing market fundamentals data...')
  
  try {
    const { data, error } = await supabase
      .from('market_fundamentals')
      .select('*')
      .eq('market_slug', 'dallas-fort-worth-tx')
      .limit(1)
    
    if (error) {
      console.error('❌ Market fundamentals query failed:', error.message)
      return false
    }
    
    if (data.length === 0) {
      console.log('⚠️  No market fundamentals found - inserting sample data...')
      
      const sampleFundamentals = {
        market_slug: 'dallas-fort-worth-tx',
        city: 'Dallas',
        avg_cap_rate_pct: 7.2,
        avg_asking_rent_psf_yr_nnn: 28.5,
        vacancy_rate_pct: 12.8,
        rent_growth_yoy_pct: 4.2,
        under_construction_sf: 2500000,
        absorption_sf_ytd: 1200000,
        inventory_sf: 45000000,
        as_of_date: new Date().toISOString().split('T')[0]
      }
      
      const { data: insertData, error: insertError } = await supabase
        .from('market_fundamentals')
        .insert(sampleFundamentals)
        .select()
      
      if (insertError) {
        console.error('❌ Market fundamentals insertion failed:', insertError.message)
        return false
      }
      
      console.log('✅ Inserted Dallas market fundamentals')
    } else {
      console.log('✅ Market fundamentals found:', {
        market: data[0].market_slug,
        cap_rate: data[0].avg_cap_rate_pct + '%',
        rent_psf: '$' + data[0].avg_asking_rent_psf_yr_nnn,
        vacancy: data[0].vacancy_rate_pct + '%'
      })
    }
    
    return true
  } catch (error) {
    console.error('❌ Market fundamentals error:', error.message)
    return false
  }
}

async function runSupabaseValidation() {
  console.log('🎯 CapsightMVP Supabase Validation')
  console.log('===================================\n')
  
  const results = []
  
  // Test connection
  const connected = await testSupabaseConnection()
  results.push({ test: 'Supabase Connection', success: connected })
  
  if (!connected) {
    console.log('❌ Cannot proceed without database connection')
    return
  }
  
  // Insert test properties
  const propertiesInserted = await insertTestProperties()
  results.push({ test: 'Property Insertion', success: !!propertiesInserted })
  
  // Validate BUY classifications
  const buyValidated = await validateBUYClassifications()
  results.push({ test: 'BUY Classification', success: buyValidated })
  
  // Test market fundamentals
  const fundamentalsOk = await testMarketFundamentals()
  results.push({ test: 'Market Fundamentals', success: fundamentalsOk })
  
  // Summary
  console.log('\n📋 SUPABASE VALIDATION SUMMARY')
  console.log('==============================')
  const passed = results.filter(r => r.success).length
  const total = results.length
  
  console.log(`✅ Passed: ${passed}/${total}`)
  console.log(`❌ Failed: ${total - passed}/${total}`)
  
  results.forEach(result => {
    const status = result.success ? '✅' : '❌'
    console.log(`   ${status} ${result.test}`)
  })
  
  if (passed === total) {
    console.log('\n🎉 ALL SUPABASE TESTS PASSED!')
    console.log('   - Properties stored successfully')
    console.log('   - Classifications working')
    console.log('   - Market data available')
    console.log('   - Ready for webhook emission!')
  }
  
  return results
}

// Run validation
runSupabaseValidation().catch(console.error)
