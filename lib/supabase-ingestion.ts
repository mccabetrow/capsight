/**
 * ===== SUPABASE INTEGRATION FOR INGESTION PIPELINE =====
 * Handles upserts and queries for property data, valuations, and scores
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { getIngestionConfig } from './ingestion-config'
import type { 
  CapsightProperty, 
  PropertyFeatures, 
  ValuationResult, 
  PropertyScores,
  MarketFundamentals,
  DemographicData
} from './ingestion-types'

export class SupabaseIngestionClient {
  private supabase: SupabaseClient
  private config = getIngestionConfig()
  
  constructor() {
    this.supabase = createClient(
      this.config.supabase_url,
      this.config.supabase_service_role_key,
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    )
  }
  
  // ===== PROPERTY OPERATIONS =====
  
  async upsertProperties(properties: CapsightProperty[]): Promise<{ success: number, errors: string[] }> {
    console.log(`💾 Upserting ${properties.length} properties to Supabase...`)
    
    let successCount = 0
    const errors: string[] = []
    const batchSize = 100 // Process in batches
    
    for (let i = 0; i < properties.length; i += batchSize) {
      const batch = properties.slice(i, i + batchSize)
      
      try {
        const { error } = await this.supabase
          .from('properties')
          .upsert(batch.map(this.mapPropertyForDatabase), { 
            onConflict: 'id',
            ignoreDuplicates: false 
          })
        
        if (error) {
          console.error(`❌ Batch ${Math.floor(i/batchSize) + 1} failed:`, error)
          errors.push(`Batch ${Math.floor(i/batchSize) + 1}: ${error instanceof Error ? error.message : String(error)}`)
        } else {
          successCount += batch.length
          console.log(`✅ Batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(properties.length/batchSize)} complete`)
        }
        
      } catch (error) {
        console.error(`❌ Batch ${Math.floor(i/batchSize) + 1} exception:`, error)
        const errorMsg = error instanceof Error ? error instanceof Error ? error.message : String(error) : String(error)
        errors.push(`Batch ${Math.floor(i/batchSize) + 1}: ${errorMsg}`)
      }
    }
    
    console.log(`💾 Property upsert complete: ${successCount}/${properties.length} successful`)
    return { success: successCount, errors }
  }
  
  async upsertPropertyFeatures(features: PropertyFeatures[]): Promise<{ success: number, errors: string[] }> {
    console.log(`💾 Upserting ${features.length} property feature sets...`)
    
    let successCount = 0
    const errors: string[] = []
    
    for (const feature of features) {
      try {
        const { error } = await this.supabase
          .from('features_properties')
          .upsert({
            property_id: feature.property_id,
            market_fundamentals: feature.market_fundamentals,
            demographics: feature.demographics || null,
            flood_zone: feature.flood_zone || null,
            broadband_served: feature.broadband_served || null,
            estimated_noi: feature.estimated_noi || null,
            provenance: feature.provenance,
            updated_at: new Date().toISOString()
          }, { onConflict: 'property_id' })
        
        if (error) {
          errors.push(`Property ${feature.property_id}: ${error instanceof Error ? error.message : String(error)}`)
        } else {
          successCount++
        }
        
      } catch (error) {
        errors.push(`Property ${feature.property_id}: ${error instanceof Error ? error.message : String(error)}`)
      }
    }
    
    console.log(`💾 Features upsert complete: ${successCount}/${features.length} successful`)
    return { success: successCount, errors }
  }
  
  async upsertValuations(valuations: ValuationResult[]): Promise<{ success: number, errors: string[] }> {
    console.log(`💾 Upserting ${valuations.length} valuations...`)
    
    let successCount = 0
    const errors: string[] = []
    
    for (const valuation of valuations) {
      try {
        const { error } = await this.supabase
          .from('valuations')
          .insert({
            property_id: valuation.property_id,
            current_value: valuation.current_value.point,
            low_value: valuation.current_value.low,
            high_value: valuation.current_value.high,
            confidence: valuation.current_value.confidence,
            forecast_value_12m: valuation.forecast_value_12m?.point || null,
            forecast_low_12m: valuation.forecast_value_12m?.low || null,
            forecast_high_12m: valuation.forecast_value_12m?.high || null,
            forecast_confidence_12m: valuation.forecast_value_12m?.confidence || null,
            income_approach_value: valuation.income_approach_value,
            comp_approach_value: valuation.comp_approach_value || null,
            assumptions: valuation.assumptions,
            warnings: valuation.warnings,
            created_at: valuation.created_at
          })
        
        if (error) {
          errors.push(`Property ${valuation.property_id}: ${error instanceof Error ? error.message : String(error)}`)
        } else {
          successCount++
        }
        
      } catch (error) {
        errors.push(`Property ${valuation.property_id}: ${error instanceof Error ? error.message : String(error)}`)
      }
    }
    
    console.log(`💾 Valuations upsert complete: ${successCount}/${valuations.length} successful`)
    return { success: successCount, errors }
  }
  
  async upsertPropertyScores(scores: PropertyScores[]): Promise<{ success: number, errors: string[] }> {
    console.log(`💾 Upserting ${scores.length} property scores...`)
    
    let successCount = 0
    const errors: string[] = []
    
    for (const score of scores) {
      try {
        const { error } = await this.supabase
          .from('scores')
          .insert({
            property_id: score.property_id,
            mts_score: score.mts_score,
            deal_score: score.deal_score,
            yield_signal: score.yield_signal,
            macro_spread: score.macro_spread || null,
            classification: score.classification,
            confidence: score.confidence,
            scoring_model_version: score.scoring_model_version,
            created_at: score.created_at
          })
        
        if (error) {
          errors.push(`Property ${score.property_id}: ${error instanceof Error ? error.message : String(error)}`)
        } else {
          successCount++
        }
        
      } catch (error) {
        errors.push(`Property ${score.property_id}: ${error instanceof Error ? error.message : String(error)}`)
      }
    }
    
    console.log(`💾 Scores upsert complete: ${successCount}/${scores.length} successful`)
    return { success: successCount, errors }
  }
  
  // ===== MARKET DATA RETRIEVAL =====
  
  async getMarketFundamentals(market: string): Promise<MarketFundamentals | null> {
    console.log(`📊 Fetching market fundamentals for: ${market}`)
    
    const freshnessThreshold = new Date()
    freshnessThreshold.setDate(freshnessThreshold.getDate() - this.config.market_fundamentals_freshness_days)
    
    const { data, error } = await this.supabase
      .from('market_fundamentals')
      .select('*')
      .eq('market', market)
      .gte('as_of', freshnessThreshold.toISOString().split('T')[0])
      .order('as_of', { ascending: false })
      .limit(1)
      .single()
    
    if (error) {
      console.warn(`⚠️ Failed to fetch market fundamentals for ${market}: ${error instanceof Error ? error.message : String(error)}`)
      return null
    }
    
    console.log(`✅ Found fresh market data for ${market} (as of ${data.as_of})`)
    return data as MarketFundamentals
  }
  
  async getDemographicsForLocation(locationId: string, locationType: 'tract' | 'zip' | 'county'): Promise<DemographicData | null> {
    console.log(`📊 Fetching demographics for ${locationType}: ${locationId}`)
    
    const freshnessThreshold = new Date()
    freshnessThreshold.setHours(freshnessThreshold.getHours() - this.config.demographics_cache_ttl_hours)
    
    const { data, error } = await this.supabase
      .from('demographics')
      .select('*')
      .eq('location_id', locationId)
      .eq('location_type', locationType)
      .gte('updated_at', freshnessThreshold.toISOString())
      .order('updated_at', { ascending: false })
      .limit(1)
      .single()
    
    if (error) {
      console.warn(`⚠️ No fresh demographics found for ${locationId}: ${error instanceof Error ? error.message : String(error)}`)
      return null
    }
    
    console.log(`✅ Found fresh demographics for ${locationId}`)
    return data as DemographicData
  }
  
  // ===== BATCH OPERATIONS =====
  
  async getPropertiesForScoring(limit: number = 1000): Promise<CapsightProperty[]> {
    console.log(`📊 Fetching properties for scoring (limit: ${limit})...`)
    
    const { data, error } = await this.supabase
      .from('properties')
      .select('*')
      .is('last_scored_at', null) // Properties that haven't been scored yet
      .or('last_scored_at.lt.' + new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()) // Or scored > 7 days ago
      .limit(limit)
    
    if (error) {
      console.error(`❌ Failed to fetch properties for scoring: ${error instanceof Error ? error.message : String(error)}`)
      return []
    }
    
    console.log(`✅ Retrieved ${data?.length || 0} properties for scoring`)
    return (data || []).map(this.mapDatabaseToProperty)
  }
  
  async markPropertiesAsScored(propertyIds: string[]): Promise<void> {
    const { error } = await this.supabase
      .from('properties')
      .update({ last_scored_at: new Date().toISOString() })
      .in('id', propertyIds)
    
    if (error) {
      console.error(`❌ Failed to mark properties as scored: ${error instanceof Error ? error.message : String(error)}`)
    } else {
      console.log(`✅ Marked ${propertyIds.length} properties as scored`)
    }
  }
  
  // ===== HEALTH CHECKS =====
  
  async getIngestionHealthStats(): Promise<any> {
    const [propertiesCount, valuationsCount, scoresCount, featuresCount] = await Promise.all([
      this.supabase.from('properties').select('*', { count: 'exact', head: true }),
      this.supabase.from('valuations').select('*', { count: 'exact', head: true }),
      this.supabase.from('scores').select('*', { count: 'exact', head: true }),
      this.supabase.from('features_properties').select('*', { count: 'exact', head: true })
    ])
    
    return {
      properties_total: propertiesCount.count || 0,
      valuations_total: valuationsCount.count || 0,
      scores_total: scoresCount.count || 0,
      features_total: featuresCount.count || 0,
      last_updated: new Date().toISOString()
    }
  }
  
  // ===== PRIVATE MAPPING HELPERS =====
  
  private mapPropertyForDatabase(property: CapsightProperty): any {
    return {
      id: property.id,
      address: property.address,
      city: property.city,
      state: property.state,
      zip: property.zip,
      market: property.market,
      submarket: property.submarket,
      lat: property.lat,
      lon: property.lon,
      building_sf: property.building_sf,
      land_sf: property.land_sf,
      year_built: property.year_built,
      assessed_value: property.assessed_value,
      owner_name: property.owner_name,
      zoning_code: property.zoning_code,
      asset_type: property.asset_type,
      rent_psf_yr: property.rent_psf_yr,
      opex_psf_yr: property.opex_psf_yr,
      vacancy_pct: property.vacancy_pct,
      evidence: property.evidence,
      updated_at: new Date().toISOString()
    }
  }
  
  private mapDatabaseToProperty(data: any): CapsightProperty {
    return {
      id: data.id,
      address: data.address,
      city: data.city,
      state: data.state,
      zip: data.zip,
      market: data.market,
      submarket: data.submarket,
      lat: data.lat,
      lon: data.lon,
      building_sf: data.building_sf,
      land_sf: data.land_sf,
      year_built: data.year_built,
      assessed_value: data.assessed_value,
      owner_name: data.owner_name,
      zoning_code: data.zoning_code,
      asset_type: data.asset_type,
      rent_psf_yr: data.rent_psf_yr,
      opex_psf_yr: data.opex_psf_yr,
      vacancy_pct: data.vacancy_pct,
      evidence: data.evidence || []
    }
  }
}

// Export singleton instance
export const supabaseIngestion = new SupabaseIngestionClient()
