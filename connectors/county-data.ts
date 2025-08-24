/**
 * ===== COUNTY / CITY OPEN DATA CONNECTOR =====
 * Ingests property data from county assessor CSV files or open data APIs
 * 
 * Supported formats:
 * - CSV files (local or URL)
 * - JSON APIs (county-specific endpoints)
 * 
 * Common sources:
 * - Dallas County: https://www.dallascad.org/download-data/
 * - Cook County (Chicago): https://datacatalog.cookcountyil.gov/
 * - NYC DOF: https://data.cityofnewyork.us/Housing-Development/Property-Valuation-and-Assessment-Data/rgy2-tnr3
 * - LA County: https://portal.assessor.lacounty.gov/
 */

import fs from 'fs'
import Papa from 'papaparse'
import type { RawProperty, ConnectorResult, ConnectorOptions, DataProvenance } from '../lib/ingestion-types'

export interface CountyDataConfig {
  source_name: string
  file_path_or_url: string
  format: 'csv' | 'json_api'
  
  // Field mappings (county schemas vary widely)
  field_mappings: {
    apn_or_parcel_id?: string
    address?: string
    city?: string
    state?: string
    zip?: string
    building_sf?: string
    land_sf?: string
    year_built?: string
    assessed_value?: string
    owner_name?: string
    zoning_code?: string
  }
  
  // Data cleaning rules
  skip_rows_with_null?: string[] // Skip rows where these fields are null
  default_state?: string
  default_asset_type?: 'industrial' | 'office' | 'retail' | 'multifamily' | 'land' | 'other'
}

interface ParsedRow {
  [key: string]: string | number | null
}

export class CountyDataConnector {
  private config: CountyDataConfig
  
  constructor(config: CountyDataConfig) {
    this.config = config
  }
  
  async fetch(options: ConnectorOptions = {}): Promise<ConnectorResult<RawProperty>> {
    console.log(`📊 Fetching county data from: ${this.config.source_name}`)
    console.log(`   Source: ${this.config.file_path_or_url}`)
    console.log(`   Format: ${this.config.format}`)
    
    const started_at = new Date().toISOString()
    
    try {
      let rawRows: ParsedRow[]
      
      if (this.config.format === 'csv') {
        rawRows = await this.fetchCsvData(options)
      } else {
        rawRows = await this.fetchApiData(options)
      }
      
      console.log(`📥 Fetched ${rawRows.length} raw rows`)
      
      // Transform to RawProperty format
      const { properties, stats } = this.transformRows(rawRows)
      
      const provenance: DataProvenance = {
        source: this.config.source_name,
        as_of: started_at,
        from_cache: false
      }
      
      console.log(`✅ County data processed:`)
      console.log(`   Total fetched: ${stats.total_fetched}`)
      console.log(`   Valid properties: ${stats.total_valid}`)
      console.log(`   Skipped: ${stats.total_skipped}`)
      console.log(`   Errors: ${stats.errors.length}`)
      
      return {
        rows: properties,
        provenance,
        stats
      }
      
    } catch (error) {
      console.error(`❌ County data fetch failed:`, error)
      
      return {
        rows: [],
        provenance: {
          source: this.config.source_name,
          as_of: started_at,
          from_cache: false
        },
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [`Fetch failed: ${error instanceof Error ? error.message : String(error)}`]
        }
      }
    }
  }
  
  private async fetchCsvData(options: ConnectorOptions): Promise<ParsedRow[]> {
    console.log(`📄 Parsing CSV data...`)
    
    let csvContent: string
    
    // Handle URL vs local file
    if (this.config.file_path_or_url.startsWith('http')) {
      console.log(`🌐 Downloading CSV from URL...`)
      const response = await fetch(this.config.file_path_or_url)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      csvContent = await response.text()
    } else {
      console.log(`📁 Reading local CSV file...`)
      if (!fs.existsSync(this.config.file_path_or_url)) {
        throw new Error(`File not found: ${this.config.file_path_or_url}`)
      }
      csvContent = fs.readFileSync(this.config.file_path_or_url, 'utf-8')
    }
    
    // Parse CSV with Papa Parse
    const parseResult = Papa.parse<Record<string, string>>(csvContent, {
      header: true,
      skipEmptyLines: true,
      transform: (value: string) => value.trim()
    })
    
    if (parseResult.errors.length > 0) {
      console.warn(`⚠️ CSV parsing warnings:`, parseResult.errors)
    }
    
    let rows = parseResult.data
    
    // Apply offset and limit
    if (options.offset) {
      rows = rows.slice(options.offset)
    }
    
    if (options.limit) {
      rows = rows.slice(0, options.limit)
    }
    
    // Convert to ParsedRow format
    const parsedRows: ParsedRow[] = rows.map(row => {
      const parsedRow: ParsedRow = {}
      for (const [key, value] of Object.entries(row)) {
        if (value === '' || value === null || value === undefined) {
          parsedRow[key] = null
        } else if (!isNaN(Number(value)) && value.trim() !== '') {
          parsedRow[key] = Number(value)
        } else {
          parsedRow[key] = value
        }
      }
      return parsedRow
    })
    
    console.log(`📄 CSV parsing complete: ${parsedRows.length} rows`)
    return parsedRows
  }
  
  private async fetchApiData(options: ConnectorOptions): Promise<ParsedRow[]> {
    // For API endpoints, construct query parameters
    const params = new URLSearchParams()
    if (options.limit) params.append('$limit', options.limit.toString())
    if (options.offset) params.append('$offset', options.offset.toString())
    
    const url = `${this.config.file_path_or_url}?${params}`
    console.log(`🌐 Fetching from API: ${url}`)
    
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()
    
    // Most open data APIs return an array directly
    if (Array.isArray(data)) {
      return data
    }
    
    // Some APIs wrap in a 'data' or 'results' field
    if (data.data && Array.isArray(data.data)) {
      return data.data
    }
    
    if (data.results && Array.isArray(data.results)) {
      return data.results
    }
    
    throw new Error(`Unexpected API response format: ${typeof data}`)
  }
  
  private transformRows(rawRows: ParsedRow[]): { properties: RawProperty[], stats: any } {
    const properties: RawProperty[] = []
    const errors: string[] = []
    let skipped = 0
    
    for (let index = 0; index < rawRows.length; index++) {
      const row = rawRows[index]
      try {
        // Check skip conditions
        if (this.config.skip_rows_with_null) {
          let shouldSkip = false
          for (const requiredField of this.config.skip_rows_with_null) {
            const mappedField = this.config.field_mappings[requiredField as keyof typeof this.config.field_mappings] || requiredField
            if (!(row as any)[mappedField]) {
              shouldSkip = true
              break
            }
          }
          if (shouldSkip) {
            skipped++
            continue
          }
        }
        
        // Map fields according to configuration
        const property: RawProperty = {
          address: String(this.extractField(row, 'address') || `Unknown Address ${index}`),
          source: this.config.source_name,
          as_of: new Date().toISOString().split('T')[0] // Today's date for CSV data
        }
        
        // Optional fields
        const optionalMappings: (keyof RawProperty)[] = [
          'apn_or_parcel_id', 'city', 'state', 'zip',
          'building_sf', 'land_sf', 'year_built', 'assessed_value',
          'owner_name', 'zoning_code'
        ]
        
        for (const field of optionalMappings) {
          const value = this.extractField(row, field)
          if (value !== null && value !== undefined) {
            (property as any)[field] = value
          }
        }
        
        // Apply defaults
        if (this.config.default_state && !property.state) {
          property.state = this.config.default_state
        }
        
        if (this.config.default_asset_type) {
          property.asset_type = this.config.default_asset_type
        }
        
        // Basic validation
        if (!property.address || property.address.length < 5) {
          throw new Error('Invalid or missing address')
        }
        
        properties.push(property)
        
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error)
        errors.push(`Row ${index}: ${errorMsg}`)
        skipped++
      }
    }
    
    return {
      properties,
      stats: {
        total_fetched: rawRows.length,
        total_valid: properties.length,
        total_skipped: skipped,
        errors
      }
    }
  }
  
  private extractField(row: ParsedRow, field: keyof RawProperty): string | number | null {
    const mappedField = this.config.field_mappings[field as keyof typeof this.config.field_mappings]
    if (!mappedField) return null
    
    const value = (row as any)[mappedField]
    if (value === null || value === undefined || value === '') {
      return null
    }
    
    // For numeric fields, ensure proper conversion
    const numericFields = ['building_sf', 'land_sf', 'year_built', 'assessed_value']
    if (numericFields.includes(field) && typeof value === 'string') {
      const parsed = parseFloat(value.replace(/[,$]/g, ''))
      return isNaN(parsed) ? null : parsed
    }
    
    return value
  }
}

// ===== PREDEFINED COUNTY CONFIGURATIONS =====

export const DALLAS_COUNTY_CONFIG: CountyDataConfig = {
  source_name: 'Dallas County Assessor',
  file_path_or_url: 'https://www.dallascad.org/downloads/real_prop_data.csv',
  format: 'csv',
  field_mappings: {
    apn_or_parcel_id: 'ACCOUNT',
    address: 'PROPERTY_ADDRESS',
    city: 'PROPERTY_CITY', 
    state: 'PROPERTY_STATE',
    zip: 'PROPERTY_ZIP',
    building_sf: 'IMPROVEMENT_SF',
    land_sf: 'LAND_SF',
    year_built: 'YEAR_BUILT',
    assessed_value: 'APPRAISED_VALUE',
    owner_name: 'OWNER_NAME'
  },
  skip_rows_with_null: ['address'],
  default_state: 'TX',
  default_asset_type: 'other'
}

export const COOK_COUNTY_CONFIG: CountyDataConfig = {
  source_name: 'Cook County Assessor',
  file_path_or_url: 'https://datacatalog.cookcountyil.gov/resource/bcnq-qi2z.json',
  format: 'json_api',
  field_mappings: {
    apn_or_parcel_id: 'pin',
    address: 'property_address',
    city: 'property_city',
    state: 'property_state',
    zip: 'property_zip',
    building_sf: 'building_sqft',
    assessed_value: 'total_assessed_value'
  },
  skip_rows_with_null: ['property_address'],
  default_state: 'IL',
  default_asset_type: 'other'
}

// Export singleton instance with default configuration
export const countyDataConnector = new CountyDataConnector(COOK_COUNTY_CONFIG)
