/**
 * ===== PROPERTY ENRICHMENT SERVICE =====
 * Enriches normalized properties with market data, demographics, and computed features
 */

import { supabaseIngestion } from './supabase-ingestion'
import { getIngestionConfig } from './ingestion-config'
import type { 
  CapsightProperty, 
  PropertyFeatures, 
  MarketFundamentals, 
  DemographicData,
  FloodRisk,
  BroadbandCoverage,
  EstimatedNOI,
  DataProvenance
} from './ingestion-types'

export class PropertyEnrichmentService {
  private config = getIngestionConfig()
  
  async enrichProperties(properties: CapsightProperty[]): Promise<PropertyFeatures[]> {
    console.log(`🔬 Enriching ${properties.length} properties with market data and demographics...`)
    
    const enrichedFeatures: PropertyFeatures[] = []
    
    // Process in batches to avoid API limits
    const batchSize = 50
    for (let i = 0; i < properties.length; i += batchSize) {
      const batch = properties.slice(i, i + batchSize)
      console.log(`🔬 Processing enrichment batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(properties.length/batchSize)}...`)
      
      const batchFeatures = await Promise.all(
        batch.map(property => this.enrichProperty(property))
      )
      
      enrichedFeatures.push(...batchFeatures.filter((f): f is PropertyFeatures => f !== null))
      
      // Rate limiting: 100ms between batches
      if (i + batchSize < properties.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
    
    console.log(`🔬 Enrichment complete: ${enrichedFeatures.length}/${properties.length} properties enriched`)
    return enrichedFeatures
  }
  
  private async enrichProperty(property: CapsightProperty): Promise<PropertyFeatures | null> {
    try {
      const [marketFundamentals, demographics, floodRisk, broadbandCoverage] = await Promise.all([
        this.getMarketFundamentals(property.market),
        this.getDemographics(property),
        this.assessFloodRisk(property),
        this.getBroadbandCoverage(property)
      ])
      
      const estimatedNOI = this.calculateNOI(property, marketFundamentals)
      
      const features: PropertyFeatures = {
        property_id: property.id,
        market_fundamentals: marketFundamentals,
        demographics: demographics || undefined,
        flood_zone: floodRisk || undefined,
        broadband_served: broadbandCoverage || undefined,
        estimated_noi: estimatedNOI || undefined,
        provenance: this.buildProvenanceChain(property, marketFundamentals, demographics, floodRisk, broadbandCoverage)
      }
      
      return features
      
    } catch (error) {
      console.error(`❌ Failed to enrich property ${property.id}:`, error)
      return null
    }
  }
  
  // ===== MARKET FUNDAMENTALS =====
  
  private async getMarketFundamentals(market: string): Promise<MarketFundamentals> {
    // Check cache first
    const cached = await supabaseIngestion.getMarketFundamentals(market)
    if (cached) {
      return cached
    }
    
    console.log(`🏙️ Fetching fresh market fundamentals for: ${market}`)
    
    // For MVP, return computed fundamentals based on property data
    // In production, this would integrate with real market data APIs
    const fundamentals: MarketFundamentals = {
      market,
      avg_cap_rate: this.getMarketCapRate(market),
      avg_rent_psf: this.getMarketRent(market),
      vacancy_rate: this.getMarketVacancy(market),
      appreciation_forecast_1yr: this.getAppreciationForecast(market),
      supply_pipeline_sf: null, // Would integrate with real data
      absorption_rate_sf_mo: null, // Would integrate with real data
      unemployment_rate: null, // Would fetch from BLS API
      population_growth_rate: null, // Would fetch from Census API
      as_of: new Date().toISOString().split('T')[0],
      data_sources: ['CapSight Analysis', 'Property Assessments']
    }
    
    return fundamentals
  }
  
  // ===== DEMOGRAPHICS =====
  
  private async getDemographics(property: CapsightProperty): Promise<DemographicData | null> {
    // Try to get demographics by ZIP code first
    if (!property.zip) return null
    
    let demographics = await supabaseIngestion.getDemographicsForLocation(property.zip, 'zip')
    if (demographics) return demographics
    
    // Fall back to county-level demographics
    const countyFips = this.extractCountyFromEvidence(property.evidence)
    if (countyFips) {
      demographics = await supabaseIngestion.getDemographicsForLocation(countyFips, 'county')
      if (demographics) return demographics
    }
    
    console.log(`📊 No demographics found for ${property.address}`)
    return null
  }
  
  // ===== FLOOD RISK ASSESSMENT =====
  
  private async assessFloodRisk(property: CapsightProperty): Promise<FloodRisk | null> {
    // For MVP, assess based on elevation and proximity to water bodies
    // In production, would integrate with FEMA Flood Map Service API
    
    if (!property.lat || !property.lon) return null
    
    try {
      // Simulate flood zone lookup
      const zone = this.simulateFloodZone(property.lat, property.lon)
      
      const floodRisk: FloodRisk = {
        fema_zone: zone,
        flood_risk_level: this.mapZoneToRiskLevel(zone),
        base_flood_elevation_ft: zone.startsWith('A') ? 10.5 : null,
        annual_chance_pct: this.mapZoneToAnnualChance(zone),
        data_source: 'FEMA NFHL (Simulated)',
        as_of: new Date().toISOString().split('T')[0]
      }
      
      return floodRisk
      
    } catch (error) {
      console.error(`❌ Flood risk assessment failed for ${property.id}:`, error)
      return null
    }
  }
  
  // ===== BROADBAND COVERAGE =====
  
  private async getBroadbandCoverage(property: CapsightProperty): Promise<BroadbandCoverage | null> {
    // For MVP, estimate based on urban/rural classification
    // In production, would integrate with FCC Broadband Data API
    
    if (!property.lat || !property.lon) return null
    
    try {
      const isUrban = await this.classifyUrbanRural(property)
      
      const broadband: BroadbandCoverage = {
        fiber_available: isUrban ? Math.random() > 0.3 : Math.random() > 0.7,
        max_download_mbps: isUrban ? 100 + Math.random() * 900 : 25 + Math.random() * 75,
        max_upload_mbps: isUrban ? 50 + Math.random() * 450 : 10 + Math.random() * 40,
        provider_count: isUrban ? 3 + Math.floor(Math.random() * 5) : 1 + Math.floor(Math.random() * 3),
        data_source: 'FCC Form 477 (Simulated)',
        as_of: new Date().toISOString().split('T')[0]
      }
      
      return broadband
      
    } catch (error) {
      console.error(`❌ Broadband assessment failed for ${property.id}:`, error)
      return null
    }
  }
  
  // ===== NOI CALCULATION =====
  
  private calculateNOI(property: CapsightProperty, marketFundamentals: MarketFundamentals): EstimatedNOI | null {
    if (!property.building_sf || !property.rent_psf_yr) return null
    
    try {
      // Base rent calculation
      const effectiveRent = property.rent_psf_yr || marketFundamentals.avg_rent_psf
      const potentialGrossIncome = property.building_sf * effectiveRent
      
      // Apply vacancy
      const vacancyRate = property.vacancy_pct ? property.vacancy_pct / 100 : marketFundamentals.vacancy_rate / 100
      const effectiveGrossIncome = potentialGrossIncome * (1 - vacancyRate)
      
      // Operating expenses
      const opexPSF = property.opex_psf_yr || effectiveRent * 0.35 // Default to 35% of rent
      const totalOpex = property.building_sf * opexPSF
      
      const netOperatingIncome = effectiveGrossIncome - totalOpex
      
      const estimatedNOI: EstimatedNOI = {
        annual_noi: Math.round(netOperatingIncome),
        noi_psf: Math.round(netOperatingIncome / property.building_sf * 100) / 100,
        gross_income: Math.round(potentialGrossIncome),
        effective_income: Math.round(effectiveGrossIncome),
        operating_expenses: Math.round(totalOpex),
        vacancy_rate_applied: Math.round(vacancyRate * 10000) / 100, // Convert to percentage
        assumptions: {
          rent_psf_source: property.rent_psf_yr ? 'Property Record' : 'Market Average',
          opex_psf_source: property.opex_psf_yr ? 'Property Record' : 'Market Estimate (35% of rent)',
          vacancy_source: property.vacancy_pct ? 'Property Record' : 'Market Average'
        }
      }
      
      return estimatedNOI
      
    } catch (error) {
      console.error(`❌ NOI calculation failed for ${property.id}:`, error)
      return null
    }
  }
  
  // ===== HELPER METHODS =====
  
  private getMarketCapRate(market: string): number {
    // Market-specific cap rates (MVP simulation)
    const capRates: Record<string, number> = {
      'San Francisco': 4.2,
      'New York': 4.8,
      'Los Angeles': 4.5,
      'Chicago': 6.1,
      'Dallas': 6.8,
      'Atlanta': 7.2,
      'Denver': 5.9,
      'Seattle': 4.7,
      'Miami': 6.5,
      'Boston': 5.1
    }
    
    return capRates[market] || 6.5 // Default cap rate
  }
  
  private getMarketRent(market: string): number {
    // Market-specific rents (MVP simulation)
    const rents: Record<string, number> = {
      'San Francisco': 65.0,
      'New York': 55.0,
      'Los Angeles': 45.0,
      'Chicago': 32.0,
      'Dallas': 28.0,
      'Atlanta': 25.0,
      'Denver': 30.0,
      'Seattle': 40.0,
      'Miami': 35.0,
      'Boston': 42.0
    }
    
    return rents[market] || 30.0 // Default rent PSF
  }
  
  private getMarketVacancy(market: string): number {
    // Market-specific vacancy rates (MVP simulation)
    const vacancies: Record<string, number> = {
      'San Francisco': 8.5,
      'New York': 12.0,
      'Los Angeles': 10.5,
      'Chicago': 15.2,
      'Dallas': 11.8,
      'Atlanta': 13.5,
      'Denver': 9.2,
      'Seattle': 7.8,
      'Miami': 14.0,
      'Boston': 8.9
    }
    
    return vacancies[market] || 12.0 // Default vacancy rate
  }
  
  private getAppreciationForecast(market: string): number {
    // 1-year appreciation forecasts (MVP simulation)
    const forecasts: Record<string, number> = {
      'San Francisco': 2.1,
      'New York': 1.8,
      'Los Angeles': 3.2,
      'Chicago': 2.8,
      'Dallas': 4.1,
      'Atlanta': 3.9,
      'Denver': 3.5,
      'Seattle': 2.7,
      'Miami': 4.2,
      'Boston': 2.4
    }
    
    return forecasts[market] || 3.0 // Default appreciation
  }
  
  private simulateFloodZone(lat: number, lon: number): string {
    // Simulate flood zone based on location (MVP)
    const zones = ['X', 'AE', 'A', 'VE', 'X-Shaded']
    const hash = Math.abs(lat * 1000 + lon * 1000) % zones.length
    return zones[hash]
  }
  
  private mapZoneToRiskLevel(zone: string): 'low' | 'moderate' | 'high' {
    if (zone === 'X') return 'low'
    if (zone.includes('Shaded') || zone === 'B' || zone === 'C') return 'moderate'
    return 'high' // A, AE, VE zones
  }
  
  private mapZoneToAnnualChance(zone: string): number {
    if (zone === 'X') return 0.2
    if (zone.includes('Shaded')) return 0.5
    if (zone.startsWith('A')) return 1.0
    if (zone.startsWith('V')) return 1.0
    return 0.2
  }
  
  private async classifyUrbanRural(property: CapsightProperty): Promise<boolean> {
    // Simple urban/rural classification based on population density
    const urbanCities = ['San Francisco', 'New York', 'Los Angeles', 'Chicago', 'Boston', 'Seattle', 'Miami']
    return property.city ? urbanCities.some(city => property.city!.toLowerCase().includes(city.toLowerCase())) : false
  }
  
  private extractCountyFromEvidence(evidence: DataProvenance[]): string | null {
    // Extract county FIPS from evidence chain
    const countyEvidence = evidence.find(e => e.source.includes('county_fips:'))
    return countyEvidence ? countyEvidence.source.split('county_fips:')[1].split(',')[0].trim() : null
  }
  
  private buildProvenanceChain(
    property: CapsightProperty, 
    market: MarketFundamentals, 
    demographics: DemographicData | null,
    flood: FloodRisk | null,
    broadband: BroadbandCoverage | null
  ): string[] {
    const provenance = [
      `enrichment_timestamp:${new Date().toISOString()}`,
      `market_data_source:${market.data_sources.join(',')}`,
      `market_data_as_of:${market.as_of}`
    ]
    
    if (demographics) {
      provenance.push(`demographics_source:${demographics.data_source}`)
    }
    
    if (flood) {
      provenance.push(`flood_data_source:${flood.data_source}`)
    }
    
    if (broadband) {
      provenance.push(`broadband_data_source:${broadband.data_source}`)
    }
    
    return provenance
  }
}

// Export singleton instance
export const enrichmentService = new PropertyEnrichmentService()
