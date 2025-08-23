import { createClient } from '@supabase/supabase-js'

// Browser-safe client (uses anon key)
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY! // browser-safe key
)

// Server-side client (uses service role)
export const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE!, // server-only key
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  }
)

// Market slug to name mapping
export const MARKET_LABELS = {
  dfw: 'Dallas-Fort Worth',
  ie: 'Inland Empire',
  atl: 'Atlanta',
  phx: 'Phoenix',
  sav: 'Savannah'
} as const

export type MarketSlug = keyof typeof MARKET_LABELS
