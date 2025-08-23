import { supabase } from './supabaseClient'
import type { Fundamentals } from './types'

export async function fetchFundamentals(marketSlug: string): Promise<Fundamentals | null> {
  const { data, error } = await supabase
    .from('v_market_fundamentals_latest')
    .select(`
      market_slug,
      as_of_date,
      vacancy_rate_pct,
      avg_asking_rent_psf_yr_nnn,
      yoy_rent_growth_pct,
      under_construction_sf,
      net_absorption_sf_ytd,
      cap_rate_stabilized_median_pct,
      source_name,
      source_url,
      source_date
    `)
    .eq('market_slug', marketSlug)
    .single()

  if (error) {
    console.error('Error fetching fundamentals:', error)
    return null
  }

  return data
}
