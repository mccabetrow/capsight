import { cn } from '@/lib/format'

interface KpiProps {
  label: string
  value: string | number | null
  tooltip?: string
  format?: 'currency' | 'percent' | 'number' | 'sf'
}

export default function Kpi({ label, value, tooltip, format = 'number' }: KpiProps) {
  const formatValue = (val: string | number | null) => {
    if (val === null || val === undefined) return 'N/A'
    if (typeof val === 'string') return val
    
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(val)
      case 'percent':
        return new Intl.NumberFormat('en-US', {
          style: 'percent',
          minimumFractionDigits: 1,
          maximumFractionDigits: 1,
        }).format(val / 100)
      case 'sf':
        if (val >= 1000000) {
          return `${(val / 1000000).toFixed(1)}M`
        } else if (val >= 1000) {
          return `${(val / 1000).toFixed(0)}K`
        }
        return val.toLocaleString()
      default:
        return val.toLocaleString()
    }
  }

  return (
    <div className="flex flex-col space-y-1">
      <div className="flex items-center space-x-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        {tooltip && (
          <span 
            className="text-gray-400 hover:text-gray-600 cursor-help"
            title={tooltip}
            aria-label={tooltip}
          >
            ℹ
          </span>
        )}
      </div>
      <span 
        className={cn(
          "text-2xl font-semibold",
          value === null ? "text-gray-400" : "text-gray-900"
        )}
      >
        {formatValue(value)}
      </span>
    </div>
  )
}
