// CapSight UI utility functions for confidence band logic

export interface AccuracyMetrics {
  mape: number
  rmse_bps: number
  coverage80: number
  ape_q80: number
}

export interface ConfidenceBand {
  widthPct: number
  label: string
  tone: 'ok' | 'warn' | 'bad'
  status: 'ok' | 'warn' | 'bad'
}

/**
 * Decide confidence band width and styling based on accuracy metrics
 * Implements the same logic as the backend for consistency
 */
export function decideBand(acc: AccuracyMetrics): ConfidenceBand {
  const slaOk = acc.mape <= 0.10 && 
                acc.rmse_bps <= 50 && 
                acc.coverage80 >= 0.78 && 
                acc.coverage80 <= 0.82
  
  const q = Number.isFinite(acc.ape_q80) ? acc.ape_q80 : 0.10
  
  if (slaOk && q <= 0.05) {
    return { 
      widthPct: 0.05, 
      label: '±5% (SLA met)', 
      tone: 'ok',
      status: 'ok'
    }
  }
  
  if (q <= 0.08) {
    return { 
      widthPct: q, 
      label: `±${Math.round(q * 100)}% (calibrated)`, 
      tone: 'warn',
      status: 'warn'
    }
  }
  
  return { 
    widthPct: q, 
    label: `±${Math.round(q * 100)}% (low data / dispersion)`, 
    tone: 'bad',
    status: 'bad'
  }
}

/**
 * Format confidence band for display
 */
export function formatConfidenceBand(
  valuation: number, 
  interval: [number, number]
): string {
  const lower = interval[0]
  const upper = interval[1]
  const lowerPct = Math.round(((valuation - lower) / valuation) * 100)
  const upperPct = Math.round(((upper - valuation) / valuation) * 100)
  
  if (Math.abs(lowerPct - upperPct) <= 1) {
    // Symmetric band
    return `±${lowerPct}%`
  } else {
    // Asymmetric band
    return `+${upperPct}%/-${lowerPct}%`
  }
}

/**
 * Get status color classes for Tailwind
 */
export function getStatusColors(status: 'ok' | 'warn' | 'bad') {
  const colors = {
    ok: 'bg-green-100 text-green-800 border-green-200',
    warn: 'bg-yellow-100 text-yellow-800 border-yellow-200', 
    bad: 'bg-red-100 text-red-800 border-red-200'
  }
  
  return colors[status]
}

/**
 * Get status icon
 */
export function getStatusIcon(status: 'ok' | 'warn' | 'bad'): string {
  const icons = {
    ok: '✓',
    warn: '⚠',
    bad: '⚠'
  }
  
  return icons[status]
}

/**
 * Check if market is enabled and return appropriate message
 */
export function checkMarketStatus(
  marketSlug: string, 
  marketStatus?: { enabled: boolean; reason?: string }
): { enabled: boolean; message?: string } {
  if (!marketStatus) {
    return { enabled: true }
  }
  
  if (!marketStatus.enabled) {
    return {
      enabled: false,
      message: `${marketSlug.toUpperCase()} market temporarily unavailable: ${
        marketStatus.reason || 'Data quality issues'
      }`
    }
  }
  
  return { enabled: true }
}

/**
 * Format large numbers for display
 */
export function formatCurrency(value: number, compact = false): string {
  if (compact && value >= 1000000) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(value)
  }
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value)
}

/**
 * Format percentage with proper precision
 */
export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * Format basis points
 */
export function formatBasisPoints(value: number): string {
  return `${Math.round(value)} bps`
}

/**
 * Get quality assessment for sample size
 */
export function assessSampleSize(count: number): {
  status: 'good' | 'adequate' | 'low'
  message: string
} {
  if (count >= 20) {
    return { status: 'good', message: 'Large sample size' }
  } else if (count >= 10) {
    return { status: 'adequate', message: 'Adequate sample size' }
  } else {
    return { status: 'low', message: 'Small sample size - wider bands applied' }
  }
}

/**
 * Get freshness assessment for data age
 */
export function assessDataFreshness(months: number): {
  status: 'fresh' | 'acceptable' | 'stale'
  message: string
} {
  if (months <= 6) {
    return { status: 'fresh', message: 'Recent data' }
  } else if (months <= 12) {
    return { status: 'acceptable', message: 'Reasonably fresh data' }
  } else {
    return { status: 'stale', message: 'Aging data - bands widened' }
  }
}

/**
 * Get dispersion assessment
 */
export function assessDispersion(bps: number): {
  status: 'tight' | 'moderate' | 'wide'
  message: string
} {
  if (bps <= 30) {
    return { status: 'tight', message: 'Consistent comps' }
  } else if (bps <= 60) {
    return { status: 'moderate', message: 'Moderate variation' }
  } else {
    return { status: 'wide', message: 'High variation - wider bands' }
  }
}
