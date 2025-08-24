/**
 * ===== CAPSIGHT INGESTION PIPELINE TYPE DEFINITIONS =====
 * Strict TypeScript types for the data ingestion and enrichment pipeline
 */

// ===== SOURCE DATA TYPES =====

export type AssetType = 'industrial' | 'office' | 'retail' | 'multifamily' | 'land' | 'other'

export interface DataProvenance {
  source: string
  as_of: string
  from_cache?: boolean
}

export interface RawProperty {
  // Identifiers
  external_id?: string
  apn_or_parcel_id?: string
  address: string
  city?: string
  state?: string
  zip?: string
  
  // Physical characteristics
  building_sf?: number
  land_sf?: number
  year_built?: number
  
  // Financial data
  assessed_value?: number
  asking_rent_psf_yr?: number
  asking_price?: number
  
  // Ownership and zoning
  owner_name?: string
  zoning_code?: string
  
  // Classification
  asset_type?: AssetType
  
  // Provenance
  source: string
  as_of: string
}

// ===== NORMALIZED DATA TYPES =====

export interface CapsightProperty {
  // Primary key (deterministic hash)
  id: string
  
  // Address and location
  address: string
  city?: string
  state?: string
  zip?: string
  market: string
  submarket?: string
  lat: number
  lon: number
  
  // Physical characteristics
  building_sf?: number
  land_sf?: number
  year_built?: number
  
  // Financial data
  assessed_value?: number
  owner_name?: string
  zoning_code?: string
  
  // Classification
  asset_type: AssetType
  
  // Operating assumptions (may be inferred)
  rent_psf_yr?: number
  opex_psf_yr?: number
  vacancy_pct?: number
  
  // Data provenance
  evidence: DataProvenance[]
}

// ===== MARKET ENRICHMENT TYPES =====

export interface MarketFundamentals {
  market: string
  avg_cap_rate: number
  avg_rent_psf: number
  vacancy_rate: number
  appreciation_forecast_1yr: number
  supply_pipeline_sf: number | null
  absorption_rate_sf_mo: number | null
  unemployment_rate: number | null
  population_growth_rate: number | null
  as_of: string
  data_sources: string[]
}

export interface DemographicData {
  location_id: string // tract/zip/county
  location_type: 'tract' | 'zip' | 'county'
  population: number
  population_trend_1yr: number
  median_income: number
  employment_yoy: number
  data_source: string
  as_of: string
  updated_at: string
}

export interface FloodRisk {
  fema_zone: string
  flood_risk_level: 'low' | 'moderate' | 'high'
  base_flood_elevation_ft: number | null
  annual_chance_pct: number
  data_source: string
  as_of: string
}

export interface BroadbandCoverage {
  fiber_available: boolean
  max_download_mbps: number
  max_upload_mbps: number
  provider_count: number
  data_source: string
  as_of: string
}

export interface EstimatedNOI {
  annual_noi: number
  noi_psf: number
  gross_income: number
  effective_income: number
  operating_expenses: number
  vacancy_rate_applied: number
  assumptions: {
    rent_psf_source: string
    opex_psf_source: string
    vacancy_source: string
  }
}

export interface PropertyFeatures {
  property_id: string
  
  // Market context
  market_fundamentals: MarketFundamentals
  demographics?: DemographicData
  
  // Risk factors
  flood_zone?: FloodRisk
  broadband_served?: BroadbandCoverage
  
  // Computed financials
  estimated_noi?: EstimatedNOI
  
  // Data provenance
  provenance: string[]
}

// ===== VALUATION AND SCORING TYPES =====

export interface ValuationResult {
  property_id: string
  
  // Current valuation
  current_value: {
    point: number
    low: number
    high: number
    confidence: number
  }
  
  // Valuation methods
  income_approach_value: number
  comp_approach_value?: number
  
  // Forward-looking
  forecast_value_12m?: {
    point: number
    low: number
    high: number
    confidence: number
  }
  
  // Assumptions and inputs
  assumptions: {
    rent_psf_yr: number
    opex_psf_yr: number
    vacancy_pct: number
    cap_rate_pct: number
    noi_annual: number
  }
  
  // Quality flags
  warnings: string[]
  
  created_at: string
}

export interface PropertyScores {
  property_id: string
  
  // Core scores (0-100)
  mts_score: number        // Market Timing Score
  deal_score: number       // Overall Deal Score
  
  // Component scores
  yield_signal: number     // Z-score of yield vs market
  macro_spread?: number    // Cap rate spread over risk-free rate
  
  // Classification
  classification: string   // 'A', 'B+', 'B', 'B-', 'C', 'D'
  
  // Metadata
  confidence: number
  scoring_model_version: string
  created_at: string
}

// ===== WEBHOOK EVENT TYPES =====

export interface WebhookValuationEvent {
  schema_version: string
  type: 'valuation.upsert'
  tenant_id: string
  as_of: string
  
  model: {
    name: string
    version: string
  }
  
  provenance: {
    fundamentals?: DataProvenance
    listings?: DataProvenance
    geo?: DataProvenance
    demographics?: DataProvenance
  }
  
  address: string
  
  geo: {
    lat: number
    lon: number
    market: string
    submarket?: string
  }
  
  property_snapshot: {
    building_sf?: number
    year_built?: number
    zoning_code?: string
    asset_type: AssetType
  }
  
  inputs: {
    asset_type: AssetType
    rent_psf_yr: number
    opex_psf_yr: number
    vacancy_pct: number
    cap_rate_now_pct: number
  }
  
  current_value: {
    point: number
    low: number
    high: number
    confidence: number
  }
  
  scores: {
    mts: number
    deal_score: number
    classification: 'BUY' | 'HOLD' | 'AVOID'
  }
  
  warnings?: string[]
}

// ===== CONNECTOR INTERFACE =====

export interface ConnectorResult<T> {
  rows: T[]
  provenance: DataProvenance
  stats: {
    total_fetched: number
    total_valid: number
    total_skipped: number
    errors: string[]
  }
}

export interface ConnectorOptions {
  limit?: number
  offset?: number
  cache_ttl_hours?: number
  force_refresh?: boolean
}

// ===== PIPELINE SUMMARY TYPES =====

export interface IngestionSummary {
  run_id: string
  started_at: string
  completed_at: string
  
  // Input stats
  sources_processed: string[]
  raw_properties_fetched: number
  
  // Processing stats
  properties_normalized: number
  properties_geocoded: number
  properties_enriched: number
  properties_scored: number
  
  // Output stats
  properties_upserted: number
  valuations_created: number
  webhooks_sent: number
  webhook_failures: number
  
  // Classification distribution
  classifications: {
    BUY: number
    HOLD: number
    AVOID: number
  }
  
  // Quality metrics
  avg_confidence: number
  properties_with_warnings: number
  
  // Errors and warnings
  errors: string[]
  warnings: string[]
}

// ===== GEOCODING TYPES =====

export interface GeocodeResult {
  lat: number
  lon: number
  formatted_address: string
  precision: 'exact' | 'approximate' | 'city'
  provider: 'mapbox' | 'nominatim'
  cached: boolean
}

export interface GeocodeCache {
  address_key: string
  result: GeocodeResult
  cached_at: string
  expires_at: string
}
