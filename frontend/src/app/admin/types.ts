// Types for admin console components

export interface AccuracyMetric {
  market_slug: string
  method: string
  calc_date: string
  window_months: number
  sample_size: number
  mape: number
  rmse_bps: number
  coverage80: number
  ape_q80: number
  bias_bps: number
  last_updated: string
}

export interface AccuracyMetrics {
  overall_mae: number
  overall_sla_met: boolean
  sla_breaches: number
  last_updated: string
  markets: AccuracyMetric[]
}

export interface MarketStatus {
  market_slug: string
  enabled: boolean
  status: 'active' | 'disabled' | 'down'
  reason?: string
  updated_at: string
}

export interface ReviewQueueItem {
  id: string
  market_slug: string
  address: string
  sale_date: string
  price_total_usd: number
  building_sf: number
  cap_rate_pct: number
  reason: string
  severity: 'high' | 'medium' | 'low'
  created_at: string
  status: 'pending' | 'approved' | 'rejected'
}

export interface ReviewQueueAction {
  id: string
  review_id: string
  action: 'approve' | 'reject'
  comment?: string
  admin_user: string
  created_at: string
}

export type SLAStatus = 'pass' | 'warning' | 'critical'

export interface AccuracyCardProps {
  metrics: AccuracyMetrics | null
  isLoading: boolean
  sparklineData?: number[]
}

export interface MarketCardProps {
  market: MarketStatus
  onToggle?: (marketSlug: string, enabled: boolean, reason?: string) => Promise<void>
  onRefresh?: (marketSlug: string) => Promise<void>
}

export interface ReviewQueueItemProps {
  item: ReviewQueueItem
  onApprove: (id: string, comment?: string) => Promise<void>
  onReject: (id: string, comment: string) => Promise<void>
}
