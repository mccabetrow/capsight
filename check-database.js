// Quick script to check what's actually in your Supabase database
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

async function checkDatabase() {
  console.log('🔍 Checking Supabase database structure...')
  
  // Check what tables exist
  const { data: tables, error: tablesError } = await supabase.rpc('get_schema_tables')
  
  if (tablesError) {
    console.log('⚠️ Could not get tables via RPC, trying direct queries...')
    
    // Try to query some common table names
    const tablesToCheck = [
      'properties',
      'comparables', 
      'comps',
      'sales',
      'market_data',
      'fundamentals',
      'property_sales',
      'v_comps_trimmed',
      'market_fundamentals'
    ]
    
    for (const table of tablesToCheck) {
      try {
        const { data, error } = await supabase
          .from(table)
          .select('*')
          .limit(1)
        
        if (!error) {
          console.log(`✅ Found table: ${table}`)
          console.log(`   Sample data:`, data)
        } else {
          console.log(`❌ Table ${table} not found: ${error.message}`)
        }
      } catch (err) {
        console.log(`❌ Error checking ${table}:`, err)
      }
    }
  } else {
    console.log('📊 Available tables:', tables)
  }
}

checkDatabase().catch(console.error)
