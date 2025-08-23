import { AccuracyCardProps } from '../types'
import { getSLAStatus, getSLAStatusColor, getSLAStatusIcon, formatPercent, formatBasisPoints, formatDate } from '../lib/utils'

export default function AccuracyCard({ metrics, isLoading }: AccuracyCardProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="bg-gray-200 h-8 rounded mb-4" />
          <div className="grid grid-cols-2 gap-4 mb-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-gray-200 h-16 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500 mb-2">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Accuracy Data</h3>
        <p className="text-gray-600">
          Accuracy metrics will appear here once the nightly job runs.
        </p>
      </div>
    )
  }

  const overallSlaStatus = metrics.overall_sla_met ? 'pass' : 
    (metrics.sla_breaches > 2 ? 'critical' : 'warning')
  const statusColor = getSLAStatusColor(overallSlaStatus)
  const statusIcon = getSLAStatusIcon(overallSlaStatus)

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Overall Accuracy Status
          </h3>
          <div className={`px-3 py-1 rounded-full border text-sm font-medium ${statusColor}`}>
            <span className="mr-1">{statusIcon}</span>
            {overallSlaStatus.toUpperCase()}
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-500">Average MAPE</div>
            <div className={`text-2xl font-bold ${metrics.overall_mae <= 0.10 ? 'text-green-600' : 'text-red-600'}`}>
              {formatPercent(metrics.overall_mae)}
            </div>
            <div className="text-xs text-gray-400">Target: ≤10%</div>
          </div>
          
          <div>
            <div className="text-sm text-gray-500">SLA Breaches</div>
            <div className={`text-2xl font-bold ${metrics.sla_breaches === 0 ? 'text-green-600' : 'text-red-600'}`}>
              {metrics.sla_breaches}
            </div>
            <div className="text-xs text-gray-400">Target: 0</div>
          </div>
          
          <div>
            <div className="text-sm text-gray-500">Last Updated</div>
            <div className="text-sm font-medium text-gray-900">
              {formatDate(metrics.last_updated)}
            </div>
          </div>
        </div>
      </div>

      {/* Market Breakdown */}
      <div className="space-y-4">
        <h4 className="text-md font-medium text-gray-800">Market Breakdown</h4>
        {metrics.markets.map((metric) => {
          const marketSlaStatus = getSLAStatus(metric)
          const marketStatusColor = getSLAStatusColor(marketSlaStatus)
          const marketStatusIcon = getSLAStatusIcon(marketSlaStatus)
          
          return (
            <div key={metric.market_slug} className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h5 className="text-md font-semibold text-gray-900 uppercase">
                  {metric.market_slug}
                </h5>
                <div className={`px-2 py-1 rounded-full border text-xs font-medium ${marketStatusColor}`}>
                  <span className="mr-1">{marketStatusIcon}</span>
                  {marketSlaStatus.toUpperCase()}
                </div>
              </div>
              
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-gray-500">MAPE</div>
                  <div className={`text-lg font-bold ${metric.mape <= 0.10 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(metric.mape)}
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-500">RMSE</div>
                  <div className={`text-lg font-bold ${metric.rmse_bps <= 50 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatBasisPoints(metric.rmse_bps)}
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-500">Coverage80</div>
                  <div className={`text-lg font-bold ${
                    metric.coverage80 >= 0.78 && metric.coverage80 <= 0.82 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatPercent(metric.coverage80)}
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-500">Sample Size</div>
                  <div className="text-lg font-bold text-gray-900">
                    {metric.sample_size.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
