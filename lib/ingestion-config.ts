/**
 * ===== INGESTION PIPELINE ENVIRONMENT CONFIGURATION =====
 * Validates required environment variables for the data ingestion pipeline
 */

export interface IngestionConfig {
  // Node.js version
  node_version: string
  
  // Core services
  supabase_url: string
  supabase_service_role_key: string
  
  // Webhook configuration
  n8n_ingest_url: string
  webhook_secret: string
  
  // Geocoding services
  mapbox_token?: string
  
  // Government API keys (optional)
  acs_api_key?: string
  bls_api_key?: string
  
  // Tenant configuration
  tenant_id: string
  
  // Cache and freshness settings
  geocode_cache_ttl_days: number
  market_fundamentals_freshness_days: number
  demographics_cache_ttl_hours: number
}

class IngestionValidationError extends Error {
  constructor(message: string) {
    super(`Ingestion pipeline validation failed: ${message}`)
    this.name = 'IngestionValidationError'
  }
}

export function validateIngestionEnvironment(): IngestionConfig {
  const errors: string[] = []
  
  // Check Node.js version
  const nodeVersion = process.version
  if (!nodeVersion.startsWith('v20.')) {
    errors.push(`Node.js version must be 20.x, got ${nodeVersion}`)
  }
  
  // Required environment variables
  const required = {
    SUPABASE_URL: 'Supabase project URL',
    SUPABASE_SERVICE_ROLE_KEY: 'Supabase service role key for ingestion',
    N8N_INGEST_URL: 'n8n webhook endpoint URL for data events',
    WEBHOOK_SECRET: 'HMAC secret for webhook signatures'
  }
  
  for (const [key, description] of Object.entries(required)) {
    if (!process.env[key]) {
      errors.push(`${key} is required (${description})`)
    }
  }
  
  // Optional with defaults
  const getEnvNumber = (key: string, defaultValue: number): number => {
    const value = process.env[key]
    if (!value) return defaultValue
    const parsed = parseInt(value, 10)
    if (isNaN(parsed)) {
      errors.push(`${key} must be a number, got "${value}"`)
      return defaultValue
    }
    return parsed
  }
  
  const getEnvString = (key: string, defaultValue: string): string => {
    return process.env[key] || defaultValue
  }
  
  // Validate URLs
  const supabaseUrl = process.env.SUPABASE_URL || ''
  if (supabaseUrl && !supabaseUrl.startsWith('https://')) {
    errors.push('SUPABASE_URL must be HTTPS')
  }
  
  const webhookUrl = process.env.N8N_INGEST_URL || ''
  if (webhookUrl && !webhookUrl.startsWith('https://')) {
    errors.push('N8N_INGEST_URL must be HTTPS')
  }
  
  // Validate secret length
  const webhookSecret = process.env.WEBHOOK_SECRET || ''
  if (webhookSecret && webhookSecret.length < 16) {
    errors.push('WEBHOOK_SECRET must be at least 16 characters')
  }
  
  if (errors.length > 0) {
    console.error('❌ Ingestion pipeline environment validation failed:')
    errors.forEach(error => console.error(`   - ${error}`))
    throw new IngestionValidationError(errors.join('; '))
  }
  
  const config: IngestionConfig = {
    node_version: nodeVersion,
    supabase_url: supabaseUrl,
    supabase_service_role_key: process.env.SUPABASE_SERVICE_ROLE_KEY!,
    n8n_ingest_url: webhookUrl,
    webhook_secret: webhookSecret,
    mapbox_token: process.env.MAPBOX_TOKEN,
    acs_api_key: process.env.ACS_API_KEY,
    bls_api_key: process.env.BLS_API_KEY,
    tenant_id: getEnvString('CAPSIGHT_TENANT_ID', 'demo'),
    geocode_cache_ttl_days: getEnvNumber('GEOCODE_CACHE_TTL_DAYS', 30),
    market_fundamentals_freshness_days: getEnvNumber('MARKET_FUNDAMENTALS_FRESHNESS_DAYS', 90),
    demographics_cache_ttl_hours: getEnvNumber('DEMOGRAPHICS_CACHE_TTL_HOURS', 24)
  }
  
  console.log('✅ Ingestion pipeline environment validation passed')
  console.log(`   Node.js: ${config.node_version}`)
  console.log(`   Tenant: ${config.tenant_id}`)
  console.log(`   Supabase: ${config.supabase_url.substring(0, 30)}...`)
  console.log(`   Webhook: ${config.n8n_ingest_url.substring(0, 50)}...`)
  console.log(`   Geocoding: ${config.mapbox_token ? 'Mapbox' : 'Nominatim fallback'}`)
  
  return config
}

// Validate on module load for ingestion pipeline
let ingestionConfig: IngestionConfig | null = null

export function getIngestionConfig(): IngestionConfig {
  if (!ingestionConfig) {
    ingestionConfig = validateIngestionEnvironment()
  }
  return ingestionConfig
}
