/**
 * ===== REAL-TIME DATA FETCHER SERVICE =====
 * Fetches live data from FRED API, Supabase, and other sources
 * with caching, circuit breakers, and comprehensive provenance tracking
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'

// ===== TYPES =====
export interface MacroData {
  fed_funds_rate: number
  treasury_10yr: number
  credit_spread?: number
  as_of: string
  source: string
}

export interface MarketFundamentals {
  market_slug: string
  city: string
  vacancy_rate_pct: number
  avg_asking_rent_psf_yr_nnn: number
  yoy_rent_growth_pct: number
  under_construction_sf: number
  absorption_sf_ytd: number
  inventory_sf: number
  avg_cap_rate_pct: number
  as_of_date: string
  updated_at: string
}

export interface Comparable {
  id: string
  market_slug: string
  address: string
  building_sf: number
  price_per_sf_usd: number
  cap_rate_pct: number
  noi_annual: number
  sale_date: string
  submarket: string
  building_class: string
  year_built: number
  occupancy_pct: number
}

export interface DataProvenance {
  macro?: {
    source: string
    as_of: string
    from_cache: boolean
    breaker_status?: 'open' | 'half-open' | 'closed'
  }
  fundamentals?: {
    source: string
    as_of: string
    from_cache: boolean
    record_count: number
  }
  comps?: {
    source: string
    as_of: string
    from_cache: boolean
    record_count: number
  }
}

export interface DataFreshness {
  is_fresh: boolean
  days_old: number
  threshold_days: number
  status: 'FRESH' | 'STALE' | 'EXPIRED'
}

export interface CircuitBreakerState {
  state: 'closed' | 'open' | 'half-open'
  failure_count: number
  last_failure_time?: number
  next_attempt_time?: number
}

// ===== CACHE INTERFACE =====
interface CacheEntry<T> {
  data: T
  timestamp: number
  expires_at: number
}

class MemoryCache {
  private cache = new Map<string, CacheEntry<any>>()

  set<T>(key: string, data: T, ttl_ms: number): void {
    const now = Date.now()
    this.cache.set(key, {
      data,
      timestamp: now,
      expires_at: now + ttl_ms
    })
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key)
    if (!entry || entry.expires_at < Date.now()) {
      this.cache.delete(key)
      return null
    }
    return entry.data
  }

  delete(key: string): void {
    this.cache.delete(key)
  }

  clear(): void {
    this.cache.clear()
  }
}

// ===== CIRCUIT BREAKER =====
class CircuitBreaker {
  private state: CircuitBreakerState = { state: 'closed', failure_count: 0 }
  
  constructor(
    private failure_threshold = 3,
    private timeout_ms = 120000 // 2 minutes
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state.state === 'open') {
      if (Date.now() >= (this.state.next_attempt_time || 0)) {
        this.state.state = 'half-open'
      } else {
        throw new Error(`Circuit breaker OPEN. Next attempt in ${Math.ceil(((this.state.next_attempt_time || 0) - Date.now()) / 1000)}s`)
      }
    }

    try {
      const result = await operation()
      
      // Success - reset or close circuit
      if (this.state.state === 'half-open' || this.state.failure_count > 0) {
        this.state = { state: 'closed', failure_count: 0 }
      }
      
      return result
    } catch (error) {
      this.state.failure_count++
      this.state.last_failure_time = Date.now()

      if (this.state.failure_count >= this.failure_threshold) {
        this.state.state = 'open'
        this.state.next_attempt_time = Date.now() + this.timeout_ms
      }

      throw error
    }
  }

  getState(): CircuitBreakerState {
    return { ...this.state }
  }
}

// ===== MAIN DATA FETCHER CLASS =====
export class DataFetcher {
  private supabase: SupabaseClient
  private cache = new MemoryCache()
  private fredCircuitBreaker = new CircuitBreaker(3, 120000)
  private supabaseCircuitBreaker = new CircuitBreaker(5, 60000)
  
  private readonly FRED_BASE_URL = 'https://api.stlouisfed.org/fred'
  private readonly MACRO_CACHE_TTL = parseInt(process.env.CACHE_TTL_MACRO_MINUTES || '30') * 60 * 1000
  private readonly FUNDAMENTALS_CACHE_TTL = parseInt(process.env.CACHE_TTL_FUNDAMENTALS_HOURS || '24') * 60 * 60 * 1000
  private readonly COMPS_CACHE_TTL = parseInt(process.env.CACHE_TTL_COMPS_HOURS || '24') * 60 * 60 * 1000

  constructor() {
    this.supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    )
  }

  // ===== MACRO DATA FROM FRED =====
  async getMacroData(): Promise<{ data: MacroData, provenance: DataProvenance['macro'] }> {
    const cache_key = 'macro_data'
    
    // Check cache first
    const cached = this.cache.get<{ data: MacroData, provenance: DataProvenance['macro'] }>(cache_key)
    if (cached && cached.provenance) {
      return {
        data: cached.data,
        provenance: { 
          source: cached.provenance.source,
          as_of: cached.provenance.as_of,
          from_cache: true,
          breaker_status: cached.provenance.breaker_status
        }
      }
    }

    try {
      const data = await this.fredCircuitBreaker.execute(async () => {
        const fed_funds = await this.fetchFredSeries('DFF') // Effective Federal Funds Rate
        const treasury_10yr = await this.fetchFredSeries('GS10') // 10-Year Treasury Rate
        
        return {
          fed_funds_rate: fed_funds.value,
          treasury_10yr: treasury_10yr.value,
          as_of: fed_funds.date, // Use most recent date
          source: 'FRED'
        }
      })

      const provenance = {
        source: 'FRED',
        as_of: data.as_of,
        from_cache: false,
        breaker_status: this.fredCircuitBreaker.getState().state as 'open' | 'half-open' | 'closed'
      }

      // Cache successful result
      this.cache.set(cache_key, { data, provenance }, this.MACRO_CACHE_TTL)
      
      return { data, provenance }
      
    } catch (error) {
      console.error('FRED API error:', error)
      
      // Try to return cached data even if expired
      const stale_cached = this.cache.get<{ data: MacroData, provenance: DataProvenance['macro'] }>(cache_key)
      if (stale_cached && stale_cached.provenance) {
        return {
          data: stale_cached.data,
          provenance: {
            source: stale_cached.provenance.source,
            as_of: stale_cached.provenance.as_of,
            from_cache: true,
            breaker_status: this.fredCircuitBreaker.getState().state as 'open' | 'half-open' | 'closed'
          }
        }
      }
      
      throw new Error(`FRED API unavailable and no cached data: ${error}`)
    }
  }

  private async fetchFredSeries(series_id: string): Promise<{ value: number, date: string }> {
    const api_key = process.env.FRED_API_KEY
    if (!api_key) {
      throw new Error('FRED_API_KEY not configured')
    }

    const url = `${this.FRED_BASE_URL}/series/observations?series_id=${series_id}&api_key=${api_key}&file_type=json&limit=1&sort_order=desc`
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'CapSight/1.0',
      },
      signal: AbortSignal.timeout(10000) // 10 second timeout
    })

    if (!response.ok) {
      throw new Error(`FRED API error: ${response.status} ${response.statusText}`)
    }

    const result = await response.json()
    
    if (!result.observations || result.observations.length === 0) {
      throw new Error(`No observations found for series ${series_id}`)
    }

    const observation = result.observations[0]
    return {
      value: parseFloat(observation.value),
      date: observation.date
    }
  }

  // ===== MARKET FUNDAMENTALS FROM SUPABASE =====
  async getMarketFundamentals(market_slug: string): Promise<{
    data: MarketFundamentals | null,
    provenance: DataProvenance['fundamentals'],
    freshness: DataFreshness
  }> {
    const cache_key = `fundamentals_${market_slug}`
    
    // Check cache first
    const cached = this.cache.get<{ data: MarketFundamentals, provenance: DataProvenance['fundamentals'], freshness: DataFreshness }>(cache_key)
    if (cached && cached.provenance) {
      return {
        data: cached.data,
        provenance: { 
          source: cached.provenance.source,
          as_of: cached.provenance.as_of,
          from_cache: true,
          record_count: cached.provenance.record_count
        },
        freshness: cached.freshness
      }
    }

    try {
      const result = await this.supabaseCircuitBreaker.execute(async () => {
        const { data, error } = await this.supabase
          .from('market_fundamentals')
          .select('*')
          .eq('market_slug', market_slug)
          .order('as_of_date', { ascending: false })
          .limit(1)
          .single()

        if (error) {
          throw new Error(`Supabase error: ${error.message}`)
        }

        return data as MarketFundamentals
      })

      if (!result) {
        return {
          data: null,
          provenance: {
            source: 'Supabase:market_fundamentals',
            as_of: new Date().toISOString(),
            from_cache: false,
            record_count: 0
          },
          freshness: {
            is_fresh: false,
            days_old: 999,
            threshold_days: parseInt(process.env.FRESHNESS_FUNDAMENTALS_DAYS || '90'),
            status: 'EXPIRED'
          }
        }
      }

      const freshness = this.calculateFreshness(result.as_of_date, parseInt(process.env.FRESHNESS_FUNDAMENTALS_DAYS || '90'))
      
      const provenance = {
        source: 'Supabase:market_fundamentals',
        as_of: result.as_of_date,
        from_cache: false,
        record_count: 1
      }

      // Cache result
      this.cache.set(cache_key, { data: result, provenance, freshness }, this.FUNDAMENTALS_CACHE_TTL)

      return { data: result, provenance, freshness }

    } catch (error) {
      console.error('Market fundamentals fetch error:', error)
      throw error
    }
  }

  // ===== COMPARABLE SALES FROM SUPABASE =====
  async getComps(market_slug: string, limit = 10): Promise<{
    data: Comparable[],
    provenance: DataProvenance['comps'],
    freshness: DataFreshness
  }> {
    const cache_key = `comps_${market_slug}_${limit}`
    
    // Check cache first
    const cached = this.cache.get<{ data: Comparable[], provenance: DataProvenance['comps'], freshness: DataFreshness }>(cache_key)
    if (cached && cached.provenance) {
      return {
        data: cached.data,
        provenance: { 
          source: cached.provenance.source,
          as_of: cached.provenance.as_of,
          from_cache: true,
          record_count: cached.provenance.record_count
        },
        freshness: cached.freshness
      }
    }

    try {
      const result = await this.supabaseCircuitBreaker.execute(async () => {
        const { data, error } = await this.supabase
          .from('v_comps_trimmed')
          .select('*')
          .eq('market_slug', market_slug)
          .order('sale_date', { ascending: false })
          .limit(limit)

        if (error) {
          throw new Error(`Supabase comps error: ${error.message}`)
        }

        return (data || []) as Comparable[]
      })

      const most_recent_date = result.length > 0 ? result[0].sale_date : null
      const freshness = most_recent_date 
        ? this.calculateFreshness(most_recent_date, parseInt(process.env.FRESHNESS_COMPS_DAYS || '180'))
        : { is_fresh: false, days_old: 999, threshold_days: 180, status: 'EXPIRED' as const }

      const provenance = {
        source: 'Supabase:v_comps_trimmed',
        as_of: most_recent_date || new Date().toISOString(),
        from_cache: false,
        record_count: result.length
      }

      // Cache result
      this.cache.set(cache_key, { data: result, provenance, freshness }, this.COMPS_CACHE_TTL)

      return { data: result, provenance, freshness }

    } catch (error) {
      console.error('Comparables fetch error:', error)
      return {
        data: [],
        provenance: {
          source: 'Supabase:v_comps_trimmed',
          as_of: new Date().toISOString(),
          from_cache: false,
          record_count: 0
        },
        freshness: {
          is_fresh: false,
          days_old: 999,
          threshold_days: parseInt(process.env.FRESHNESS_COMPS_DAYS || '180'),
          status: 'EXPIRED'
        }
      }
    }
  }

  // ===== UTILITY METHODS =====
  private calculateFreshness(as_of_date: string, threshold_days: number): DataFreshness {
    const now = new Date()
    const data_date = new Date(as_of_date)
    const days_old = Math.floor((now.getTime() - data_date.getTime()) / (1000 * 60 * 60 * 24))
    
    let status: DataFreshness['status']
    if (days_old <= threshold_days) {
      status = 'FRESH'
    } else if (days_old <= threshold_days * 1.5) {
      status = 'STALE'
    } else {
      status = 'EXPIRED'
    }

    return {
      is_fresh: status === 'FRESH',
      days_old,
      threshold_days,
      status
    }
  }

  // ===== CACHE MANAGEMENT =====
  invalidateCache(pattern?: string): void {
    if (pattern) {
      // TODO: Implement pattern-based cache invalidation
      console.log(`Invalidating cache pattern: ${pattern}`)
    } else {
      this.cache.clear()
      console.log('Cache cleared')
    }
  }

  // ===== HEALTH CHECKS =====
  async healthCheck(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy'
    checks: Record<string, { status: string, latency_ms?: number, error?: string }>
  }> {
    const checks: Record<string, { status: string, latency_ms?: number, error?: string }> = {}
    
    // FRED API check
    try {
      const start = Date.now()
      await this.fetchFredSeries('DFF')
      checks.fred = { status: 'healthy', latency_ms: Date.now() - start }
    } catch (error) {
      checks.fred = { status: 'unhealthy', error: String(error) }
    }

    // Supabase check
    try {
      const start = Date.now()
      const { data, error } = await this.supabase.from('market_fundamentals').select('count').limit(1)
      if (error) throw error
      checks.supabase = { status: 'healthy', latency_ms: Date.now() - start }
    } catch (error) {
      checks.supabase = { status: 'unhealthy', error: String(error) }
    }

    // Overall status
    const unhealthy_count = Object.values(checks).filter(c => c.status === 'unhealthy').length
    const status = unhealthy_count === 0 ? 'healthy' : unhealthy_count < Object.keys(checks).length ? 'degraded' : 'unhealthy'

    return { status, checks }
  }
}

// ===== SINGLETON INSTANCE =====
let dataFetcherInstance: DataFetcher | null = null

export function getDataFetcher(): DataFetcher {
  if (!dataFetcherInstance) {
    dataFetcherInstance = new DataFetcher()
  }
  return dataFetcherInstance
}
