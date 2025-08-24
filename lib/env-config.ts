/**
 * ===== ENVIRONMENT VALIDATION =====
 * Validates required environment variables on application boot
 */

interface EnvConfig {
  // Node.js version
  node_version: string
  
  // Webhook configuration
  n8n_ingest_url: string
  webhook_secret: string
  tenant_id: string
  
  // Data sources
  fred_api_key: string
  supabase_url: string
  supabase_anon_key: string
  supabase_service_role_key?: string
  
  // Cache and freshness
  cache_ttl_macro_minutes: number
  freshness_macro_days: number
  freshness_fundamentals_days: number
  freshness_comps_days: number
  
  // Circuit breaker
  circuit_breaker_failure_threshold: number
  circuit_breaker_timeout_minutes: number
}

class ValidationError extends Error {
  constructor(message: string) {
    super(`Environment validation failed: ${message}`)
    this.name = 'ValidationError'
  }
}

export function validateEnvironment(): EnvConfig {
  const errors: string[] = []
  
  // Check Node.js version
  const nodeVersion = process.version
  if (!nodeVersion.startsWith('v20.')) {
    errors.push(`Node.js version must be 20.x, got ${nodeVersion}`)
  }
  
  // Required environment variables
  const required = {
    N8N_INGEST_URL: 'Webhook endpoint URL',
    WEBHOOK_SECRET: 'Webhook HMAC secret',
    FRED_API_KEY: 'FRED API key for macro data',
    NEXT_PUBLIC_SUPABASE_URL: 'Supabase project URL',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: 'Supabase anonymous key'
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
  
  // Validate webhook URL format
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
    console.error('❌ Environment validation failed:')
    errors.forEach(error => console.error(`   - ${error}`))
    throw new ValidationError(errors.join('; '))
  }
  
  const config: EnvConfig = {
    node_version: nodeVersion,
    n8n_ingest_url: webhookUrl,
    webhook_secret: webhookSecret,
    tenant_id: getEnvString('CAPSIGHT_TENANT_ID', 'demo'),
    fred_api_key: process.env.FRED_API_KEY!,
    supabase_url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
    supabase_anon_key: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    supabase_service_role_key: process.env.SUPABASE_SERVICE_ROLE_KEY,
    cache_ttl_macro_minutes: getEnvNumber('CACHE_TTL_MACRO_MINUTES', 30),
    freshness_macro_days: getEnvNumber('FRESHNESS_MACRO_DAYS', 7),
    freshness_fundamentals_days: getEnvNumber('FRESHNESS_FUNDAMENTALS_DAYS', 90),
    freshness_comps_days: getEnvNumber('FRESHNESS_COMPS_DAYS', 180),
    circuit_breaker_failure_threshold: getEnvNumber('CIRCUIT_BREAKER_FAILURE_THRESHOLD', 3),
    circuit_breaker_timeout_minutes: getEnvNumber('CIRCUIT_BREAKER_TIMEOUT_MINUTES', 2)
  }
  
  console.log('✅ Environment validation passed')
  console.log(`   Node.js: ${config.node_version}`)
  console.log(`   Tenant: ${config.tenant_id}`)
  console.log(`   Webhook: ${config.n8n_ingest_url.substring(0, 50)}...`)
  
  return config
}

// Validate on module load
let envConfig: EnvConfig | null = null

export function getEnvConfig(): EnvConfig {
  if (!envConfig) {
    envConfig = validateEnvironment()
  }
  return envConfig
}
