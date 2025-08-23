'use client'

import { useState, useEffect } from 'react'

export interface DemoData {
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
  top_comps: Array<{
    masked_address: string
    sale_date: string
    distance_mi: number
    adj_cap_rate: number
    weight: number
    price_total_usd: number
    building_sf: number
  }>
  calculation_details: {
    time_adjustment_summary: string
    outlier_trim_details: string
    sample_quality: string
    dispersion_coefficient: number
    market_conditions: string
  }
}

export function useDemo() {
  const [isDemoMode, setIsDemoMode] = useState(false)

  useEffect(() => {
    // Check URL parameter
    const urlParams = new URLSearchParams(window.location.search)
    setIsDemoMode(urlParams.get('demo') === '1')
  }, [])

  const toggleDemo = () => {
    const url = new URL(window.location.href)
    if (isDemoMode) {
      url.searchParams.delete('demo')
    } else {
      url.searchParams.set('demo', '1')
    }
    window.history.replaceState({}, '', url.toString())
    setIsDemoMode(!isDemoMode)
  }

  const getDemoData = async (market: string, buildingSf: number): Promise<DemoData | null> => {
    if (!isDemoMode) return null

    // Select demo file based on market and size
    let fileName = 'dfw-250k-sf.json' // default

    // Size-based selection
    const sizeCategory = buildingSf < 120000 ? '100k' : 
                        buildingSf < 220000 ? '180k' : '250k'
    
    // Market-based selection with fallbacks
    if (market === 'dfw') {
      fileName = `dfw-250k-sf.json`
    } else if (market === 'aus') {
      fileName = `aus-180k-sf.json`
    } else if (market === 'sat') {
      fileName = `sat-100k-sf.json`
    }

    try {
      const response = await fetch(`/demo/${fileName}`)
      if (!response.ok) {
        console.warn(`Demo file not found: ${fileName}, using default`)
        const fallbackResponse = await fetch('/demo/dfw-250k-sf.json')
        return await fallbackResponse.json()
      }
      return await response.json()
    } catch (error) {
      console.error('Error loading demo data:', error)
      return null
    }
  }

  const blockNetworkWrite = (operation: string) => {
    if (isDemoMode) {
      console.log(`Demo mode: ${operation} blocked`)
      return true
    }
    return false
  }

  return {
    isDemoMode,
    toggleDemo,
    getDemoData,
    blockNetworkWrite
  }
}
