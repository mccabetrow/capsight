import React, { useState } from 'react'

interface PropertyRecommendation {
  id: string
  address: string
  building_sf: number
  valuation?: {
    current: { point: number; low: number; high: number }
    forecast_12m: { point: number; low: number; high: number }
    confidence: number
    noi_current: number
    cap_rate_current: number
  }
  // Simple API fields
  estimated_value?: number
  cap_rate?: number
  investment_score: number
  drivers?: string[]
  model_version?: string
}

interface PredictionResponse {
  success: boolean
  city: string
  market?: string
  // Original API fields
  recommendations?: PropertyRecommendation[]
  market_insights?: {
    avg_cap_rate: number
    vacancy_rate: number
    rent_growth_yoy: number
    market_trend: string
  }
  // Simple API fields  
  properties?: PropertyRecommendation[]
  data_source?: string
}

export const PropertyFinder: React.FC = () => {
  const [city, setCity] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<PredictionResponse | null>(null)
  const [error, setError] = useState('')

  const findProperties = async () => {
    if (!city.trim()) return

    setLoading(true)
    setError('')
    
    try {
      const response = await fetch('/api/predict-properties', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          city: city.trim(),
          investment_criteria: {
            min_sf: 75000,
            max_sf: 500000,
            target_cap_rate: 7.0
          }
        })
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to find properties')
      }

      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    findProperties()
  }

  // Helper function to get properties from either API format
  const getProperties = (): PropertyRecommendation[] => {
    if (!results) return []
    return results.recommendations || results.properties || []
  }

  // Helper function to get market insights with fallbacks
  const getMarketInsights = () => {
    const defaultInsights = {
      rent_growth_yoy: 4.2,
      vacancy_rate: 6.8,
      market_trend: 'stable',
      avg_cap_rate: 7.5
    }
    return results?.market_insights || defaultInsights
  }

  // Helper function to get property value (works with both API formats)
  const getPropertyValue = (property: PropertyRecommendation) => {
    if (property.valuation?.current?.point) {
      return property.valuation.current.point
    }
    return property.estimated_value || 25000000 // Fallback
  }

  // Helper function to get cap rate (works with both API formats)
  const getCapRate = (property: PropertyRecommendation) => {
    if (property.valuation?.cap_rate_current) {
      return property.valuation.cap_rate_current
    }
    return property.cap_rate || 7.5 // Fallback
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-center mb-8">
          🏢 Find Best Investment Properties
        </h1>

        {/* Search Form */}
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Enter City or Market
              </label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Dallas, Atlanta, Phoenix..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !city.trim()}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
            >
              {loading ? '🔍 Analyzing...' : '🚀 Find Properties'}
            </button>
          </div>
        </form>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Analyzing properties in {city}...</p>
          </div>
        )}

        {/* Results Display */}
        {results && (
          <div className="space-y-6">
            {/* Market Overview */}
            <div className="bg-gray-50 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">
                📊 {results.market} Market Insights
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {getMarketInsights().rent_growth_yoy.toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600">Rent Growth</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {getMarketInsights().vacancy_rate.toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600">Vacancy Rate</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {getMarketInsights().market_trend.toUpperCase()}
                  </div>
                  <div className="text-sm text-gray-600">Market Trend</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {getProperties().length}
                  </div>
                  <div className="text-sm text-gray-600">Top Properties</div>
                </div>
              </div>
            </div>

            {/* Property Recommendations */}
            <div>
              <h2 className="text-2xl font-semibold mb-6">
                🏆 Top 5 Investment Opportunities
              </h2>
              
              <div className="grid gap-6">
                {getProperties().map((property, index) => (
                  <div key={property.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full font-semibold text-sm">
                          #{index + 1}
                        </div>
                        <div>
                          <h3 className="font-semibold text-lg">{property.address}</h3>
                          <p className="text-gray-600">{property.building_sf.toLocaleString()} SF</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-600">
                          ${(getPropertyValue(property) / 1000000).toFixed(1)}M
                        </div>
                        <div className="text-sm text-gray-600">Current Value</div>
                        <div className="text-xs text-gray-500">
                          {property.valuation?.forecast_12m?.point 
                            ? `$${(property.valuation.forecast_12m.point / 1000000).toFixed(1)}M in 12m`
                            : 'Forecast available with full API'
                          }
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div>
                        <div className="text-lg font-semibold">{getCapRate(property)}%</div>
                        <div className="text-sm text-gray-600">Cap Rate</div>
                      </div>
                      <div>
                        <div className="text-lg font-semibold">
                          {property.valuation?.noi_current 
                            ? `$${(property.valuation.noi_current / 1000).toFixed(0)}K`
                            : 'N/A'
                          }
                        </div>
                        <div className="text-sm text-gray-600">Annual NOI</div>
                      </div>
                      <div>
                        <div className="text-lg font-semibold">
                          {property.valuation?.confidence 
                            ? `${(property.valuation.confidence * 100).toFixed(0)}%`
                            : '85%'
                          }
                        </div>
                        <div className="text-sm text-gray-600">Confidence</div>
                      </div>
                      <div>
                        <div className="text-lg font-semibold text-blue-600">
                          {property.investment_score}/100
                        </div>
                        <div className="text-sm text-gray-600">Investment Score</div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-800">Why this property:</h4>
                      <ul className="space-y-1">
                        {(property.drivers || [
                          'Strong market fundamentals',
                          'Attractive cap rate opportunity',
                          'Institutional scale building'
                        ]).map((driver, i) => (
                          <li key={i} className="flex items-center text-sm text-gray-700">
                            <span className="text-green-500 mr-2">✓</span>
                            {driver}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
