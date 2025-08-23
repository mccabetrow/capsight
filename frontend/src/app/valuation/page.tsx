'use client'

import { useState } from 'react'
import { useDemo } from '@/hooks/useDemo'
import CalculationModal from '@/components/ui/CalculationModal'

interface ValuationResult {
  valuation_total_usd: number
  valuation_low_usd: number
  valuation_high_usd: number
  implied_cap_rate: number
  market_slug: string
  method: string
  method_version: string
  confidence_level: number
  comp_count: number
  outliers_removed: number
  time_adjustment_months: number
  fallback_reasons: string[]
  valuation_date: string
  top_comps?: any[]
  calculation_details?: any
}

export default function ValuationPage() {
  const [formData, setFormData] = useState({
    market: 'dfw',
    building_sf: 250000,
    noi_annual: 1950000
  })
  const [result, setResult] = useState<ValuationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [showCalculationModal, setShowCalculationModal] = useState(false)
  
  const { isDemoMode, getDemoData, blockNetworkWrite } = useDemo()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      // Check for demo mode first
      if (isDemoMode) {
        const demoData = await getDemoData(formData.market, formData.building_sf)
        if (demoData) {
          setResult(demoData)
          setLoading(false)
          return
        }
      }

      // Make API call (only if not in demo mode)
      const response = await fetch('/api/value', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Valuation failed:', error)
      alert('Valuation request failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  const getBadgeColor = (reason: string) => {
    const colors: Record<string, string> = {
      'low_sample': 'bg-yellow-100 text-yellow-800 border-yellow-300',
      'high_dispersion': 'bg-orange-100 text-orange-800 border-orange-300',
      'stale': 'bg-red-100 text-red-800 border-red-300'
    }
    return colors[reason] || 'bg-gray-100 text-gray-800 border-gray-300'
  }

  const fallbackLabels: Record<string, string> = {
    'low_sample': 'Low Sample Size',
    'high_dispersion': 'High Dispersion',
    'stale': 'Stale Data'
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Commercial Real Estate Valuation
          </h1>
          <p className="mt-2 text-gray-600">
            Get an accurate valuation for your commercial property using our advanced pricing models.
          </p>
        </div>

        {/* Form */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label htmlFor="market" className="block text-sm font-medium text-gray-700 mb-2">
                  Market
                </label>
                <select
                  id="market"
                  value={formData.market}
                  onChange={(e) => setFormData({ ...formData, market: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  <option value="dfw">Dallas-Fort Worth</option>
                  <option value="aus">Austin</option>
                  <option value="hou">Houston</option>
                  <option value="sat">San Antonio</option>
                  <option value="phx">Phoenix</option>
                </select>
              </div>

              <div>
                <label htmlFor="building_sf" className="block text-sm font-medium text-gray-700 mb-2">
                  Building Size (SF)
                </label>
                <input
                  type="number"
                  id="building_sf"
                  value={formData.building_sf}
                  onChange={(e) => setFormData({ ...formData, building_sf: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                  min="1000"
                  step="1000"
                />
              </div>

              <div>
                <label htmlFor="noi_annual" className="block text-sm font-medium text-gray-700 mb-2">
                  Annual NOI ($)
                </label>
                <input
                  type="number"
                  id="noi_annual"
                  value={formData.noi_annual}
                  onChange={(e) => setFormData({ ...formData, noi_annual: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                  min="10000"
                  step="10000"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading && (
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                )}
                {loading ? 'Calculating...' : 'Get Valuation'}
              </button>
            </div>
          </form>
        </div>

        {/* Results */}
        {result && (
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Valuation Results</h2>
              <button
                onClick={() => setShowCalculationModal(true)}
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                How this was calculated
              </button>
            </div>

            {/* Main Valuation */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">
                  {formatCurrency(result.valuation_total_usd)}
                </div>
                <div className="text-sm text-gray-500 mt-1">Estimated Value</div>
              </div>

              <div className="text-center">
                <div className="text-lg text-gray-900">
                  {formatCurrency(result.valuation_low_usd)} - {formatCurrency(result.valuation_high_usd)}
                </div>
                <div className="text-sm text-gray-500 mt-1">
                  {((result.confidence_level || 0.8) * 100)}% Confidence Interval
                </div>
              </div>

              <div className="text-center">
                <div className="text-lg font-semibold text-gray-900">
                  {formatPercent(result.implied_cap_rate)}
                </div>
                <div className="text-sm text-gray-500 mt-1">Implied Cap Rate</div>
              </div>
            </div>

            {/* Method & Quality Indicators */}
            <div className="border-t border-gray-200 pt-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <div>
                    <span className="text-sm text-gray-500">Method:</span>
                    <span className="ml-2 font-medium capitalize">
                      {result.method?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">Comparables:</span>
                    <span className="ml-2 font-medium">{result.comp_count}</span>
                  </div>
                </div>

                {result.fallback_reasons && result.fallback_reasons.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {result.fallback_reasons.map((reason, index) => (
                      <span
                        key={index}
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getBadgeColor(reason)}`}
                      >
                        {fallbackLabels[reason] || reason}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="text-xs text-gray-400">
                Valuation Date: {new Date(result.valuation_date).toLocaleDateString()}
                {result.method_version && ` • Model Version: ${result.method_version}`}
              </div>
            </div>
          </div>
        )}

        {/* Calculation Modal */}
        <CalculationModal
          isOpen={showCalculationModal}
          onClose={() => setShowCalculationModal(false)}
          data={result}
        />
      </div>
    </div>
  )
}
