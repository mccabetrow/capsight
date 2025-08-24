/**
 * ===== LIVE DATA SOURCES =====
 * Real-time macro data from FRED API with circuit breaker, cache, and retry logic
 */

import { createClient } from '@supabase/supabase-js'
import { getEnvConfig } from './env-config'

interface MacroData {
  fed_funds_rate: number
  ten_year_treasury: number
  unemployment_rate: number
  fetched_at: string
}

interface MarketFundamentals {
  market_slug: string
  avg_asking_rent_psf_yr_nnn: number
  vacancy_rate_pct: number
  avg_cap_rate_pct: number
  absorption_sf_12m: number
  deliveries_sf_12m: number
  rent_growth_yoy_pct: number
  last_updated: string
}

interface CompSale {
  id: string
  address: string
  sale_date: string
  sale_price_usd: number
  building_sf: number
  price_per_sf_usd: number
  cap_rate_pct: number
  asset_type: string
  market_slug: string
}

interface DataProvenance {
  source: string
  as_of: string
  from_cache: boolean
}

interface DataResult<T> {
  data: T | null
  provenance: DataProvenance
  freshness: {
    is_fresh: boolean
    days_old: number
  }
}

class CircuitBreakerError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'CircuitBreakerError'
  }
}

class DataCircuitBreaker {
  private failures = 0
  private lastFailureTime: number | null = null
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED'
  
  constructor(
    private threshold: number,
    private timeout: number
  ) {}
  
  canExecute(): boolean {
    if (this.state === 'CLOSED') return true
    
    if (this.state === 'OPEN') {
      if (this.lastFailureTime && Date.now() - this.lastFailureTime > this.timeout) {
        this.state = 'HALF_OPEN'
        return true
      }
      return false
    }
    
    return true // HALF_OPEN
  }
  
  onSuccess(): void {
    this.failures = 0
    this.state = 'CLOSED'
    this.lastFailureTime = null
  }
  
  onFailure(): void {
    this.failures++
    this.lastFailureTime = Date.now()
    
    if (this.failures >= this.threshold) {
      this.state = 'OPEN'
    }
  }
  
  getState() {
    return {
      state: this.state,
      failures: this.failures,
      lastFailureTime: this.lastFailureTime
    }
  }
}

class LiveDataFetcher {
  private macroCache: { data: MacroData; expiry: number } | null = null
  private circuitBreaker: DataCircuitBreaker
  private supabase: any
  private config = getEnvConfig()
  
  constructor() {
    this.circuitBreaker = new DataCircuitBreaker(
      this.config.circuit_breaker_failure_threshold,
      this.config.circuit_breaker_timeout_minutes * 60 * 1000
    )
    
    this.supabase = createClient(
      this.config.supabase_url,
      this.config.supabase_service_role_key || this.config.supabase_anon_key
    )
  }
  
  /**
   * Fetch macro data from FRED API with circuit breaker and cache
   */
  async getMacroData(): Promise<DataResult<MacroData>> {
    const now = Date.now()
    const cacheValidUntil = this.config.cache_ttl_macro_minutes * 60 * 1000
    
    // Check cache first
    if (this.macroCache && now < this.macroCache.expiry) {
      const daysSinceData = Math.floor((now - new Date(this.macroCache.data.fetched_at).getTime()) / (24 * 60 * 60 * 1000))
      
      return {
        data: this.macroCache.data,
        provenance: {
          source: 'FRED',
          as_of: this.macroCache.data.fetched_at.split('T')[0],
          from_cache: true
        },
        freshness: {
          is_fresh: daysSinceData <= this.config.freshness_macro_days,
          days_old: daysSinceData
        }
      }
    }
    
    // Check circuit breaker
    if (!this.circuitBreaker.canExecute()) {
      console.warn('⚡ Macro data circuit breaker is OPEN - using fallback')
      throw new CircuitBreakerError('Macro data circuit breaker is open')
    }
    
    try {
      console.log('🌐 Fetching live macro data from FRED...')
      
      // Fetch from FRED API with retry logic
      const macroData = await this.fetchFromFredWithRetry()
      
      // Cache the result
      this.macroCache = {
        data: macroData,
        expiry: now + cacheValidUntil
      }
      
      this.circuitBreaker.onSuccess()
      
      const daysSinceData = 0 // Fresh data
      
      return {
        data: macroData,
        provenance: {
          source: 'FRED',
          as_of: macroData.fetched_at.split('T')[0],
          from_cache: false
        },
        freshness: {
          is_fresh: true,
          days_old: daysSinceData
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to fetch macro data:', error)
      this.circuitBreaker.onFailure()
      
      // Return cached data if available, even if expired
      if (this.macroCache) {
        const daysSinceData = Math.floor((now - new Date(this.macroCache.data.fetched_at).getTime()) / (24 * 60 * 60 * 1000))
        
        return {
          data: this.macroCache.data,
          provenance: {
            source: 'FRED',
            as_of: this.macroCache.data.fetched_at.split('T')[0],
            from_cache: true
          },
          freshness: {
            is_fresh: false,
            days_old: daysSinceData
          }
        }
      }
      
      throw error
    }
  }
  
  /**
   * Fetch market fundamentals from Supabase
   */
  async getMarketFundamentals(marketSlug: string): Promise<DataResult<MarketFundamentals>> {
    try {
      console.log(`📊 Fetching market fundamentals for ${marketSlug}...`)
      
      const { data, error } = await this.supabase
        .from('market_fundamentals')
        .select('*')
        .eq('market_slug', marketSlug.toLowerCase())
        .order('last_updated', { ascending: false })
        .limit(1)
        .single()
      
      if (error || !data) {
        console.error(`❌ No market fundamentals found for ${marketSlug}:`, error)
        return {
          data: null,
          provenance: {
            source: 'Supabase:market_fundamentals',
            as_of: new Date().toISOString().split('T')[0],
            from_cache: false
          },
          freshness: {
            is_fresh: false,
            days_old: 999
          }
        }
      }
      
      const lastUpdated = new Date(data.last_updated)
      const daysSinceUpdate = Math.floor((Date.now() - lastUpdated.getTime()) / (24 * 60 * 60 * 1000))
      
      return {
        data: data as MarketFundamentals,
        provenance: {
          source: 'Supabase:market_fundamentals',
          as_of: lastUpdated.toISOString().split('T')[0],
          from_cache: false
        },
        freshness: {
          is_fresh: daysSinceUpdate <= this.config.freshness_fundamentals_days,
          days_old: daysSinceUpdate
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to fetch market fundamentals:', error)
      throw error
    }
  }
  
  /**
   * Fetch comparable sales from Supabase
   */
  async getComparableSales(marketSlug: string, limit = 15): Promise<DataResult<CompSale[]>> {
    try {
      console.log(`🏢 Fetching comparable sales for ${marketSlug}...`)
      
      const sixMonthsAgo = new Date()
      sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6)
      
      const { data, error } = await this.supabase
        .from('comps')
        .select('*')
        .eq('market_slug', marketSlug.toLowerCase())
        .gte('sale_date', sixMonthsAgo.toISOString().split('T')[0])
        .not('cap_rate_pct', 'is', null)
        .not('price_per_sf_usd', 'is', null)
        .order('sale_date', { ascending: false })
        .limit(limit)
      
      if (error) {
        console.error(`❌ Error fetching comps for ${marketSlug}:`, error)
        throw error
      }
      
      const comps = data || []
      
      // Find most recent comp date
      const mostRecentDate = comps.length > 0
        ? new Date(Math.max(...comps.map((c: any) => new Date(c.sale_date).getTime())))
        : new Date()

      const daysSinceRecent = Math.floor((Date.now() - mostRecentDate.getTime()) / (24 * 60 * 60 * 1000))
      
      return {
        data: comps as CompSale[],
        provenance: {
          source: 'Supabase:comps',
          as_of: mostRecentDate.toISOString().split('T')[0],
          from_cache: false
        },
        freshness: {
          is_fresh: daysSinceRecent <= this.config.freshness_comps_days,
          days_old: daysSinceRecent
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to fetch comparable sales:', error)
      throw error
    }
  }
  
  /**
   * Get circuit breaker status
   */
  getCircuitBreakerStatus() {
    return this.circuitBreaker.getState()
  }
  
  /**
   * Private method to fetch from FRED with exponential backoff
   */
  private async fetchFromFredWithRetry(): Promise<MacroData> {
    const maxRetries = 3
    const baseDelay = 500
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        // Fetch Fed Funds Rate (DFF)
        const dffUrl = `https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=${this.config.fred_api_key}&file_type=json&limit=1&sort_order=desc`
        const dffResponse = await fetch(dffUrl, { 
          signal: AbortSignal.timeout(10000) 
        })
        
        if (!dffResponse.ok) {
          throw new Error(`FRED DFF API error: ${dffResponse.status}`)
        }
        
        const dffData = await dffResponse.json()
        const fedFundsRate = parseFloat(dffData.observations[0].value)
        
        // Fetch 10-Year Treasury (GS10)
        const gs10Url = `https://api.stlouisfed.org/fred/series/observations?series_id=GS10&api_key=${this.config.fred_api_key}&file_type=json&limit=1&sort_order=desc`
        const gs10Response = await fetch(gs10Url, { 
          signal: AbortSignal.timeout(10000) 
        })
        
        if (!gs10Response.ok) {
          throw new Error(`FRED GS10 API error: ${gs10Response.status}`)
        }
        
        const gs10Data = await gs10Response.json()
        const tenYearTreasury = parseFloat(gs10Data.observations[0].value)
        
        // Fetch Unemployment Rate (UNRATE)
        const unrateUrl = `https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key=${this.config.fred_api_key}&file_type=json&limit=1&sort_order=desc`
        const unrateResponse = await fetch(unrateUrl, { 
          signal: AbortSignal.timeout(10000) 
        })
        
        const unrateData = await unrateResponse.json()
        const unemploymentRate = parseFloat(unrateData.observations[0].value)
        
        return {
          fed_funds_rate: fedFundsRate,
          ten_year_treasury: tenYearTreasury,
          unemployment_rate: unemploymentRate,
          fetched_at: new Date().toISOString()
        }
        
      } catch (error) {
        console.warn(`⚠️ FRED fetch attempt ${attempt + 1} failed:`, error)
        
        if (attempt === maxRetries - 1) {
          throw error
        }
        
        // Exponential backoff
        const delay = baseDelay * Math.pow(2, attempt)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
    
    throw new Error('All FRED fetch attempts failed')
  }
}

// Singleton instance
let dataFetcher: LiveDataFetcher | null = null

export function getLiveDataFetcher(): LiveDataFetcher {
  if (!dataFetcher) {
    dataFetcher = new LiveDataFetcher()
  }
  return dataFetcher
}

export type { MacroData, MarketFundamentals, CompSale, DataProvenance, DataResult }
