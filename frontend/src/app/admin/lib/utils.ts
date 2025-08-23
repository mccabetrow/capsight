import { AccuracyMetric, SLAStatus } from '../types'

export function getSLAStatus(metric: AccuracyMetric): SLAStatus {
  const slaPass = metric.mape <= 0.10 && 
                  metric.rmse_bps <= 50 && 
                  metric.coverage80 >= 0.78 && 
                  metric.coverage80 <= 0.82

  if (slaPass) return 'pass'
  
  // Critical violations
  if (metric.mape > 0.15 || metric.rmse_bps > 75 || metric.coverage80 < 0.70 || metric.coverage80 > 0.90) {
    return 'critical'
  }
  
  return 'warning'
}

export function getSLAStatusColor(status: SLAStatus): string {
  switch (status) {
    case 'pass':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'warning':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'critical':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

export function getSLAStatusIcon(status: SLAStatus): string {
  switch (status) {
    case 'pass':
      return '✓'
    case 'warning':
      return '⚠'
    case 'critical':
      return '✗'
    default:
      return '?'
  }
}

export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}

export function formatBasisPoints(value: number): string {
  return `${Math.round(value)} bps`
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function getTimeSince(dateString: string): string {
  const now = new Date()
  const date = new Date(dateString)
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffHours < 1) return 'Just now'
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
  
  return formatDate(dateString)
}
