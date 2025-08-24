/**
 * ===== GEOCODING SERVICE WITH CACHING =====
 * Handles address-to-coordinates conversion with caching and fallback providers
 * 
 * Primary: Mapbox Geocoding API (if token available)
 * Fallback: Nominatim (OpenStreetMap)
 */

import crypto from 'crypto'
import { getIngestionConfig } from './ingestion-config'
import type { GeocodeResult, GeocodeCache } from '../lib/ingestion-types.js'

export interface GeocodeService {
  geocode(address: string, force_refresh?: boolean): Promise<GeocodeResult>
  geocodeBatch(addresses: string[], force_refresh?: boolean): Promise<Map<string, GeocodeResult>>
  clearCache(): Promise<void>
  getCacheStats(): Promise<{ entries: number, hit_rate: number }>
}

export class ProductionGeocodeService implements GeocodeService {
  private cache: Map<string, GeocodeCache> = new Map()
  private config = getIngestionConfig()
  private hitCount = 0
  private totalRequests = 0
  
  constructor() {
    // Load cache from disk if available
    this.loadCacheFromDisk()
  }
  
  async geocode(address: string, force_refresh: boolean = false): Promise<GeocodeResult> {
    this.totalRequests++
    
    const addressKey = this.normalizeAddressForCache(address)
    
    // Check cache first (unless force refresh)
    if (!force_refresh) {
      const cached = this.getCachedResult(addressKey)
      if (cached) {
        this.hitCount++
        console.log(`📍 Geocode cache hit: ${address}`)
        return cached
      }
    }
    
    console.log(`🌐 Geocoding: ${address}`)
    
    let result: GeocodeResult
    
    try {
      // Try Mapbox first if token available
      if (this.config.mapbox_token) {
        result = await this.geocodeWithMapbox(address)
      } else {
        result = await this.geocodeWithNominatim(address)
      }
      
      // Cache the result
      this.cacheResult(addressKey, result)
      
      console.log(`✅ Geocoded: ${address} → ${result.lat}, ${result.lon} (${result.provider})`)
      return result
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      console.warn(`⚠️ Primary geocoding failed for "${address}": ${errorMsg}`)
      
      // Try fallback if primary was Mapbox
      if (this.config.mapbox_token) {
        try {
          result = await this.geocodeWithNominatim(address)
          this.cacheResult(addressKey, result)
          console.log(`✅ Geocoded via fallback: ${address} → ${result.lat}, ${result.lon}`)
          return result
        } catch (fallbackError) {
          console.error(`❌ Both geocoding providers failed for "${address}"`)
          const fallbackMsg = fallbackError instanceof Error ? fallbackError.message : String(fallbackError)
          throw new Error(`Geocoding failed: ${fallbackMsg}`)
        }
      } else {
        throw error
      }
    }
  }
  
  async geocodeBatch(addresses: string[], force_refresh: boolean = false): Promise<Map<string, GeocodeResult>> {
    const results = new Map<string, GeocodeResult>()
    const batchSize = 10 // Process in small batches to avoid rate limits
    
    console.log(`📍 Geocoding batch of ${addresses.length} addresses...`)
    
    for (let i = 0; i < addresses.length; i += batchSize) {
      const batch = addresses.slice(i, i + batchSize)
      
      console.log(`📍 Processing batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(addresses.length/batchSize)}`)
      
      const batchPromises = batch.map(async (address) => {
        try {
          const result = await this.geocode(address, force_refresh)
          return { address, result }
        } catch (error) {
          console.error(`❌ Failed to geocode: ${address}`)
          return { address, result: null }
        }
      })
      
      const batchResults = await Promise.all(batchPromises)
      
      for (const { address, result } of batchResults) {
        if (result) {
          results.set(address, result)
        }
      }
      
      // Rate limiting: wait between batches
      if (i + batchSize < addresses.length) {
        await this.sleep(1000) // 1 second between batches
      }
    }
    
    console.log(`✅ Batch geocoding complete: ${results.size}/${addresses.length} successful`)
    return results
  }
  
  private async geocodeWithMapbox(address: string): Promise<GeocodeResult> {
    const encodedAddress = encodeURIComponent(address)
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodedAddress}.json?access_token=${this.config.mapbox_token}&limit=1&types=address`
    
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Mapbox API error: ${response.status}`)
    }
    
    const data = await response.json()
    
    if (!data.features || data.features.length === 0) {
      throw new Error('No results found')
    }
    
    const feature = data.features[0]
    const [lon, lat] = feature.center
    
    // Determine precision based on place type
    const precision = feature.place_type?.includes('address') ? 'exact' : 
                     feature.place_type?.includes('postcode') ? 'approximate' : 'city'
    
    return {
      lat,
      lon,
      formatted_address: feature.place_name,
      precision,
      provider: 'mapbox',
      cached: false
    }
  }
  
  private async geocodeWithNominatim(address: string): Promise<GeocodeResult> {
    // Rate limiting for Nominatim (1 request per second)
    await this.sleep(1100)
    
    const encodedAddress = encodeURIComponent(address)
    const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=1&q=${encodedAddress}`
    
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'CapsightMVP-DataIngestion/1.0'
      }
    })
    
    if (!response.ok) {
      throw new Error(`Nominatim API error: ${response.status}`)
    }
    
    const data = await response.json()
    
    if (!Array.isArray(data) || data.length === 0) {
      throw new Error('No results found')
    }
    
    const result = data[0]
    
    // Determine precision based on class and type
    const precision = result.class === 'place' && result.type === 'house' ? 'exact' :
                     result.class === 'highway' || result.type === 'residential' ? 'approximate' : 'city'
    
    return {
      lat: parseFloat(result.lat),
      lon: parseFloat(result.lon),
      formatted_address: result.display_name,
      precision,
      provider: 'nominatim',
      cached: false
    }
  }
  
  private normalizeAddressForCache(address: string): string {
    // Create a normalized key for caching
    const normalized = address
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ') // Remove punctuation
      .replace(/\s+/g, ' ')      // Collapse whitespace
      .trim()
    
    return crypto.createHash('md5').update(normalized).digest('hex')
  }
  
  private getCachedResult(addressKey: string): GeocodeResult | null {
    const cached = this.cache.get(addressKey)
    if (!cached) return null
    
    // Check if cache entry has expired
    const now = new Date()
    const expiresAt = new Date(cached.expires_at)
    
    if (now > expiresAt) {
      this.cache.delete(addressKey)
      return null
    }
    
    return {
      ...cached.result,
      cached: true
    }
  }
  
  private cacheResult(addressKey: string, result: GeocodeResult): void {
    const now = new Date()
    const expiresAt = new Date(now.getTime() + (this.config.geocode_cache_ttl_days * 24 * 60 * 60 * 1000))
    
    const cacheEntry: GeocodeCache = {
      address_key: addressKey,
      result: { ...result, cached: false },
      cached_at: now.toISOString(),
      expires_at: expiresAt.toISOString()
    }
    
    this.cache.set(addressKey, cacheEntry)
    
    // Persist to disk periodically
    if (this.cache.size % 100 === 0) {
      this.saveCacheToDisk()
    }
  }
  
  private loadCacheFromDisk(): void {
    // In a production system, this would load from a persistent store
    // For now, we'll use in-memory cache only
    console.log('📦 Geocode cache initialized (in-memory only)')
  }
  
  private saveCacheToDisk(): void {
    // In a production system, this would save to a persistent store
    console.log(`💾 Geocode cache: ${this.cache.size} entries`)
  }
  
  async clearCache(): Promise<void> {
    this.cache.clear()
    console.log('🧹 Geocode cache cleared')
  }
  
  async getCacheStats(): Promise<{ entries: number, hit_rate: number }> {
    const hitRate = this.totalRequests > 0 ? this.hitCount / this.totalRequests : 0
    return {
      entries: this.cache.size,
      hit_rate: Math.round(hitRate * 100) / 100
    }
  }
  
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

// Export singleton instance
export const geocodeService = new ProductionGeocodeService()
