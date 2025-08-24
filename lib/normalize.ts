/**
 * ===== DATA NORMALIZATION SERVICE =====
 * Normalizes heterogeneous property data into CapSight's standard schema
 */

import crypto from 'crypto'
import { geocodeService } from './geocode'
import type { RawProperty, CapsightProperty, AssetType, DataProvenance } from './ingestion-types'

export interface NormalizationResult {
  properties: CapsightProperty[]
  stats: {
    total_processed: number
    successfully_normalized: number
    geocoding_failures: number
    validation_failures: number
    errors: string[]
  }
}

export class PropertyNormalizer {
  
  async normalize(rawProperties: RawProperty[]): Promise<NormalizationResult> {
    console.log(`🔄 Normalizing ${rawProperties.length} raw properties...`)
    
    const properties: CapsightProperty[] = []
    const errors: string[] = []
    let geocodingFailures = 0
    let validationFailures = 0
    
    // First pass: normalize addresses for geocoding
    const addressesToGeocode = new Set<string>()
    const addressMap = new Map<string, RawProperty[]>()
    
    for (const raw of rawProperties) {
      const cleanAddress = this.cleanAddress(raw.address, raw.city, raw.state)
      addressesToGeocode.add(cleanAddress)
      
      if (!addressMap.has(cleanAddress)) {
        addressMap.set(cleanAddress, [])
      }
      addressMap.get(cleanAddress)!.push(raw)
    }
    
    console.log(`📍 Geocoding ${addressesToGeocode.size} unique addresses...`)
    
    // Batch geocode all unique addresses
    const geocodeResults = await geocodeService.geocodeBatch(Array.from(addressesToGeocode))
    
    // Second pass: create normalized properties
    const cleanAddresses = Array.from(addressMap.keys())
    for (const cleanAddress of cleanAddresses) {
      const rawsForAddress = addressMap.get(cleanAddress)!
      const geocodeResult = geocodeResults.get(cleanAddress)
      
      if (!geocodeResult) {
        geocodingFailures++
        errors.push(`Failed to geocode address: ${cleanAddress}`)
        continue
      }
      
      for (const raw of rawsForAddress) {
        try {
          const normalized = await this.normalizeProperty(raw, geocodeResult)
          if (normalized) {
            properties.push(normalized)
          } else {
            validationFailures++
          }
        } catch (error) {
          validationFailures++
          const errorMsg = error instanceof Error ? error.message : String(error)
          errors.push(`Normalization failed for ${raw.address}: ${errorMsg}`)
        }
      }
    }
    
    console.log(`✅ Normalization complete:`)
    console.log(`   Total processed: ${rawProperties.length}`)
    console.log(`   Successfully normalized: ${properties.length}`)
    console.log(`   Geocoding failures: ${geocodingFailures}`)
    console.log(`   Validation failures: ${validationFailures}`)
    
    return {
      properties,
      stats: {
        total_processed: rawProperties.length,
        successfully_normalized: properties.length,
        geocoding_failures: geocodingFailures,
        validation_failures: validationFailures,
        errors
      }
    }
  }
  
  private async normalizeProperty(raw: RawProperty, geocodeResult: any): Promise<CapsightProperty | null> {
    // Generate deterministic ID
    const idInput = `${geocodeResult.formatted_address}|${raw.apn_or_parcel_id || ''}|${raw.source}`
    const id = crypto.createHash('sha256').update(idInput).digest('hex').substring(0, 16)
    
    // Clean and validate required fields
    const cleanAddress = this.cleanAddress(raw.address, raw.city, raw.state)
    if (!this.isValidAddress(cleanAddress)) {
      throw new Error('Invalid address after cleaning')
    }
    
    // Determine market and submarket
    const { market, submarket } = this.determineMarketFromCoordinates(
      geocodeResult.lat,
      geocodeResult.lon,
      raw.city,
      raw.state
    )
    
    // Normalize asset type
    const assetType = this.normalizeAssetType(raw.asset_type, raw.zoning_code)
    
    // Build evidence chain
    const evidence: DataProvenance[] = [
      {
        source: raw.source,
        as_of: raw.as_of,
        from_cache: false
      },
      {
        source: geocodeResult.provider,
        as_of: new Date().toISOString().split('T')[0],
        from_cache: geocodeResult.cached
      }
    ]
    
    const normalized: CapsightProperty = {
      id,
      address: geocodeResult.formatted_address,
      city: raw.city || this.extractCityFromFormattedAddress(geocodeResult.formatted_address),
      state: raw.state || this.extractStateFromFormattedAddress(geocodeResult.formatted_address),
      zip: raw.zip,
      market,
      submarket,
      lat: geocodeResult.lat,
      lon: geocodeResult.lon,
      asset_type: assetType,
      evidence
    }
    
    // Add optional numeric fields if valid
    if (raw.building_sf && raw.building_sf > 0) {
      normalized.building_sf = Math.round(raw.building_sf)
    }
    
    if (raw.land_sf && raw.land_sf > 0) {
      normalized.land_sf = Math.round(raw.land_sf)
    }
    
    if (raw.year_built && raw.year_built > 1800 && raw.year_built <= new Date().getFullYear()) {
      normalized.year_built = raw.year_built
    }
    
    if (raw.assessed_value && raw.assessed_value > 0) {
      normalized.assessed_value = Math.round(raw.assessed_value)
    }
    
    // Add optional string fields if present
    if (raw.owner_name && raw.owner_name.trim().length > 0) {
      normalized.owner_name = this.cleanOwnerName(raw.owner_name)
    }
    
    if (raw.zoning_code && raw.zoning_code.trim().length > 0) {
      normalized.zoning_code = raw.zoning_code.trim().toUpperCase()
    }
    
    // Add rental data if available
    if (raw.asking_rent_psf_yr && raw.asking_rent_psf_yr > 0) {
      normalized.rent_psf_yr = raw.asking_rent_psf_yr
    }
    
    return normalized
  }
  
  private cleanAddress(address: string, city?: string, state?: string): string {
    let cleaned = address.trim()
    
    // Standardize common abbreviations
    const replacements = {
      ' ST ': ' STREET ',
      ' ST$': ' STREET',
      ' AVE ': ' AVENUE ',
      ' AVE$': ' AVENUE',
      ' BLVD ': ' BOULEVARD ',
      ' BLVD$': ' BOULEVARD',
      ' RD ': ' ROAD ',
      ' RD$': ' ROAD',
      ' DR ': ' DRIVE ',
      ' DR$': ' DRIVE',
      ' PKWY ': ' PARKWAY ',
      ' PKWY$': ' PARKWAY'
    }
    
    for (const [pattern, replacement] of Object.entries(replacements)) {
      cleaned = cleaned.replace(new RegExp(pattern, 'gi'), replacement)
    }
    
    // Add city and state if not already present
    if (city && !cleaned.toLowerCase().includes(city.toLowerCase())) {
      cleaned += `, ${city}`
    }
    
    if (state && !cleaned.toLowerCase().includes(state.toLowerCase())) {
      cleaned += `, ${state}`
    }
    
    return cleaned.toUpperCase().trim()
  }
  
  private isValidAddress(address: string): boolean {
    if (!address || address.length < 5) return false
    
    // Must contain at least one number (house number)
    if (!/\d/.test(address)) return false
    
    // Must contain at least one letter (street name)
    if (!/[a-zA-Z]/.test(address)) return false
    
    return true
  }
  
  private normalizeAssetType(rawAssetType?: string, zoningCode?: string): AssetType {
    if (rawAssetType) {
      const normalized = rawAssetType.toLowerCase().trim()
      
      if (normalized.includes('industrial') || normalized.includes('warehouse')) {
        return 'industrial'
      }
      if (normalized.includes('office')) {
        return 'office'
      }
      if (normalized.includes('retail') || normalized.includes('commercial')) {
        return 'retail'
      }
      if (normalized.includes('multifamily') || normalized.includes('apartment')) {
        return 'multifamily'
      }
      if (normalized.includes('land') || normalized.includes('vacant')) {
        return 'land'
      }
    }
    
    // Try to infer from zoning code
    if (zoningCode) {
      const zoning = zoningCode.toUpperCase()
      
      if (zoning.includes('IL') || zoning.includes('IND') || zoning.includes('M')) {
        return 'industrial'
      }
      if (zoning.includes('O') || zoning.includes('OFF')) {
        return 'office'
      }
      if (zoning.includes('C') || zoning.includes('COM') || zoning.includes('RETAIL')) {
        return 'retail'
      }
      if (zoning.includes('R') && (zoning.includes('M') || zoning.includes('4') || zoning.includes('5'))) {
        return 'multifamily'
      }
    }
    
    return 'other'
  }
  
  private determineMarketFromCoordinates(lat: number, lon: number, city?: string, state?: string): { market: string, submarket?: string } {
    // This is a simplified implementation
    // In production, you would query PostGIS for ST_Contains with market polygons
    
    // Major metro mapping based on coordinates
    const metros = [
      { name: 'Dallas–Fort Worth, TX', bounds: { minLat: 32.5, maxLat: 33.2, minLon: -97.5, maxLon: -96.5 } },
      { name: 'Chicago, IL', bounds: { minLat: 41.6, maxLat: 42.1, minLon: -88.0, maxLon: -87.5 } },
      { name: 'Los Angeles, CA', bounds: { minLat: 33.7, maxLat: 34.3, minLon: -118.7, maxLon: -118.1 } },
      { name: 'New York, NY', bounds: { minLat: 40.5, maxLat: 40.9, minLon: -74.3, maxLon: -73.7 } },
      { name: 'Houston, TX', bounds: { minLat: 29.5, maxLat: 30.1, minLon: -95.8, maxLon: -95.0 } },
      { name: 'Phoenix, AZ', bounds: { minLat: 33.2, maxLat: 33.8, minLon: -112.5, maxLon: -111.8 } },
      { name: 'Philadelphia, PA', bounds: { minLat: 39.8, maxLat: 40.2, minLon: -75.4, maxLon: -74.9 } },
      { name: 'San Antonio, TX', bounds: { minLat: 29.2, maxLat: 29.8, minLon: -98.8, maxLon: -98.3 } },
      { name: 'San Diego, CA', bounds: { minLat: 32.5, maxLat: 33.0, minLon: -117.3, maxLon: -116.9 } },
      { name: 'Detroit, MI', bounds: { minLat: 42.1, maxLat: 42.6, minLon: -83.3, maxLon: -82.8 } }
    ]
    
    for (const metro of metros) {
      const b = metro.bounds
      if (lat >= b.minLat && lat <= b.maxLat && lon >= b.minLon && lon <= b.maxLon) {
        return { market: metro.name, submarket: city }
      }
    }
    
    // Fallback to state-level market
    if (state) {
      const stateMarket = `${state} (${city || 'Unknown City'})`
      return { market: stateMarket }
    }
    
    return { market: 'Unknown Market' }
  }
  
  private extractCityFromFormattedAddress(formattedAddress: string): string | undefined {
    // Extract city from formatted address (varies by geocoding provider)
    const parts = formattedAddress.split(',')
    if (parts.length >= 2) {
      return parts[parts.length - 3]?.trim() // Typically "City, State ZIP, Country"
    }
    return undefined
  }
  
  private extractStateFromFormattedAddress(formattedAddress: string): string | undefined {
    // Extract state from formatted address
    const parts = formattedAddress.split(',')
    if (parts.length >= 2) {
      const statePart = parts[parts.length - 2]?.trim()
      if (statePart) {
        // Extract 2-letter state code
        const stateMatch = statePart.match(/\b[A-Z]{2}\b/)
        return stateMatch ? stateMatch[0] : undefined
      }
    }
    return undefined
  }
  
  private cleanOwnerName(ownerName: string): string {
    return ownerName
      .trim()
      .replace(/\s+/g, ' ') // Collapse whitespace
      .replace(/[^\w\s,.-]/g, '') // Remove special characters except common ones
      .toUpperCase()
  }
}

// Export singleton instance
export const propertyNormalizer = new PropertyNormalizer()
