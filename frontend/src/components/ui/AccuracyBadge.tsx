import React from 'react'

interface AccuracyBadgeProps {
  confidence_band: {
    width_pct: number
    label: string
    status: 'ok' | 'warn' | 'bad'
  }
  quality_indicators: {
    sample_size: number
    data_freshness_months: number
    dispersion_bps: number
    fallback_reason?: string
  }
}

export default function AccuracyBadge({ confidence_band, quality_indicators }: AccuracyBadgeProps) {
  const { status, label, width_pct } = confidence_band
  const { sample_size, data_freshness_months, dispersion_bps, fallback_reason } = quality_indicators
  
  const statusColors = {
    ok: 'bg-green-100 text-green-800 border-green-200',
    warn: 'bg-yellow-100 text-yellow-800 border-yellow-200', 
    bad: 'bg-red-100 text-red-800 border-red-200'
  }
  
  const statusIcons = {
    ok: '✓',
    warn: '⚠',
    bad: '⚠'
  }
  
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
      <div className="flex items-center space-x-3">
        <div className={`px-3 py-1 rounded-full border text-sm font-medium ${statusColors[status]}`}>
          <span className="mr-1">{statusIcons[status]}</span>
          {label}
        </div>
        <div className="text-sm text-gray-600">
          {Math.round(width_pct * 100)}% confidence band
        </div>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <div className="text-gray-500">Sample Size</div>
          <div className="font-medium">{sample_size} comps</div>
        </div>
        <div>
          <div className="text-gray-500">Data Freshness</div>
          <div className="font-medium">{data_freshness_months.toFixed(1)}m avg</div>
        </div>
        <div>
          <div className="text-gray-500">Dispersion</div>
          <div className="font-medium">{dispersion_bps} bps</div>
        </div>
        <div>
          <div className="text-gray-500">Status</div>
          <div className="font-medium capitalize">
            {fallback_reason ? fallback_reason : 'Normal'}
          </div>
        </div>
      </div>
      
      {fallback_reason && (
        <div className="bg-amber-50 border border-amber-200 rounded p-2 text-sm text-amber-800">
          <strong>Note:</strong> {fallback_reason} detected. Confidence band widened for safety.
        </div>
      )}
    </div>
  )
}
