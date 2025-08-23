# Vercel Environment Variables Setup Guide
# Copy these values into Vercel Dashboard → Settings → Environment Variables

# =============================================================================
# REQUIRED VARIABLES (Production + Preview)
# =============================================================================

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://azwkiifefkwewruyplcj.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-actual-anon-key-from-supabase
SUPABASE_SERVICE_ROLE_KEY=your-actual-service-role-key-from-supabase

# Admin Access
ADMIN_TOKEN=generate-secure-random-token-here

# Sentry Error Monitoring (if using Sentry)
SENTRY_DSN=your-sentry-dsn-here
NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn-here

# API Configuration
NEXT_PUBLIC_API_BASE_URL=https://your-production-api-domain.com

# =============================================================================
# OPTIONAL VARIABLES (if using Upstash Redis for rate limiting)
# =============================================================================

UPSTASH_REDIS_REST_URL=your-upstash-redis-url
UPSTASH_REDIS_REST_TOKEN=your-upstash-redis-token

# Performance Testing
PERF_BASE_URL=https://your-production-domain.vercel.app

# =============================================================================
# HOW TO SET IN VERCEL:
# =============================================================================

# 1. Go to vercel.com → Your Project → Settings → Environment Variables
# 2. Click "Add New" for each variable above
# 3. Set Environment: Production (and Preview if needed)
# 4. Value: Copy the actual values from your Supabase dashboard
# 5. Click "Save"

# =============================================================================
# GET YOUR SUPABASE KEYS:
# =============================================================================

# 1. Go to supabase.com → Your Project → Settings → API
# 2. Copy "Project URL" for NEXT_PUBLIC_SUPABASE_URL
# 3. Copy "anon public" key for NEXT_PUBLIC_SUPABASE_ANON_KEY  
# 4. Copy "service_role secret" key for SUPABASE_SERVICE_ROLE_KEY (⚠️ Keep secret!)

# =============================================================================
# GENERATE ADMIN TOKEN:
# =============================================================================

# Run this command to generate a secure admin token:
# node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
