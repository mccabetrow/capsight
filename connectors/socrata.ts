/**
 * ===== SOCRATA CONNECTOR =====
 * Fetches city/state open data from Socrata/ArcGIS platforms
 * Handles parcels, zoning, permits, deeds, assessments
 */

import type { ConnectorResult, DataProvenance, RawProperty } from '../lib/ingestion-types'

interface SocrataDataset {
  domain: string        // e.g., 'data.cityofnewyork.us'
  identifier: string    // e.g., 'bnx9-e6tj' (dataset ID)
  name: string
  description?: string
  columns: Record<string, string> // field mappings
}

interface SocrataRecord {
  [key: string]: any
}

export class SocrataConnector {
  private readonly cache = new Map<string, { data: SocrataRecord[], timestamp: number }>()
  private readonly cacheMs = 24 * 60 * 60 * 1000 // 24 hours
  private readonly rateLimitMs = 100 // Conservative rate limiting

  // Predefined datasets for major cities
  private readonly knownDatasets: Record<string, SocrataDataset[]> = {
    'nyc': [
      {
        domain: 'data.cityofnewyork.us',
        identifier: 'bnx9-e6tj', // Property Valuation and Assessment Data
        name: 'Property Valuation and Assessment Data',
        columns: {
          'block': 'block',
          'lot': 'lot',
          'address': 'address',
          'ownername': 'owner_name',
          'bldgclass': 'building_class',
          'taxclass': 'tax_class',
          'lotarea': 'land_sf',
          'bldgarea': 'building_sf',
          'yearbuilt': 'year_built',
          'assesstot': 'assessed_value'
        }
      }
    ],
    'chicago': [
      {
        domain: 'data.cityofchicago.org',
        identifier: 'bcnq-qi2z', // Building Permits
        name: 'Building Permits',
        columns: {
          'permit_': 'permit_id',
          'permit_type': 'permit_type',
          'work_description': 'description',
          'application_start_date': 'application_date',
          'street_number': 'street_number',
          'street_direction': 'street_direction',
          'street_name': 'street_name',
          'zip_code': 'zip'
        }
      }
    ],
    'dallas': [
      {
        domain: 'www.dallasopendata.com',
        identifier: 'example-dataset', // Placeholder - would need actual dataset IDs
        name: 'Dallas County Properties',
        columns: {
          'account_num': 'account_number',
          'property_address': 'address',
          'owner_name': 'owner_name',
          'land_square_footage': 'land_sf',
          'building_square_footage': 'building_sf',
          'year_built': 'year_built',
          'appraised_value': 'assessed_value'
        }
      }
    ]
  }

  async fetchCityData(
    cityKey: string,
    limit: number = 1000,
    offset: number = 0
  ): Promise<ConnectorResult<SocrataRecord>> {
    const startTime = Date.now()
    
    console.log(`🏛️ Fetching Socrata data for ${cityKey}...`)

    try {
      const datasets = this.knownDatasets[cityKey.toLowerCase()]
      if (!datasets) {
        throw new Error(`No known datasets for city: ${cityKey}`)
      }

      const allRecords: SocrataRecord[] = []
      const errors: string[] = []

      for (const dataset of datasets) {
        try {
          const cacheKey = `${dataset.domain}-${dataset.identifier}-${limit}-${offset}`
          
          // Check cache first
          const cached = this.getFromCache(cacheKey)
          if (cached) {
            allRecords.push(...cached)
            continue
          }

          const records = await this.fetchDataset(dataset, limit, offset)
          allRecords.push(...records)
          this.setCache(cacheKey, records)

          // Rate limiting
          await this.sleep(this.rateLimitMs)

        } catch (error) {
          const message = `Failed to fetch ${dataset.name}: ${error instanceof Error ? error.message : String(error)}`
          console.warn(`⚠️ ${message}`)
          errors.push(message)
        }
      }

      const duration = Date.now() - startTime
      console.log(`✅ Socrata fetch completed: ${allRecords.length} records in ${duration}ms`)

      return {
        rows: allRecords,
        provenance: this.createProvenance(cityKey),
        stats: {
          total_fetched: allRecords.length,
          total_valid: allRecords.length,
          total_skipped: 0,
          errors
        }
      }

    } catch (error) {
      console.error(`❌ Socrata connector failed: ${error instanceof Error ? error.message : String(error)}`)
      return {
        rows: [],
        provenance: this.createProvenance(cityKey, false, true),
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [error instanceof Error ? error.message : String(error)]
        }
      }
    }
  }

  async fetchCustomDataset(
    domain: string,
    identifier: string,
    fieldMappings: Record<string, string>,
    limit: number = 1000,
    filters?: Record<string, string>
  ): Promise<ConnectorResult<SocrataRecord>> {
    const startTime = Date.now()
    
    console.log(`🏛️ Fetching custom Socrata dataset ${domain}/${identifier}...`)

    try {
      const dataset: SocrataDataset = {
        domain,
        identifier,
        name: `Custom Dataset (${identifier})`,
        columns: fieldMappings
      }

      const records = await this.fetchDataset(dataset, limit, 0, filters)

      const duration = Date.now() - startTime
      console.log(`✅ Custom dataset fetch completed: ${records.length} records in ${duration}ms`)

      return {
        rows: records,
        provenance: this.createProvenance(`${domain}/${identifier}`),
        stats: {
          total_fetched: records.length,
          total_valid: records.length,
          total_skipped: 0,
          errors: []
        }
      }

    } catch (error) {
      console.error(`❌ Custom Socrata fetch failed: ${error instanceof Error ? error.message : String(error)}`)
      return {
        rows: [],
        provenance: this.createProvenance(`${domain}/${identifier}`, false, true),
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [error instanceof Error ? error.message : String(error)]
        }
      }
    }
  }

  private async fetchDataset(
    dataset: SocrataDataset,
    limit: number,
    offset: number,
    filters?: Record<string, string>
  ): Promise<SocrataRecord[]> {
    
    const params = new URLSearchParams({
      '$limit': limit.toString(),
      '$offset': offset.toString(),
      '$format': 'json'
    })

    // Add filters if provided
    if (filters) {
      for (const [field, value] of Object.entries(filters)) {
        params.set(field, value)
      }
    }

    const url = `https://${dataset.domain}/resource/${dataset.identifier}.json?${params}`
    
    try {
      const response = await fetch(url, {
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'CapSight/1.0'
        }
      })

      if (!response.ok) {
        throw new Error(`Socrata API error: ${response.status} ${response.statusText}`)
      }

      const rawData = await response.json()

      if (!Array.isArray(rawData)) {
        throw new Error('Invalid Socrata API response format')
      }

      // Normalize field names using column mappings
      return rawData.map(record => this.normalizeRecord(record, dataset.columns))

    } catch (error) {
      throw new Error(`Failed to fetch dataset ${dataset.identifier}: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private normalizeRecord(record: any, columnMappings: Record<string, string>): SocrataRecord {
    const normalized: SocrataRecord = {}

    for (const [sourceField, targetField] of Object.entries(columnMappings)) {
      const value = record[sourceField]
      if (value !== undefined && value !== null && value !== '') {
        normalized[targetField] = value
      }
    }

    // Keep original record for reference
    normalized._original = record

    return normalized
  }

  private getFromCache(key: string): SocrataRecord[] | null {
    const cached = this.cache.get(key)
    if (!cached) return null
    
    if (Date.now() - cached.timestamp > this.cacheMs) {
      this.cache.delete(key)
      return null
    }
    
    console.log(`🏛️ Using cached Socrata data for ${key}`)
    return cached.data
  }

  private setCache(key: string, data: SocrataRecord[]): void {
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
      source: `Socrata Open Data - ${source}`,
      as_of: new Date().toISOString(),
      from_cache: fromCache,
      ...(hasError && { error: true })
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // Convert Socrata records to RawProperty format
  static toRawProperties(
    socrataRecords: SocrataRecord[],
    cityKey: string,
    sourceType: 'assessment' | 'permit' | 'deed' | 'zoning' = 'assessment'
  ): RawProperty[] {
    const asOf = new Date().toISOString()
    
    return socrataRecords.map(record => ({
      source_id: this.generateSourceId(record, cityKey),
      source: `Socrata - ${cityKey}`,
      as_of: asOf,
      address: this.extractAddress(record),
      city: this.extractCity(record, cityKey),
      state: this.extractState(cityKey),
      zip: record.zip || record.zipcode || record.zip_code,
      building_sf: this.parseNumeric(record.building_sf || record.bldg_sf || record.gross_sf),
      land_sf: this.parseNumeric(record.land_sf || record.lot_sf || record.lot_area),
      year_built: this.parseNumeric(record.year_built || record.yearbuilt),
      zoning_code: record.zoning || record.zone || record.zoning_code,
      assessed_value: this.parseNumeric(record.assessed_value || record.total_value),
      owner_name: record.owner_name || record.ownername || record.owner,
      owner_entity_id: undefined,
      lat: this.parseNumeric(record.latitude || record.lat),
      lon: this.parseNumeric(record.longitude || record.lon),
      raw_data: {
        source_type: sourceType,
        city_key: cityKey,
        original_record: record._original,
        ...record
      }
    })).filter(prop => prop.address) // Only include records with valid addresses
  }

  private static generateSourceId(record: SocrataRecord, cityKey: string): string {
    // Try to use unique identifiers from the record
    const uniqueFields = [
      record.account_number,
      record.permit_id,
      record.parcel_id,
      record.pin,
      record.block && record.lot ? `${record.block}-${record.lot}` : null,
      record.address
    ].filter(Boolean)

    const identifier = uniqueFields[0] || JSON.stringify(record).slice(0, 50)
    return `socrata-${cityKey}-${Buffer.from(identifier).toString('hex').slice(0, 16)}`
  }

  private static extractAddress(record: SocrataRecord): string {
    // Try various address field patterns
    const addressFields = [
      record.address,
      record.property_address,
      record.site_address,
      record.full_address,
      `${record.street_number || ''} ${record.street_direction || ''} ${record.street_name || ''}`.trim()
    ].filter(Boolean)

    return addressFields[0] || ''
  }

  private static extractCity(record: SocrataRecord, cityKey: string): string {
    return record.city || this.getCityNameFromKey(cityKey)
  }

  private static extractState(cityKey: string): string {
    const stateMap: Record<string, string> = {
      'nyc': 'NY',
      'chicago': 'IL', 
      'dallas': 'TX',
      'la': 'CA',
      'miami': 'FL'
    }
    return stateMap[cityKey.toLowerCase()] || 'Unknown'
  }

  private static getCityNameFromKey(cityKey: string): string {
    const cityMap: Record<string, string> = {
      'nyc': 'New York',
      'chicago': 'Chicago',
      'dallas': 'Dallas',
      'la': 'Los Angeles',
      'miami': 'Miami'
    }
    return cityMap[cityKey.toLowerCase()] || cityKey
  }

  private static parseNumeric(value: any): number | undefined {
    if (value === null || value === undefined || value === '') return undefined
    
    const num = parseFloat(String(value).replace(/[,$]/g, ''))
    return isNaN(num) ? undefined : num
  }

  // Get available datasets for a city
  getAvailableDatasets(cityKey: string): SocrataDataset[] {
    return this.knownDatasets[cityKey.toLowerCase()] || []
  }
}

// Singleton export
export const socrataConnector = new SocrataConnector()
