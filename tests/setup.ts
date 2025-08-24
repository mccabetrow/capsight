/**
 * Jest test setup
 */

// Mock environment variables for testing
process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test-project.supabase.co'
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-key'
process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-service-key'
process.env.FRED_API_KEY = 'test-fred-key'
process.env.N8N_WEBHOOK_URL = 'https://test-n8n.com/webhook/capsight'
process.env.WEBHOOK_SECRET = 'test-webhook-secret'
process.env.TENANT_ID = 'test-tenant'

// Global test timeout
jest.setTimeout(30000)
