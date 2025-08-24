/**
 * ===== FRED CONNECTOR =====
 * Fetches macroeconomic data from Federal Reserve Economic Data
 * Includes Fed Funds Rate, 10-Year Treasury, CRE lending rates
 */

import type { ConnectorResult, DataProvenance } from '../lib/ingestion-types'

interface FredSeries {
  id: string
  title: string
  units: string
}

interface FredObservation {
  date: string
  value: string
}

interface FredData {
  series_id: string
  series_name: string
  date: string
  value: number
  units: string
}

export class FredConnector {
  private readonly baseUrl = 'https://api.stlouisfed.org/fred'
  private readonly defaultSeries = [
    'DFF',      // Federal Funds Rate
    'GS10',     // 10-Year Treasury
    'OBMMICRE', // CRE Lending Rate (if available)
    'MORTGAGE30US' // 30-Year Fixed Rate Mortgage
  ]
  private readonly cache = new Map<string, { data: FredData[], timestamp: number }>()
  private readonly cacheMs = 30 * 60 * 1000 // 30 minutes

  constructor(private apiKey?: string) {
    if (!apiKey) {
      console.warn('⚠️ FRED API key not provided - using public endpoints only')
    }
  }

  async fetchMacroData(seriesIds?: string[]): Promise<ConnectorResult<FredData>> {
    const startTime = Date.now()
    const series = seriesIds || this.defaultSeries
    
    console.log(`📊 Fetching FRED macro data for ${series.length} series...`)

    try {
      const allData: FredData[] = []
      const errors: string[] = []

      for (const seriesId of series) {
        try {
          const cached = this.getFromCache(seriesId)
          if (cached) {
            allData.push(...cached)
            continue
          }

          const seriesData = await this.fetchSeries(seriesId)
          if (seriesData.length > 0) {
            allData.push(...seriesData)
            this.setCache(seriesId, seriesData)
          }
          
          // Rate limit: 5 requests per minute for free tier
          await this.sleep(200)
          
        } catch (error) {
          const message = `Failed to fetch ${seriesId}: ${error instanceof Error ? error.message : String(error)}`
          console.warn(`⚠️ ${message}`)
          errors.push(message)
        }
      }

      const duration = Date.now() - startTime
      console.log(`✅ FRED fetch completed: ${allData.length} observations in ${duration}ms`)

      return {
        rows: allData,
        provenance: this.createProvenance(),
        stats: {
          total_fetched: series.length,
          total_valid: allData.length,
          total_skipped: series.length - new Set(allData.map(d => d.series_id)).size,
          errors
        }
      }

    } catch (error) {
      console.error(`❌ FRED connector failed: ${error instanceof Error ? error.message : String(error)}`)
      return {
        rows: [],
        provenance: this.createProvenance(true),
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [error instanceof Error ? error.message : String(error)]
        }
      }
    }
  }

  private async fetchSeries(seriesId: string): Promise<FredData[]> {
    // First get series info
    const seriesInfo = await this.fetchSeriesInfo(seriesId)
    
    // Then get observations (most recent 12 months)
    const observations = await this.fetchObservations(seriesId)
    
    return observations.map(obs => ({
      series_id: seriesId,
      series_name: seriesInfo.title,
      date: obs.date,
      value: parseFloat(obs.value),
      units: seriesInfo.units
    })).filter(d => !isNaN(d.value))
  }

  private async fetchSeriesInfo(seriesId: string): Promise<FredSeries> {
    const params = new URLSearchParams({
      series_id: seriesId,
      file_type: 'json'
    })
    
    if (this.apiKey) {
      params.set('api_key', this.apiKey)
    }

    const url = `${this.baseUrl}/series?${params}`
    
    try {
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`FRED series API error: ${response.status}`)
      }
      
      const data = await response.json()
      
      if (!data.seriess || data.seriess.length === 0) {
        throw new Error(`Series ${seriesId} not found`)
      }
      
      return data.seriess[0]
      
    } catch (error) {
      throw new Error(`Failed to fetch series info for ${seriesId}: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private async fetchObservations(seriesId: string): Promise<FredObservation[]> {
    const params = new URLSearchParams({
      series_id: seriesId,
      file_type: 'json',
      limit: '12', // Last 12 observations
      sort_order: 'desc'
    })
    
    if (this.apiKey) {
      params.set('api_key', this.apiKey)
    }

    const url = `${this.baseUrl}/series/observations?${params}`
    
    try {
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`FRED observations API error: ${response.status}`)
      }
      
      const data = await response.json()
      
      return data.observations || []
      
    } catch (error) {
      throw new Error(`Failed to fetch observations for ${seriesId}: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private getFromCache(seriesId: string): FredData[] | null {
    const cached = this.cache.get(seriesId)
    if (!cached) return null
    
    if (Date.now() - cached.timestamp > this.cacheMs) {
      this.cache.delete(seriesId)
      return null
    }
    
    console.log(`📊 Using cached FRED data for ${seriesId}`)
    return cached.data
  }

  private setCache(seriesId: string, data: FredData[]): void {
    this.cache.set(seriesId, {
      data,
      timestamp: Date.now()
    })
  }

  private createProvenance(hasError: boolean = false): DataProvenance {
    const fromCache = this.cache.size > 0
    return {
      source: 'FRED (Federal Reserve Economic Data)',
      as_of: new Date().toISOString(),
      from_cache: fromCache,
      ...(hasError && { error: true })
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // Get most recent value for a series
  getMostRecentValue(data: FredData[], seriesId: string): number | null {
    const seriesData = data
      .filter(d => d.series_id === seriesId)
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    
    return seriesData.length > 0 ? seriesData[0].value : null
  }

  // Calculate term spread (GS10 - DFF)
  getTermSpread(data: FredData[]): number | null {
    const gs10 = this.getMostRecentValue(data, 'GS10')
    const dff = this.getMostRecentValue(data, 'DFF')
    
    if (gs10 === null || dff === null) return null
    
    return gs10 - dff
  }

  // Get cache statistics
  getCacheStats() {
    return {
      total_cached_series: this.cache.size,
      cache_ttl_minutes: this.cacheMs / (60 * 1000),
      cached_series: Array.from(this.cache.keys())
    }
  }
}

// Singleton export
export const fredConnector = new FredConnector(process.env.FRED_API_KEY)
