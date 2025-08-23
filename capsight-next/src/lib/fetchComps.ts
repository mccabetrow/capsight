import { supabase } from './supabaseClient'
import type { Comp } from './types'

export async function fetchComps(marketSlug: string): Promise<Comp[]> {
  const { data, error } = await supabase
    .from('v_verified_sales_18mo')
    .select(`
      market_slug,
      sale_date,
      submarket,
      building_sf,
      price_per_sf_usd,
      cap_rate_pct,
      data_source_url
    `)
    .eq('market_slug', marketSlug)
    .order('sale_date', { ascending: false })

  if (error) {
    console.error('Error fetching comps:', error)
    return []
  }

  return data || []
}
