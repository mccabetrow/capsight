'use client'

import React, { useState } from 'react'
import useSWR from 'swr'
import { fetchFundamentals } from '@/lib/fetchFundamentals'
import { fetchComps } from '@/lib/fetchComps'
import { fetchValuation } from '@/lib/fetchValuation'
import { formatNoiInput, parseNoiInput, cn } from '@/lib/format'
import type { ValuationResponse, Market } from '@/lib/types'

// Market options with friendly labels
const MARKETS: Market[] = [
  { slug: 'dfw', name: 'Dallas–Fort Worth' },
  { slug: 'ie', name: 'Inland Empire' },
  { slug: 'atl', name: 'Atlanta' },
  { slug: 'phx', name: 'Phoenix' },
  { slug: 'sav', name: 'Savannah' },
]

// Analytics stub functions
const track = (event: string, properties: Record<string, any>) => {
  console.log('Analytics event:', event, properties)
}

export default function HomePage() {
  const [selectedMarket, setSelectedMarket] = useState('dfw')
  const [noiInput, setNoiInput] = useState('')
  const [valuation, setValuation] = useState<ValuationResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch market data using SWR
  const { data: fundamentals } = useSWR(
    ['fundamentals', selectedMarket],
    () => fetchFundamentals(selectedMarket)
  )

  const { data: comps } = useSWR(
    ['comps', selectedMarket],
    () => fetchComps(selectedMarket)
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const noiValue = parseNoiInput(noiInput)
    
    if (noiValue < 1) {
      setError('Please enter a valid NOI amount')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const result = await fetchValuation({
        market_slug: selectedMarket,
        noi_annual: noiValue
      })
      setValuation(result)
      track('valuation_success', { market: selectedMarket, noi: noiValue })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Valuation failed'
      setError(message)
      track('valuation_error', { market: selectedMarket })
    } finally {
      setIsLoading(false)
    }
  }

  const handleNoiChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNoiInput(e.target.value)
  }

  const handleNoiBlur = () => {
    setNoiInput(formatNoiInput(noiInput))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit(e as any)
    }
  }

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8">
      {/* Hero Section */}
      <section className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Industrial valuations in seconds.
        </h1>
        <p className="text-xl text-gray-600 mb-2">
          Enter NOI and get a transparent value range backed by verified comps.
        </p>
        <p className="text-sm text-gray-500 flex items-center justify-center space-x-1">
          <span>Confidence bands show ±50 basis points</span>
          <span 
            className="text-gray-400 hover:text-gray-600 cursor-help"
            title="Our valuation bands reflect a ±50 basis point range around the median cap rate from verified comparable sales"
            aria-label="Valuation methodology explanation"
          >
            ℹ️
          </span>
        </p>
      </section>

      {/* Valuation Form */}
      <section className="card mb-8">
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          {/* Market Select */}
          <div className="space-y-2">
            <label htmlFor="market" className="block text-sm font-medium text-gray-700">
              Market
            </label>
            <select
              id="market"
              value={selectedMarket}
              onChange={(e) => setSelectedMarket(e.target.value)}
              className="focus-ring w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              aria-label="Select market"
            >
              {MARKETS.map(market => (
                <option key={market.slug} value={market.slug}>
                  {market.name}
                </option>
              ))}
            </select>
          </div>

          {/* NOI Input */}
          <div className="space-y-2">
            <label htmlFor="noi" className="block text-sm font-medium text-gray-700">
              Annual NOI (USD)
            </label>
            <input
              type="text"
              id="noi"
              value={noiInput}
              onChange={handleNoiChange}
              onBlur={handleNoiBlur}
              onKeyDown={handleKeyDown}
              placeholder="1,200,000"
              className="focus-ring w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              aria-label="Annual net operating income in USD"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className={cn(
              "btn btn-primary",
              isLoading && "opacity-50 cursor-not-allowed"
            )}
            aria-label="Get valuation estimate"
          >
            {isLoading ? 'Estimating...' : 'Estimate Value'}
          </button>
        </form>

        {/* Error State */}
        {error && (
          <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-4">
            <div className="flex items-center space-x-2">
              <span className="text-red-600">⚠️</span>
              <span className="text-red-700 text-sm font-medium">{error}</span>
              <button
                onClick={() => setError(null)}
                className="text-red-600 hover:text-red-800 text-sm underline"
              >
                Retry
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Valuation Results */}
      {valuation && (
        <section className="card mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Valuation Results</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="text-center">
              <div className="text-sm text-gray-500 mb-1">Low</div>
              <div className="text-2xl font-bold text-gray-700">
                ${valuation.value_low.toLocaleString()}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500 mb-1">Mid (Target)</div>
              <div className="text-3xl font-bold text-primary-600">
                ${valuation.value_mid.toLocaleString()}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500 mb-1">High</div>
              <div className="text-2xl font-bold text-gray-700">
                ${valuation.value_high.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Band Bar Visualization */}
          <div className="relative h-3 bg-gray-200 rounded-full mb-4">
            <div className="absolute inset-y-0 left-1/4 right-1/4 bg-primary-200 rounded-full"></div>
            <div 
              className="absolute top-0 bottom-0 w-1 bg-primary-600 rounded-full"
              style={{ left: '50%', marginLeft: '-2px' }}
            ></div>
          </div>

          <div className="text-center text-sm text-gray-600">
            Cap Rate: {valuation.cap_rate_mid.toFixed(1)}% | 
            Comps used: {valuation.n} | 
            Band width: 50 bps
          </div>
        </section>
      )}

      {/* Two Column Layout for Fundamentals and Comps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market Fundamentals */}
        <section className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Market Fundamentals - {MARKETS.find(m => m.slug === selectedMarket)?.name}
          </h2>
          
          {fundamentals ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-500">Vacancy Rate</div>
                <div className="text-lg font-semibold">
                  {fundamentals.vacancy_rate_pct?.toFixed(1) ?? 'N/A'}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500">Asking Rent</div>
                <div className="text-lg font-semibold">
                  ${fundamentals.avg_asking_rent_psf_yr_nnn?.toFixed(2) ?? 'N/A'}/SF/yr
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500">YoY Rent Growth</div>
                <div className="text-lg font-semibold">
                  {fundamentals.yoy_rent_growth_pct?.toFixed(1) ?? 'N/A'}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500">Under Construction</div>
                <div className="text-lg font-semibold">
                  {fundamentals.under_construction_sf ? 
                    `${(fundamentals.under_construction_sf / 1000000).toFixed(1)}M SF` : 
                    'N/A'
                  }
                </div>
              </div>
            </div>
          ) : (
            <div className="text-gray-500">Loading market fundamentals...</div>
          )}
        </section>

        {/* Recent Comps */}
        <section className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Verified Comps (Last 18 Months)
          </h2>
          
          {comps && comps.length > 0 ? (
            <div className="space-y-3">
              {comps.slice(0, 5).map((comp, idx) => (
                <div key={idx} className="border-b border-gray-100 pb-2 last:border-b-0">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium text-sm">{comp.submarket}</div>
                      <div className="text-xs text-gray-500">
                        {new Date(comp.sale_date).toLocaleDateString()} • 
                        {comp.building_sf.toLocaleString()} SF
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">
                        ${comp.price_per_sf_usd?.toFixed(0) ?? 'N/A'}/SF
                      </div>
                      <div className="text-xs text-gray-500">
                        {comp.cap_rate_pct?.toFixed(1) ?? 'N/A'}% cap
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500">
              {comps === undefined ? 'Loading comps...' : 'No verified comps available'}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
