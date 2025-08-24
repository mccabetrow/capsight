/**
 * ===== U.S. CENSUS / ACS CONNECTOR =====
 * Fetches demographics, income, and building permit data
 * Uses American Community Survey (ACS) 5-year estimates and Building Permit Survey (BPS)
 */

import type { ConnectorResult, DataProvenance } from '../lib/ingestion-types'

interface CensusVariable {
  name: string
  label: string
  concept?: string
}

interface CensusData {
  geography_type: 'county' | 'tract' | 'zip' | 'msa'
  geography_id: string
  geography_name: string
  variable_name: string
  variable_label: string
  value: number
  margin_of_error?: number
  year: number
  survey: string
}

interface BuildingPermitData {
  area_name: string
  area_code: string
  state_code: string
  year: number
  month: number
  permit_type: 'single_family' | 'multi_family' | 'total'
  units_authorized: number
  value_thousands: number
}

export class CensusConnector {
  private readonly baseUrl = 'https://api.census.gov/data'
  private readonly currentYear = 2022 // Most recent ACS 5-year
  private readonly cache = new Map<string, { data: any, timestamp: number }>()
  private readonly cacheMs = 24 * 60 * 60 * 1000 // 24 hours

  // Key demographic and economic variables
  private readonly defaultVariables = {
    // Population
    'B01003_001E': 'Total Population',
    'B25001_001E': 'Total Housing Units',
    
    // Income
    'B19013_001E': 'Median Household Income',
    'B25064_001E': 'Median Gross Rent',
    
    // Education
    'B15003_022E': 'Bachelor\'s Degree',
    'B15003_023E': 'Master\'s Degree',
    
    // Employment
    'B23025_005E': 'Unemployed',
    'B08301_010E': 'Public Transportation to Work',
    
    // Housing
    'B25077_001E': 'Median Home Value',
    'B25003_002E': 'Owner Occupied Housing Units',
    'B25003_003E': 'Renter Occupied Housing Units'
  }

  constructor(private apiKey?: string) {
    if (!apiKey) {
      console.log('📊 Census API key not provided - using public endpoints (may have rate limits)')
    }
  }

  async fetchDemographics(
    geographyType: 'county' | 'tract' | 'zip' = 'county',
    stateCode?: string,
    variables?: string[]
  ): Promise<ConnectorResult<CensusData>> {
    const startTime = Date.now()
    
    console.log(`📊 Fetching Census ACS data for ${geographyType}${stateCode ? ` in state ${stateCode}` : ''}...`)

    try {
      const varsToFetch = variables || Object.keys(this.defaultVariables)
      const cacheKey = `acs-${geographyType}-${stateCode || 'all'}-${varsToFetch.join(',')}`
      
      // Check cache first
      const cached = this.getFromCache(cacheKey)
      if (cached) {
        return {
          rows: cached,
          provenance: this.createProvenance(true),
          stats: {
            total_fetched: cached.length,
            total_valid: cached.length,
            total_skipped: 0,
            errors: []
          }
        }
      }

      const data = await this.fetchACSData(geographyType, stateCode, varsToFetch)
      this.setCache(cacheKey, data)

      const duration = Date.now() - startTime
      console.log(`✅ Census ACS fetch completed: ${data.length} observations in ${duration}ms`)

      return {
        rows: data,
        provenance: this.createProvenance(),
        stats: {
          total_fetched: data.length,
          total_valid: data.length,
          total_skipped: 0,
          errors: []
        }
      }

    } catch (error) {
      console.error(`❌ Census connector failed: ${error instanceof Error ? error.message : String(error)}`)
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

  async fetchBuildingPermits(
    stateCode?: string,
    monthsBack: number = 12
  ): Promise<ConnectorResult<BuildingPermitData>> {
    const startTime = Date.now()
    
    console.log(`🏗️ Fetching Building Permits data for ${monthsBack} months...`)

    try {
      const data = await this.fetchBPSData(stateCode, monthsBack)

      const duration = Date.now() - startTime
      console.log(`✅ Building Permits fetch completed: ${data.length} observations in ${duration}ms`)

      return {
        rows: data,
        provenance: {
          source: 'U.S. Census Building Permit Survey (BPS)',
          as_of: new Date().toISOString(),
          from_cache: false
        },
        stats: {
          total_fetched: data.length,
          total_valid: data.length,
          total_skipped: 0,
          errors: []
        }
      }

    } catch (error) {
      console.error(`❌ Building Permits connector failed: ${error instanceof Error ? error.message : String(error)}`)
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

  private async fetchACSData(
    geographyType: string,
    stateCode: string | undefined,
    variables: string[]
  ): Promise<CensusData[]> {
    
    const variableString = variables.join(',')
    let geography: string
    
    switch (geographyType) {
      case 'county':
        geography = stateCode ? `county:*&in=state:${stateCode}` : 'county:*'
        break
      case 'tract':
        geography = stateCode ? `tract:*&in=state:${stateCode}` : 'tract:*&in=state:*'
        break
      case 'zip':
        geography = 'zip code tabulation area:*'
        break
      default:
        throw new Error(`Unsupported geography type: ${geographyType}`)
    }

    const params = new URLSearchParams({
      get: variableString,
      for: geography
    })

    if (this.apiKey) {
      params.set('key', this.apiKey)
    }

    const url = `${this.baseUrl}/${this.currentYear}/acs/acs5?${params}`
    
    try {
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`Census API error: ${response.status} ${response.statusText}`)
      }
      
      const rawData = await response.json()
      
      if (!Array.isArray(rawData) || rawData.length < 2) {
        throw new Error('Invalid Census API response format')
      }
      
      return this.parseACSResponse(rawData, geographyType)
      
    } catch (error) {
      throw new Error(`Failed to fetch ACS data: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private parseACSResponse(rawData: any[][], geographyType: string): CensusData[] {
    const headers = rawData[0]
    const rows = rawData.slice(1)
    
    const result: CensusData[] = []
    
    for (const row of rows) {
      const geoName = this.extractGeographyName(row, headers, geographyType)
      const geoId = this.extractGeographyId(row, headers, geographyType)
      
      // Skip if no valid geography
      if (!geoName || !geoId) continue
      
      for (let i = 0; i < headers.length; i++) {
        const header = headers[i]
        const value = row[i]
        
        // Skip geography columns and null values
        if (this.isGeographyColumn(header) || value === null || value === '-') continue
        
        const numericValue = parseFloat(value)
        if (isNaN(numericValue)) continue
        
        const variableLabel = (this.defaultVariables as Record<string, string>)[header] || header
        
        result.push({
          geography_type: geographyType as any,
          geography_id: geoId,
          geography_name: geoName,
          variable_name: header,
          variable_label: variableLabel,
          value: numericValue,
          year: this.currentYear,
          survey: 'ACS 5-Year'
        })
      }
    }
    
    return result
  }

  private extractGeographyName(row: any[], headers: string[], geographyType: string): string | null {
    // Geography name is usually in a column ending with 'NAME' or similar
    const nameIndex = headers.findIndex(h => h.toLowerCase().includes('name'))
    return nameIndex !== -1 ? row[nameIndex] : null
  }

  private extractGeographyId(row: any[], headers: string[], geographyType: string): string | null {
    // Geography ID varies by type
    switch (geographyType) {
      case 'county':
        const stateIndex = headers.indexOf('state')
        const countyIndex = headers.indexOf('county')
        if (stateIndex !== -1 && countyIndex !== -1) {
          return `${row[stateIndex]}${row[countyIndex]}`
        }
        break
      case 'tract':
        const tractStateIndex = headers.indexOf('state')
        const tractCountyIndex = headers.indexOf('county')
        const tractIndex = headers.indexOf('tract')
        if (tractStateIndex !== -1 && tractCountyIndex !== -1 && tractIndex !== -1) {
          return `${row[tractStateIndex]}${row[tractCountyIndex]}${row[tractIndex]}`
        }
        break
      case 'zip':
        const zipIndex = headers.indexOf('zip code tabulation area')
        return zipIndex !== -1 ? row[zipIndex] : null
    }
    
    return null
  }

  private isGeographyColumn(header: string): boolean {
    const geoCols = ['state', 'county', 'tract', 'zip code tabulation area', 'name']
    return geoCols.some(col => header.toLowerCase().includes(col.toLowerCase()))
  }

  private async fetchBPSData(stateCode: string | undefined, monthsBack: number): Promise<BuildingPermitData[]> {
    // Building Permit Survey data - this would need actual BPS API endpoints
    // For now, return empty array as BPS data requires specific endpoints
    console.warn('⚠️ Building Permit Survey data requires specific endpoint implementation')
    return []
  }

  private getFromCache(key: string): CensusData[] | null {
    const cached = this.cache.get(key)
    if (!cached) return null
    
    if (Date.now() - cached.timestamp > this.cacheMs) {
      this.cache.delete(key)
      return null
    }
    
    console.log(`📊 Using cached Census data for ${key}`)
    return cached.data
  }

  private setCache(key: string, data: CensusData[]): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    })
  }

  private createProvenance(fromCache: boolean = false): DataProvenance {
    return {
      source: 'U.S. Census Bureau / American Community Survey',
      as_of: new Date().toISOString(),
      from_cache: fromCache
    }
  }

  // Helper methods for common queries
  
  getMedianIncome(data: CensusData[], geoId: string): number | null {
    const income = data.find(d => 
      d.geography_id === geoId && 
      d.variable_name === 'B19013_001E'
    )
    return income ? income.value : null
  }

  getMedianRent(data: CensusData[], geoId: string): number | null {
    const rent = data.find(d => 
      d.geography_id === geoId && 
      d.variable_name === 'B25064_001E'
    )
    return rent ? rent.value : null
  }

  getHomeownershipRate(data: CensusData[], geoId: string): number | null {
    const ownerOccupied = data.find(d => 
      d.geography_id === geoId && 
      d.variable_name === 'B25003_002E'
    )?.value
    
    const renterOccupied = data.find(d => 
      d.geography_id === geoId && 
      d.variable_name === 'B25003_003E'
    )?.value
    
    if (!ownerOccupied || !renterOccupied) return null
    
    const total = ownerOccupied + renterOccupied
    return total > 0 ? (ownerOccupied / total) * 100 : null
  }
}

// Singleton export
export const censusConnector = new CensusConnector(process.env.CENSUS_API_KEY)
