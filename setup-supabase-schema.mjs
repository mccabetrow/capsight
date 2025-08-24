/**
 * ===== SUPABASE SCHEMA SETUP =====
 * Creates the required database schema for CapsightMVP
 */

import { createClient } from '@supabase/supabase-js'
import { readFileSync } from 'fs'

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

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)

// SQL Schema for CapsightMVP
const SCHEMA_SQL = `
-- Properties table for storing valuations and property data
CREATE TABLE IF NOT EXISTS properties (
  id SERIAL PRIMARY KEY,
  market_slug TEXT NOT NULL,
  address TEXT NOT NULL,
  building_sf INTEGER,
  estimated_value DECIMAL(15,2),
  confidence_score DECIMAL(4,3),
  deal_score INTEGER,
  classification TEXT CHECK (classification IN ('BUY', 'HOLD', 'AVOID')),
  noi_annual DECIMAL(15,2),
  cap_rate_applied DECIMAL(5,4),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market fundamentals table
CREATE TABLE IF NOT EXISTS market_fundamentals (
  id SERIAL PRIMARY KEY,
  market_slug TEXT UNIQUE NOT NULL,
  city TEXT NOT NULL,
  avg_cap_rate_pct DECIMAL(5,2),
  avg_asking_rent_psf_yr_nnn DECIMAL(8,2),
  vacancy_rate_pct DECIMAL(5,2),
  rent_growth_yoy_pct DECIMAL(5,2),
  under_construction_sf BIGINT,
  absorption_sf_ytd BIGINT,
  inventory_sf BIGINT,
  as_of_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comparables/comps table
CREATE TABLE IF NOT EXISTS comp_sales (
  id SERIAL PRIMARY KEY,
  market_slug TEXT NOT NULL,
  address TEXT NOT NULL,
  building_sf INTEGER,
  price_per_sf_usd DECIMAL(8,2),
  sale_price_usd DECIMAL(15,2),
  cap_rate_pct DECIMAL(5,4),
  noi_annual DECIMAL(15,2),
  sale_date DATE,
  submarket TEXT,
  building_class TEXT,
  year_built INTEGER,
  occupancy_pct DECIMAL(5,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ingestion events table for tracking data pipeline
CREATE TABLE IF NOT EXISTS ingestion_events (
  id SERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  connector TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
  records_processed INTEGER DEFAULT 0,
  properties_created INTEGER DEFAULT 0,
  webhooks_sent INTEGER DEFAULT 0,
  error_message TEXT,
  metadata JSONB,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Webhook delivery log
CREATE TABLE IF NOT EXISTS webhook_deliveries (
  id SERIAL PRIMARY KEY,
  request_id TEXT UNIQUE NOT NULL,
  url TEXT NOT NULL,
  payload_type TEXT NOT NULL,
  status_code INTEGER,
  response_body TEXT,
  delivery_time_ms INTEGER,
  attempt_number INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  delivered_at TIMESTAMPTZ
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_properties_market ON properties(market_slug);
CREATE INDEX IF NOT EXISTS idx_properties_classification ON properties(classification);
CREATE INDEX IF NOT EXISTS idx_properties_deal_score ON properties(deal_score DESC);
CREATE INDEX IF NOT EXISTS idx_comp_sales_market ON comp_sales(market_slug);
CREATE INDEX IF NOT EXISTS idx_comp_sales_date ON comp_sales(sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_events_connector ON ingestion_events(connector);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_request_id ON webhook_deliveries(request_id);

-- Enable Row Level Security (RLS)
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_fundamentals ENABLE ROW LEVEL SECURITY;
ALTER TABLE comp_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;

-- Create policies (allow service role full access)
CREATE POLICY IF NOT EXISTS "Service role full access" ON properties FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access" ON market_fundamentals FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access" ON comp_sales FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access" ON ingestion_events FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS "Service role full access" ON webhook_deliveries FOR ALL USING (true);
`

async function createSchema() {
  console.log('🏗️  Creating CapsightMVP Database Schema...')
  console.log('============================================\n')
  
  try {
    // Execute the schema SQL
    const { data, error } = await supabase.rpc('execute_sql', { 
      sql: SCHEMA_SQL 
    })
    
    if (error) {
      console.error('❌ Schema creation failed:', error.message)
      
      // Try executing individual statements
      console.log('🔄 Trying individual table creation...')
      
      const statements = SCHEMA_SQL.split(';').filter(s => s.trim())
      let successCount = 0
      
      for (const statement of statements) {
        if (statement.trim()) {
          try {
            await supabase.rpc('execute_sql', { sql: statement.trim() + ';' })
            successCount++
          } catch (err) {
            console.log(`⚠️  Statement failed: ${statement.substring(0, 50)}...`)
          }
        }
      }
      
      console.log(`✅ Successfully executed ${successCount} statements`)
      return false
    }
    
    console.log('✅ Schema created successfully!')
    return true
    
  } catch (error) {
    console.error('❌ Schema creation error:', error.message)
    
    // Fallback: try direct SQL execution via client
    console.log('🔄 Trying direct SQL execution...')
    
    try {
      // Create tables one by one
      await supabase.from('_').select('1').limit(1) // Test connection
      
      console.log('✅ Connection working - schema should be created manually in Supabase dashboard')
      console.log('\n📋 MANUAL SCHEMA CREATION REQUIRED:')
      console.log('===================================')
      console.log('Copy the following SQL to your Supabase SQL Editor:')
      console.log('\n```sql')
      console.log(SCHEMA_SQL)
      console.log('```\n')
      
      return false
    } catch (err) {
      console.error('❌ Connection test failed:', err.message)
      return false
    }
  }
}

async function verifySchema() {
  console.log('✅ Verifying schema creation...')
  
  const tables = ['properties', 'market_fundamentals', 'comp_sales', 'ingestion_events', 'webhook_deliveries']
  const results = []
  
  for (const table of tables) {
    try {
      const { data, error } = await supabase.from(table).select('*').limit(1)
      
      if (error) {
        console.log(`❌ Table '${table}' not accessible: ${error.message}`)
        results.push({ table, success: false, error: error.message })
      } else {
        console.log(`✅ Table '${table}' exists and accessible`)
        results.push({ table, success: true })
      }
    } catch (err) {
      console.log(`❌ Table '${table}' verification failed: ${err.message}`)
      results.push({ table, success: false, error: err.message })
    }
  }
  
  const successful = results.filter(r => r.success).length
  console.log(`\n📊 Schema Verification: ${successful}/${tables.length} tables accessible`)
  
  return successful === tables.length
}

async function runSchemaSetup() {
  const created = await createSchema()
  const verified = await verifySchema()
  
  if (verified) {
    console.log('\n🎉 SCHEMA SETUP COMPLETE!')
    console.log('   - All tables created and accessible')
    console.log('   - Indexes and policies configured')
    console.log('   - Ready for data ingestion and testing')
  } else if (created) {
    console.log('\n⚠️  SCHEMA PARTIALLY CREATED')
    console.log('   - Some tables may need manual verification')
    console.log('   - Check Supabase dashboard for details')
  } else {
    console.log('\n❌ SCHEMA SETUP REQUIRED')
    console.log('   - Manual setup needed in Supabase dashboard')
    console.log('   - Copy the SQL schema above to SQL Editor')
  }
}

runSchemaSetup().catch(console.error)
