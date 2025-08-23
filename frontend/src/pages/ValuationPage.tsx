import { useState, useEffect } from 'react'
import { supabase, MARKET_LABELS, type MarketSlug } from '../lib/supabase'

interface ValuationResult {
  cap_rate_mid: number
  cap_rate_band_bps: number
  value_low: number
  value_mid: number
  value_high: number
  n: number
  market_slug: string
}

export default function ValuationPage() {
  const [selectedMarket, setSelectedMarket] = useState<MarketSlug>('dfw')
  const [noi, setNoi] = useState('')
  const [result, setResult] = useState<ValuationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch latest market fundamentals on mount
  const [fundamentals, setFundamentals] = useState<any[]>([])
  const [comps, setComps] = useState<any[]>([])

  useEffect(() => {
    const fetchData = async () => {
      // Fetch fundamentals from secure view
      const { data: fundData, error: fErr } = await supabase
        .from('v_market_fundamentals_latest')
        .select('market_slug, as_of_date, vacancy_rate_pct, avg_asking_rent_psf_yr_nnn, yoy_rent_growth_pct')
        .order('market_slug')
      
      if (fErr) {
        console.error('Error fetching fundamentals:', fErr)
      } else {
        setFundamentals(fundData || [])
        console.log('✅ Fundamentals loaded from view:', fundData?.length, 'records')
      }

      // Fetch verified comps from secure view
      const { data: compData, error: cErr } = await supabase
        .from('v_verified_sales_18mo')
        .select('market_slug, sale_date, cap_rate_pct, price_total_usd, building_sf')
        .order('sale_date', { ascending: false })
        .limit(50)
      
      if (cErr) {
        console.error('Error fetching comps:', cErr)
      } else {
        setComps(compData || [])
        console.log('✅ Verified comps loaded from view:', compData?.length, 'records')
      }
    }

    fetchData()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!noi) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/value?market_slug=${selectedMarket}&noi_annual=${noi}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Valuation failed')
      }

      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => 
    new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: 'USD', 
      minimumFractionDigits: 0,
      maximumFractionDigits: 0 
    }).format(value)

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">CapSight Industrial Valuation</h1>
      
      {/* Verified Comps Summary */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Recent Verified Sales ({comps.length} comps)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(
            comps.reduce((acc: Record<string, any[]>, comp: any) => {
              if (!acc[comp.market_slug]) acc[comp.market_slug] = []
              acc[comp.market_slug].push(comp)
              return acc
            }, {} as Record<string, any[]>)
          ).map(([slug, marketComps]: [string, any[]]) => (
            <div key={slug} className="bg-white shadow rounded-lg p-4 border">
              <h3 className="font-semibold text-gray-900">{MARKET_LABELS[slug as MarketSlug]}</h3>
              <div className="mt-2 space-y-1 text-sm">
                <div>{marketComps.length} verified comps</div>
                <div>Avg Cap Rate: {(marketComps.filter((c: any) => c.cap_rate_pct).reduce((sum: number, c: any) => sum + c.cap_rate_pct, 0) / marketComps.filter((c: any) => c.cap_rate_pct).length).toFixed(2)}%</div>
                <div>Latest: {marketComps[0]?.sale_date}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Market Fundamentals */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Latest Market Fundamentals</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {fundamentals.map(fund => (
            <div key={fund.market_slug} className="bg-white shadow rounded-lg p-4 border">
              <h3 className="font-semibold text-gray-900">{MARKET_LABELS[fund.market_slug as MarketSlug]}</h3>
              <div className="mt-2 space-y-1 text-sm">
                <div>Vacancy: {fund.vacancy_rate_pct?.toFixed(1)}%</div>
                <div>Rent: ${fund.avg_asking_rent_psf_yr_nnn?.toFixed(2)}/SF/yr</div>
                <div>YoY Growth: {fund.yoy_rent_growth_pct?.toFixed(1)}%</div>
                <div className="text-xs text-gray-500">As of {fund.as_of_date}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Valuation Form */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Property Valuation</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Market
            </label>
            <select
              value={selectedMarket}
              onChange={(e) => setSelectedMarket(e.target.value as MarketSlug)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(MARKET_LABELS).map(([slug, label]) => (
                <option key={slug} value={slug}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Net Operating Income (Annual)
            </label>
            <input
              type="number"
              value={noi}
              onChange={(e) => setNoi(e.target.value)}
              placeholder="1200000"
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading || !noi}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Calculating...' : 'Estimate Value'}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {result && (
          <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-md">
            <h3 className="font-semibold text-gray-900 mb-3">Valuation Results</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="text-center">
                <div className="text-sm text-gray-600">Low</div>
                <div className="text-lg font-semibold text-green-600">
                  {formatCurrency(result.value_low)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600">Mid</div>
                <div className="text-xl font-bold text-blue-600">
                  {formatCurrency(result.value_mid)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600">High</div>
                <div className="text-lg font-semibold text-red-600">
                  {formatCurrency(result.value_high)}
                </div>
              </div>
            </div>

            <div className="border-t pt-3 space-y-2 text-sm text-gray-700">
              <div>Cap Rate (Mid): {result.cap_rate_mid.toFixed(2)}%</div>
              <div>Band: ±{result.cap_rate_band_bps} basis points</div>
              <div>Based on {result.n} verified comps</div>
              <div>Market: {MARKET_LABELS[result.market_slug as MarketSlug]}</div>
            </div>

            {/* Visual band */}
            <div className="mt-4">
              <div className="text-xs text-gray-500 mb-2">Value Range</div>
              <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-green-500 via-blue-500 to-red-500"
                  style={{ 
                    width: `${100 * (result.value_high - result.value_low) / result.value_mid}%`,
                    maxWidth: '100%'
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
