/**
 * ===== HUD USER CONNECTOR =====
 * Fetches Fair Market Rents (FMR), Income Limits, and geographic crosswalks
 * Uses HUD USER API and USPS ZIP code crosswalks
 */

import type { ConnectorResult, DataProvenance } from '../lib/ingestion-types'

interface HudFmrData {
  area_name: string
  area_code: string
  state_code: string
  year: number
  efficiency_fmr: number
  one_br_fmr: number
  two_br_fmr: number
  three_br_fmr: number
  four_br_fmr: number
}

interface HudIncomeLimits {
  area_name: string
  area_code: string
  state_code: string
  year: number
  median_family_income: number
  very_low_income_4person: number
  low_income_4person: number
  moderate_income_4person: number
}

interface ZipCrosswalk {
  zip_code: string
  county_code: string
  county_name: string
  state_code: string
  msa_code?: string
  msa_name?: string
}

export class HudConnector {
  private readonly baseUrl = 'https://www.huduser.gov/hudapi/public'
  private readonly cache = new Map<string, { data: any, timestamp: number }>()
  private readonly cacheMs = 24 * 60 * 60 * 1000 // 24 hours
  
  constructor(private apiToken?: string) {
    if (!apiToken) {
      console.log('🏠 HUD API token not provided - may have rate limits')
    }
  }

  async fetchFairMarketRents(
    stateCode?: string,
    year: number = new Date().getFullYear()
  ): Promise<ConnectorResult<HudFmrData>> {
    const startTime = Date.now()
    
    console.log(`🏠 Fetching HUD Fair Market Rents for ${year}${stateCode ? ` in ${stateCode}` : ''}...`)

    try {
      const cacheKey = `fmr-${stateCode || 'all'}-${year}`
      
      // Check cache first
      const cached = this.getFromCache(cacheKey)
      if (cached) {
        return {
          rows: cached,
          provenance: this.createProvenance('HUD Fair Market Rents', true),
          stats: {
            total_fetched: cached.length,
            total_valid: cached.length,
            total_skipped: 0,
            errors: []
          }
        }
      }

      const data = await this.fetchFMRData(stateCode, year)
      this.setCache(cacheKey, data)

      const duration = Date.now() - startTime
      console.log(`✅ HUD FMR fetch completed: ${data.length} areas in ${duration}ms`)

      return {
        rows: data,
        provenance: this.createProvenance('HUD Fair Market Rents'),
        stats: {
          total_fetched: data.length,
          total_valid: data.length,
          total_skipped: 0,
          errors: []
        }
      }

    } catch (error) {
      console.error(`❌ HUD FMR connector failed: ${error instanceof Error ? error.message : String(error)}`)
      return {
        rows: [],
        provenance: this.createProvenance('HUD Fair Market Rents', false, true),
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [error instanceof Error ? error.message : String(error)]
        }
      }
    }
  }

  async fetchIncomeLimits(
    stateCode?: string,
    year: number = new Date().getFullYear()
  ): Promise<ConnectorResult<HudIncomeLimits>> {
    const startTime = Date.now()
    
    console.log(`💰 Fetching HUD Income Limits for ${year}${stateCode ? ` in ${stateCode}` : ''}...`)

    try {
      const cacheKey = `income-${stateCode || 'all'}-${year}`
      
      // Check cache first
      const cached = this.getFromCache(cacheKey)
      if (cached) {
        return {
          rows: cached,
          provenance: this.createProvenance('HUD Income Limits', true),
          stats: {
            total_fetched: cached.length,
            total_valid: cached.length,
            total_skipped: 0,
            errors: []
          }
        }
      }

      const data = await this.fetchIncomeData(stateCode, year)
      this.setCache(cacheKey, data)

      const duration = Date.now() - startTime
      console.log(`✅ HUD Income Limits fetch completed: ${data.length} areas in ${duration}ms`)

      return {
        rows: data,
        provenance: this.createProvenance('HUD Income Limits'),
        stats: {
          total_fetched: data.length,
          total_valid: data.length,
          total_skipped: 0,
          errors: []
        }
      }

    } catch (error) {
      console.error(`❌ HUD Income Limits connector failed: ${error instanceof Error ? error.message : String(error)}`)
      return {
        rows: [],
        provenance: this.createProvenance('HUD Income Limits', false, true),
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [error instanceof Error ? error.message : String(error)]
        }
      }
    }
  }

  async fetchZipCrosswalks(): Promise<ConnectorResult<ZipCrosswalk>> {
    const startTime = Date.now()
    
    console.log(`📮 Fetching USPS ZIP code crosswalks...`)

    try {
      const cacheKey = 'zip-crosswalks'
      
      // Check cache first  
      const cached = this.getFromCache(cacheKey)
      if (cached) {
        return {
          rows: cached,
          provenance: this.createProvenance('USPS ZIP Crosswalks', true),
          stats: {
            total_fetched: cached.length,
            total_valid: cached.length,
            total_skipped: 0,
            errors: []
          }
        }
      }

      const data = await this.fetchCrosswalkData()
      this.setCache(cacheKey, data)

      const duration = Date.now() - startTime
      console.log(`✅ ZIP crosswalks fetch completed: ${data.length} ZIP codes in ${duration}ms`)

      return {
        rows: data,
        provenance: this.createProvenance('USPS ZIP Crosswalks'),
        stats: {
          total_fetched: data.length,
          total_valid: data.length,
          total_skipped: 0,
          errors: []
        }
      }

    } catch (error) {
      console.error(`❌ ZIP crosswalks connector failed: ${error instanceof Error ? error.message : String(error)}`)
      return {
        rows: [],
        provenance: this.createProvenance('USPS ZIP Crosswalks', false, true),
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [error instanceof Error ? error.message : String(error)]
        }
      }
    }
  }

  private async fetchFMRData(stateCode: string | undefined, year: number): Promise<HudFmrData[]> {
    let url = `${this.baseUrl}/fmr/listmetros`
    
    if (stateCode) {
      url += `/${stateCode}`
    }

    const headers: Record<string, string> = {
      'Accept': 'application/json'
    }

    if (this.apiToken) {
      headers['Authorization'] = `Bearer ${this.apiToken}`
    }

    try {
      const response = await fetch(url, { headers })
      
      if (!response.ok) {
        throw new Error(`HUD FMR API error: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      
      if (!data.data || !Array.isArray(data.data.items)) {
        console.warn('⚠️ Unexpected HUD FMR API response format')
        return []
      }

      // Transform HUD API response to our format
      return data.data.items.map((item: any) => ({
        area_name: item.area_name || item.metro_name || 'Unknown',
        area_code: item.area_code || item.metro_code || '',
        state_code: item.state_code || stateCode || '',
        year,
        efficiency_fmr: parseFloat(item.efficiency) || 0,
        one_br_fmr: parseFloat(item.onebr) || 0,
        two_br_fmr: parseFloat(item.twobr) || 0,
        three_br_fmr: parseFloat(item.threebr) || 0,
        four_br_fmr: parseFloat(item.fourbr) || 0
      })).filter((item: HudFmrData) => item.area_name !== 'Unknown')

    } catch (error) {
      throw new Error(`Failed to fetch FMR data: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private async fetchIncomeData(stateCode: string | undefined, year: number): Promise<HudIncomeLimits[]> {
    let url = `${this.baseUrl}/il`
    
    if (stateCode) {
      url += `/${stateCode}`
    }

    const headers: Record<string, string> = {
      'Accept': 'application/json'
    }

    if (this.apiToken) {
      headers['Authorization'] = `Bearer ${this.apiToken}`
    }

    try {
      const response = await fetch(url, { headers })
      
      if (!response.ok) {
        throw new Error(`HUD Income Limits API error: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      
      if (!data.data || !Array.isArray(data.data.items)) {
        console.warn('⚠️ Unexpected HUD Income Limits API response format')
        return []
      }

      // Transform HUD API response to our format
      return data.data.items.map((item: any) => ({
        area_name: item.area_name || item.metro_name || 'Unknown',
        area_code: item.area_code || item.metro_code || '',
        state_code: item.state_code || stateCode || '',
        year,
        median_family_income: parseFloat(item.median_income) || 0,
        very_low_income_4person: parseFloat(item.vli_4person) || 0,
        low_income_4person: parseFloat(item.li_4person) || 0,
        moderate_income_4person: parseFloat(item.mi_4person) || 0
      })).filter((item: HudIncomeLimits) => item.area_name !== 'Unknown')

    } catch (error) {
      throw new Error(`Failed to fetch Income Limits data: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private async fetchCrosswalkData(): Promise<ZipCrosswalk[]> {
    // This would typically fetch from HUD's crosswalk files
    // For now, return empty array - would need specific crosswalk file URLs
    console.warn('⚠️ ZIP crosswalk data requires specific file endpoint implementation')
    return []
  }

  private getFromCache(key: string): any | null {
    const cached = this.cache.get(key)
    if (!cached) return null
    
    if (Date.now() - cached.timestamp > this.cacheMs) {
      this.cache.delete(key)
      return null
    }
    
    console.log(`🏠 Using cached HUD data for ${key}`)
    return cached.data
  }

  private setCache(key: string, data: any): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    })
  }

  private createProvenance(
    source: string, 
    fromCache: boolean = false, 
    hasError: boolean = false
  ): DataProvenance {
    return {
      source: `HUD USER - ${source}`,
      as_of: new Date().toISOString(),
      from_cache: fromCache,
      ...(hasError && { error: true })
    }
  }

  // Helper methods for rent reasonableness checks
  
  getFmrForBedrooms(fmrData: HudFmrData[], areaCode: string, bedrooms: number): number | null {
    const area = fmrData.find(d => d.area_code === areaCode)
    if (!area) return null
    
    switch (bedrooms) {
      case 0: return area.efficiency_fmr
      case 1: return area.one_br_fmr
      case 2: return area.two_br_fmr
      case 3: return area.three_br_fmr
      case 4: return area.four_br_fmr
      default: return area.four_br_fmr // Cap at 4BR
    }
  }

  isRentReasonable(marketRent: number, fmr: number, tolerance: number = 0.1): boolean {
    if (!fmr || fmr <= 0) return true // Can't verify, assume reasonable
    
    const ratio = marketRent / fmr
    return ratio >= (1 - tolerance) && ratio <= (1 + tolerance)
  }

  getAffordabilityRatio(rent: number, income: number): number {
    if (!income || income <= 0) return Infinity
    return (rent * 12) / income
  }
}

// Singleton export
export const hudConnector = new HudConnector(process.env.HUD_API_TOKEN)
