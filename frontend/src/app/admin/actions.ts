'use server'

import { createAdminClient } from './lib/supabase-admin'
import { revalidatePath } from 'next/cache'

// Accuracy data actions
export async function getAccuracyMetrics() {
  const supabase = createAdminClient()
  
  const { data, error } = await supabase
    .from('latest_accuracy')
    .select('*')
    .order('market_slug')
  
  if (error) {
    console.error('Failed to fetch accuracy metrics:', error)
    throw new Error('Failed to fetch accuracy metrics')
  }
  
  // Transform to expected format
  const markets = data || []
  const slaThreshold = 0.15 // 15% MAPE threshold
  const slaBreaches = markets.filter((m: any) => m.mape > slaThreshold).length
  
  const overallMae = markets.length > 0 
    ? markets.reduce((sum: number, m: any) => sum + m.mape, 0) / markets.length 
    : 0
  
  return {
    overall_mae: overallMae,
    overall_sla_met: slaBreaches === 0,
    sla_breaches: slaBreaches,
    last_updated: markets.length > 0 ? markets[0].last_updated : new Date().toISOString(),
    markets
  }
}

// Export alias for compatibility
export const getMarketStatus = getMarketStatuses

// Export alias for compatibility  
export const getReviewQueue = getReviewQueueItems

export async function getAccuracyHistory(marketSlug: string, days = 30) {
  const supabase = createAdminClient()
  
  const { data, error } = await supabase
    .from('accuracy_metrics')
    .select('calc_date, mape, rmse_bps, coverage80')
    .eq('market_slug', marketSlug)
    .gte('calc_date', new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0])
    .order('calc_date', { ascending: true })
  
  if (error) {
    console.error(`Failed to fetch accuracy history for ${marketSlug}:`, error)
    return []
  }
  
  return data || []
}

// Market management actions
export async function getMarketStatuses() {
  const supabase = createAdminClient()
  
  const { data, error } = await supabase
    .from('market_status')
    .select('*')
    .order('market_slug')
  
  if (error) {
    console.error('Failed to fetch market statuses:', error)
    throw new Error('Failed to fetch market statuses')
  }
  
  // Transform to include status field
  return (data || []).map((market: any) => ({
    ...market,
    status: market.enabled ? 'active' as const : 'disabled' as const
  }))
}

export async function updateMarketStatus(
  marketSlug: string, 
  enabled: boolean, 
  reason?: string
) {
  const supabase = createAdminClient()
  
  const { error } = await supabase
    .from('market_status')
    .upsert({
      market_slug: marketSlug,
      enabled,
      reason: reason || null,
      updated_at: new Date().toISOString()
    })
  
  if (error) {
    console.error(`Failed to update market status for ${marketSlug}:`, error)
    throw new Error('Failed to update market status')
  }
  
  revalidatePath('/admin')
}

export async function refreshMaterializedView() {
  const supabase = createAdminClient()
  
  const { error } = await supabase.rpc('refresh_recent_mv')
  
  if (error) {
    console.error('Failed to refresh materialized view:', error)
    throw new Error('Failed to refresh materialized view')
  }
  
  revalidatePath('/admin')
}

// Review queue actions
export async function getReviewQueueItems() {
  const supabase = createAdminClient()
  
  // First, let's check if we have a review queue table
  const { data, error } = await supabase
    .from('comp_review_queue')
    .select('*')
    .eq('status', 'pending')
    .order('created_at', { ascending: false })
    .limit(100)
  
  if (error) {
    console.error('Failed to fetch review queue items:', error)
    // Return empty array if table doesn't exist yet
    return []
  }
  
  return data || []
}

export async function approveReviewItem(id: string, comment?: string) {
  const supabase = createAdminClient()
  
  // Update the review queue item status
  const { error: updateError } = await supabase
    .from('comp_review_queue')
    .update({ status: 'approved' })
    .eq('id', id)
  
  if (updateError) {
    console.error(`Failed to approve review item ${id}:`, updateError)
    throw new Error('Failed to approve review item')
  }
  
  // Log the action
  const { error: logError } = await supabase
    .from('review_queue_actions')
    .insert({
      review_id: id,
      action: 'approve',
      comment: comment || null,
      admin_user: 'admin', // In a real app, this would be the logged-in user
      created_at: new Date().toISOString()
    })
  
  if (logError) {
    console.error(`Failed to log approval action for ${id}:`, logError)
    // Don't throw here, the main action succeeded
  }
  
  revalidatePath('/admin')
}

export async function rejectReviewItem(id: string, comment: string) {
  const supabase = createAdminClient()
  
  // Update the review queue item status
  const { error: updateError } = await supabase
    .from('comp_review_queue')
    .update({ status: 'rejected' })
    .eq('id', id)
  
  if (updateError) {
    console.error(`Failed to reject review item ${id}:`, updateError)
    throw new Error('Failed to reject review item')
  }
  
  // Log the action
  const { error: logError } = await supabase
    .from('review_queue_actions')
    .insert({
      review_id: id,
      action: 'reject',
      comment,
      admin_user: 'admin', // In a real app, this would be the logged-in user
      created_at: new Date().toISOString()
    })
  
  if (logError) {
    console.error(`Failed to log rejection action for ${id}:`, logError)
    // Don't throw here, the main action succeeded
  }
  
  revalidatePath('/admin')
}
