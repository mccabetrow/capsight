import React, { useState } from 'react'
import { supabase } from '../lib/supabase'
import useSWR from 'swr'

// Types
interface Market {
  slug: string
  name: string
}

interface Fundamentals {
  market_slug: string
  as_of_date: string
  vacancy_rate_pct: number | null
  avg_asking_rent_psf_yr_nnn: number | null
  yoy_rent_growth_pct: number | null
  under_construction_sf: number | null
  source_name: string
}

interface Comp {
  sale_date: string
  submarket: string
  building_sf: number
  price_per_sf_usd: number | null
  cap_rate_pct: number | null
}

interface ValuationResult {
  market_slug: string
  noi_annual: number
  cap_rate_mid: number
  value_low: number
  value_mid: number
  value_high: number
  n: number
  confidence: string
}

const MARKETS: Market[] = [
  { slug: 'dfw', name: 'Dallas-Fort Worth' },
  { slug: 'ie', name: 'Inland Empire' },
  { slug: 'atl', name: 'Atlanta' },
  { slug: 'phx', name: 'Phoenix' },
  { slug: 'sav', name: 'Savannah' },
]

export default function HomePage() {
  const [selectedMarket, setSelectedMarket] = useState('dfw')
  const [noiInput, setNoiInput] = useState('')
  const [valuation, setValuation] = useState<ValuationResult | null>(null)
  const [fundamentals, setFundamentals] = useState<Fundamentals | null>(null)
  const [comps, setComps] = useState<Comp[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch market data when market changes
  React.useEffect(() => {
    fetchMarketData(selectedMarket)
  }, [selectedMarket])

  const fetchMarketData = async (marketSlug: string) => {
    try {
      // Fetch fundamentals
      const { data: fundData } = await supabase
        .from('v_market_fundamentals_latest')
        .select('*')
        .eq('market_slug', marketSlug)
        .single()
      
      if (fundData) setFundamentals(fundData)

      // Fetch recent comps
      const { data: compsData } = await supabase
        .from('v_verified_sales_18mo')
        .select(`
          sale_date,
          submarket,
          building_sf,
          price_per_sf_usd,
          cap_rate_pct
        `)
        .eq('market_slug', marketSlug)
        .order('sale_date', { ascending: false })
        .limit(3)
      
      if (compsData) setComps(compsData)
    } catch (err) {
      console.error('Error fetching market data:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const noiValue = parseFloat(noiInput.replace(/,/g, ''))
    if (isNaN(noiValue) || noiValue <= 0) {
      setError('Please enter a valid NOI amount')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/value?market_slug=${selectedMarket}&noi_annual=${noiValue}`)
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Valuation failed')
      }
      
      const result = await response.json()
      setValuation(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get valuation')
    } finally {
      setIsLoading(false)
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const formatNumber = (value: number | null) => {
    if (value === null) return 'N/A'
    return value.toLocaleString()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-3xl font-bold text-gray-900">CapSight</h1>
              <span className="ml-3 text-sm text-gray-500">Industrial CRE Valuations</span>
            </div>
            <div className="text-sm text-gray-600">
              5 Pilot Markets • 18-Month Verified Comps
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="text-center mb-8">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Accurate Industrial Valuations in Seconds
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Get transparent value ranges backed by verified comparable sales data. 
            Fast. Transparent. Affordable.
          </p>
        </div>

        {/* Valuation Form */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-4 items-end">
            {/* Market Selection */}
            <div className="flex-1">
              <label htmlFor="market" className="block text-sm font-medium text-gray-700 mb-1">
                Market
              </label>
              <select
                id="market"
                value={selectedMarket}
                onChange={(e) => setSelectedMarket(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {MARKETS.map(market => (
                  <option key={market.slug} value={market.slug}>
                    {market.name}
                  </option>
                ))}
              </select>
            </div>

            {/* NOI Input */}
            <div className="flex-1">
              <label htmlFor="noi" className="block text-sm font-medium text-gray-700 mb-1">
                Annual NOI (USD)
              </label>
              <input
                type="text"
                id="noi"
                value={noiInput}
                onChange={(e) => setNoiInput(e.target.value)}
                placeholder="1,200,000"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Calculating...' : 'Get Valuation'}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Results Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Valuation Results */}
          {valuation && (
            <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Valuation Results</h3>
              
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">Low</div>
                  <div className="text-xl font-bold text-gray-900">
                    {formatCurrency(valuation.value_low)}
                  </div>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg border-2 border-blue-200">
                  <div className="text-sm text-blue-600 mb-1">Mid (Target)</div>
                  <div className="text-2xl font-bold text-blue-700">
                    {formatCurrency(valuation.value_mid)}
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">High</div>
                  <div className="text-xl font-bold text-gray-900">
                    {formatCurrency(valuation.value_high)}
                  </div>
                </div>
              </div>

              <div className="text-sm text-gray-600 text-center">
                Cap Rate: {valuation.cap_rate_mid}% • 
                Comps Used: {valuation.n} • 
                Confidence: {valuation.confidence.toUpperCase()}
              </div>
            </div>
          )}

          {/* Market Fundamentals */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Market Fundamentals
            </h3>
            <div className="text-sm text-gray-600 mb-4">
              {MARKETS.find(m => m.slug === selectedMarket)?.name}
            </div>
            
            {fundamentals ? (
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Vacancy Rate</span>
                  <span className="text-sm font-medium">
                    {fundamentals.vacancy_rate_pct?.toFixed(1) ?? 'N/A'}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Asking Rent</span>
                  <span className="text-sm font-medium">
                    ${fundamentals.avg_asking_rent_psf_yr_nnn?.toFixed(2) ?? 'N/A'}/SF/yr
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">YoY Growth</span>
                  <span className="text-sm font-medium">
                    {fundamentals.yoy_rent_growth_pct?.toFixed(1) ?? 'N/A'}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Under Construction</span>
                  <span className="text-sm font-medium">
                    {fundamentals.under_construction_sf ? 
                      `${(fundamentals.under_construction_sf / 1000000).toFixed(1)}M SF` : 
                      'N/A'
                    }
                  </span>
                </div>
                <div className="pt-2 border-t border-gray-100">
                  <div className="text-xs text-gray-500">
                    Source: {fundamentals.source_name}
                  </div>
                  <div className="text-xs text-gray-500">
                    As of {formatDate(fundamentals.as_of_date)}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-sm">Loading fundamentals...</div>
            )}
          </div>
        </div>

        {/* Recent Comps */}
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Verified Comps
          </h3>
          
          {comps.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Submarket
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Building SF
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Price/SF
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cap Rate
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {comps.map((comp, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {formatDate(comp.sale_date)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {comp.submarket}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {formatNumber(comp.building_sf)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        ${comp.price_per_sf_usd?.toFixed(0) ?? 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {comp.cap_rate_pct?.toFixed(1) ?? 'N/A'}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading comparable sales...</div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-16 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-gray-500">
            CapSight MVP • Powered by verified industrial CRE data • 
            <a href="mailto:hello@capsight.com" className="text-blue-600 hover:text-blue-700 ml-2">
              Contact Us
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
