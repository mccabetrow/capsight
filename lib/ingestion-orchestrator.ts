/**
 * ===== MAIN INGESTION ORCHESTRATOR =====
 * Coordinates the full pipeline: connectors → normalization → enrichment → scoring → valuation → persistence → webhook emission
 */

import { geocodeService } from './geocode'
import { propertyNormalizer } from './normalize'
import { enrichmentService } from './enrichment'
import { scoringService } from './scoring'
import { supabaseIngestion } from './supabase-ingestion'
import { createWebhookEmissionService } from './webhook-emission'
import { getIngestionConfig } from './ingestion-config'
import { countyDataConnector } from '../connectors/county-data'
import type { 
  CapsightProperty, 
  PropertyFeatures, 
  PropertyScores, 
  ValuationResult,
  RawProperty
} from './ingestion-types'

export interface PipelineRunSummary {
  run_id: string
  started_at: string
  completed_at: string
  duration_ms: number
  total_processed: number
  successful_properties: number
  failed_properties: number
  webhook_events_sent: number
  webhook_events_failed: number
  stages: {
    ingestion: { success: number, errors: string[] }
    normalization: { success: number, errors: string[] }
    enrichment: { success: number, errors: string[] }
    scoring: { success: number, errors: string[] }
    valuation: { success: number, errors: string[] }
    persistence: { success: number, errors: string[] }
    webhooks: { success: number, errors: string[] }
  }
}

export interface PipelineOptions {
  run_id?: string
  max_properties?: number
  enable_webhooks?: boolean
  county_data_source?: string
  skip_stages?: string[]
  dry_run?: boolean
}

export class IngestionOrchestrator {
  private config = getIngestionConfig()
  private webhookService?: ReturnType<typeof createWebhookEmissionService>
  
  async runFullPipeline(options: PipelineOptions = {}): Promise<PipelineRunSummary> {
    const runId = options.run_id || this.generateRunId()
    const startTime = Date.now()
    
    console.log(`🚀 Starting ingestion pipeline run: ${runId}`)
    console.log(`📊 Max properties: ${options.max_properties || 'unlimited'}`)
    console.log(`🔗 Webhooks: ${options.enable_webhooks !== false ? 'enabled' : 'disabled'}`)
    console.log(`🌊 Dry run: ${options.dry_run ? 'YES' : 'NO'}`)
    
    // Initialize webhook service if enabled
    if (options.enable_webhooks !== false) {
      this.webhookService = createWebhookEmissionService(runId)
      await this.webhookService.emitPipelineStarted(options.max_properties)
    }
    
    const summary: PipelineRunSummary = {
      run_id: runId,
      started_at: new Date().toISOString(),
      completed_at: '',
      duration_ms: 0,
      total_processed: 0,
      successful_properties: 0,
      failed_properties: 0,
      webhook_events_sent: 0,
      webhook_events_failed: 0,
      stages: {
        ingestion: { success: 0, errors: [] },
        normalization: { success: 0, errors: [] },
        enrichment: { success: 0, errors: [] },
        scoring: { success: 0, errors: [] },
        valuation: { success: 0, errors: [] },
        persistence: { success: 0, errors: [] },
        webhooks: { success: 0, errors: [] }
      }
    }
    
    try {
      // ===== STAGE 1: DATA INGESTION =====
      const rawProperties = await this.stageIngestion(options, summary)
      
      // ===== STAGE 2: NORMALIZATION =====
      const normalizedProperties = await this.stageNormalization(rawProperties, options, summary)
      
      // ===== STAGE 3: ENRICHMENT =====
      const enrichedFeatures = await this.stageEnrichment(normalizedProperties, options, summary)
      
      // ===== STAGE 4: VALUATION =====
      const valuations = await this.stageValuation(normalizedProperties, enrichedFeatures, options, summary)
      
      // ===== STAGE 5: SCORING =====
      const scores = await this.stageScoring(normalizedProperties, enrichedFeatures, valuations, options, summary)
      
      // ===== STAGE 6: PERSISTENCE =====
      await this.stagePersistence(normalizedProperties, enrichedFeatures, valuations, scores, options, summary)
      
      // ===== STAGE 7: WEBHOOK EMISSION =====
      await this.stageWebhooks(normalizedProperties, scores, valuations, options, summary)
      
      // ===== PIPELINE COMPLETION =====
      const endTime = Date.now()
      summary.completed_at = new Date().toISOString()
      summary.duration_ms = endTime - startTime
      
      console.log(`✅ Pipeline completed successfully: ${summary.successful_properties}/${summary.total_processed} properties`)
      console.log(`⏱️ Total duration: ${Math.round(summary.duration_ms / 1000)}s`)
      
      // Emit pipeline completion event
      if (this.webhookService) {
        await this.webhookService.emitPipelineCompleted(summary)
      }
      
      return summary
      
    } catch (error) {
      console.error(`❌ Pipeline failed:`, error)
      
      if (this.webhookService) {
        await this.webhookService.emitPipelineError(error as Error)
      }
      
      // Update summary with error
      summary.completed_at = new Date().toISOString()
      summary.duration_ms = Date.now() - startTime
      
      throw error
    }
  }
  
  // ===== STAGE 1: DATA INGESTION =====
  
  private async stageIngestion(options: PipelineOptions, summary: PipelineRunSummary): Promise<RawProperty[]> {
    if (options.skip_stages?.includes('ingestion')) {
      console.log(`⏭️ Skipping ingestion stage`)
      return []
    }
    
    console.log(`📊 Stage 1: Data Ingestion`)
    
    try {
      // For MVP, use county data connector
      const result = await countyDataConnector.fetch({ 
        limit: options.max_properties 
      })
      const properties = result.rows
      
      summary.total_processed = properties.length
      summary.stages.ingestion.success = properties.length
      
      console.log(`✅ Ingestion complete: ${properties.length} raw properties`)
      return properties
      
    } catch (error) {
      const errorMsg = `Ingestion failed: ${error instanceof Error ? error.message : String(error)}`
      summary.stages.ingestion.errors.push(errorMsg)
      console.error(`❌ ${errorMsg}`)
      throw error
    }
  }
  
  // ===== STAGE 2: NORMALIZATION =====
  
  private async stageNormalization(
    rawProperties: RawProperty[], 
    options: PipelineOptions, 
    summary: PipelineRunSummary
  ): Promise<CapsightProperty[]> {
    if (options.skip_stages?.includes('normalization')) {
      console.log(`⏭️ Skipping normalization stage`)
      return []
    }
    
    console.log(`🔄 Stage 2: Normalization and Geocoding`)
    
    try {
      const normalizeResult = await propertyNormalizer.normalize(rawProperties)
      const normalized = normalizeResult.properties
      
      summary.stages.normalization.success = normalized.length
      summary.stages.normalization.errors = normalizeResult.stats.errors
      
      console.log(`✅ Normalization complete: ${normalized.length}/${rawProperties.length} properties`)
      return normalized
      
    } catch (error) {
      const errorMsg = `Normalization failed: ${error instanceof Error ? error.message : String(error)}`
      summary.stages.normalization.errors.push(errorMsg)
      console.error(`❌ ${errorMsg}`)
      throw error
    }
  }
  
  // ===== STAGE 3: ENRICHMENT =====
  
  private async stageEnrichment(
    properties: CapsightProperty[], 
    options: PipelineOptions, 
    summary: PipelineRunSummary
  ): Promise<PropertyFeatures[]> {
    if (options.skip_stages?.includes('enrichment')) {
      console.log(`⏭️ Skipping enrichment stage`)
      return []
    }
    
    console.log(`🔬 Stage 3: Property Enrichment`)
    
    try {
      const enriched = await enrichmentService.enrichProperties(properties)
      
      summary.stages.enrichment.success = enriched.length
      summary.stages.enrichment.errors = properties.length - enriched.length > 0 
        ? [`${properties.length - enriched.length} properties failed enrichment`]
        : []
      
      console.log(`✅ Enrichment complete: ${enriched.length}/${properties.length} properties`)
      return enriched
      
    } catch (error) {
      const errorMsg = `Enrichment failed: ${error instanceof Error ? error.message : String(error)}`
      summary.stages.enrichment.errors.push(errorMsg)
      console.error(`❌ ${errorMsg}`)
      throw error
    }
  }
  
  // ===== STAGE 4: VALUATION =====
  
  private async stageValuation(
    properties: CapsightProperty[], 
    features: PropertyFeatures[], 
    options: PipelineOptions, 
    summary: PipelineRunSummary
  ): Promise<ValuationResult[]> {
    if (options.skip_stages?.includes('valuation')) {
      console.log(`⏭️ Skipping valuation stage`)
      return []
    }
    
    console.log(`💰 Stage 4: Property Valuation`)
    
    try {
      // For MVP, create simplified valuations based on NOI and market cap rates
      const valuations: ValuationResult[] = []
      
      for (const property of properties) {
        const propertyFeatures = features.find(f => f.property_id === property.id)
        if (!propertyFeatures?.estimated_noi) continue
        
        const capRate = propertyFeatures.market_fundamentals.avg_cap_rate / 100
        const currentValue = propertyFeatures.estimated_noi.annual_noi / capRate
        
        const valuation: ValuationResult = {
          property_id: property.id,
          current_value: {
            point: Math.round(currentValue),
            low: Math.round(currentValue * 0.9),
            high: Math.round(currentValue * 1.1),
            confidence: 0.75
          },
          income_approach_value: Math.round(currentValue),
          comp_approach_value: property.assessed_value || undefined,
          forecast_value_12m: {
            point: Math.round(currentValue * (1 + propertyFeatures.market_fundamentals.appreciation_forecast_1yr / 100)),
            low: Math.round(currentValue * (1 + (propertyFeatures.market_fundamentals.appreciation_forecast_1yr - 2) / 100)),
            high: Math.round(currentValue * (1 + (propertyFeatures.market_fundamentals.appreciation_forecast_1yr + 2) / 100)),
            confidence: 0.65
          },
          assumptions: {
            rent_psf_yr: propertyFeatures.estimated_noi.noi_psf * 12, // Approximate
            opex_psf_yr: propertyFeatures.estimated_noi.operating_expenses / (property.building_sf || 1),
            vacancy_pct: propertyFeatures.estimated_noi.vacancy_rate_applied,
            cap_rate_pct: capRate * 100,
            noi_annual: propertyFeatures.estimated_noi.annual_noi
          },
          warnings: [],
          created_at: new Date().toISOString()
        }
        
        valuations.push(valuation)
      }
      
      summary.stages.valuation.success = valuations.length
      summary.stages.valuation.errors = properties.length - valuations.length > 0 
        ? [`${properties.length - valuations.length} properties failed valuation`]
        : []
      
      console.log(`✅ Valuation complete: ${valuations.length}/${properties.length} properties`)
      return valuations
      
    } catch (error) {
      const errorMsg = `Valuation failed: ${error instanceof Error ? error.message : String(error)}`
      summary.stages.valuation.errors.push(errorMsg)
      console.error(`❌ ${errorMsg}`)
      throw error
    }
  }
  
  // ===== STAGE 5: SCORING =====
  
  private async stageScoring(
    properties: CapsightProperty[], 
    features: PropertyFeatures[], 
    valuations: ValuationResult[], 
    options: PipelineOptions, 
    summary: PipelineRunSummary
  ): Promise<PropertyScores[]> {
    if (options.skip_stages?.includes('scoring')) {
      console.log(`⏭️ Skipping scoring stage`)
      return []
    }
    
    console.log(`🎯 Stage 5: Property Scoring`)
    
    try {
      const scores = await scoringService.scoreProperties(properties, features, valuations)
      
      summary.stages.scoring.success = scores.length
      summary.stages.scoring.errors = properties.length - scores.length > 0 
        ? [`${properties.length - scores.length} properties failed scoring`]
        : []
      
      console.log(`✅ Scoring complete: ${scores.length}/${properties.length} properties`)
      return scores
      
    } catch (error) {
      const errorMsg = `Scoring failed: ${error instanceof Error ? error.message : String(error)}`
      summary.stages.scoring.errors.push(errorMsg)
      console.error(`❌ ${errorMsg}`)
      throw error
    }
  }
  
  // ===== STAGE 6: PERSISTENCE =====
  
  private async stagePersistence(
    properties: CapsightProperty[], 
    features: PropertyFeatures[], 
    valuations: ValuationResult[], 
    scores: PropertyScores[], 
    options: PipelineOptions, 
    summary: PipelineRunSummary
  ): Promise<void> {
    if (options.skip_stages?.includes('persistence') || options.dry_run) {
      console.log(`⏭️ Skipping persistence stage ${options.dry_run ? '(dry run)' : ''}`)
      return
    }
    
    console.log(`💾 Stage 6: Data Persistence`)
    
    try {
      // Upsert properties, features, valuations, and scores to Supabase
      const [propResult, featResult, valuationResult, scoreResult] = await Promise.all([
        supabaseIngestion.upsertProperties(properties),
        supabaseIngestion.upsertPropertyFeatures(features),
        supabaseIngestion.upsertValuations(valuations),
        supabaseIngestion.upsertPropertyScores(scores)
      ])
      
      const totalSuccess = propResult.success + featResult.success + valuationResult.success + scoreResult.success
      const allErrors = [...propResult.errors, ...featResult.errors, ...valuationResult.errors, ...scoreResult.errors]
      
      summary.stages.persistence.success = totalSuccess
      summary.stages.persistence.errors = allErrors
      summary.successful_properties = Math.min(propResult.success, featResult.success, valuationResult.success, scoreResult.success)
      summary.failed_properties = properties.length - summary.successful_properties
      
      console.log(`✅ Persistence complete: ${totalSuccess} records saved`)
      if (allErrors.length > 0) {
        console.warn(`⚠️ ${allErrors.length} persistence errors occurred`)
      }
      
    } catch (error) {
      const errorMsg = `Persistence failed: ${error instanceof Error ? error.message : String(error)}`
      summary.stages.persistence.errors.push(errorMsg)
      console.error(`❌ ${errorMsg}`)
      throw error
    }
  }
  
  // ===== STAGE 7: WEBHOOK EMISSION =====
  
  private async stageWebhooks(
    properties: CapsightProperty[], 
    scores: PropertyScores[], 
    valuations: ValuationResult[], 
    options: PipelineOptions, 
    summary: PipelineRunSummary
  ): Promise<void> {
    if (options.skip_stages?.includes('webhooks') || options.enable_webhooks === false || !this.webhookService) {
      console.log(`⏭️ Skipping webhook stage`)
      return
    }
    
    console.log(`🔗 Stage 7: Webhook Emission`)
    
    try {
      const { sent, failed } = await this.webhookService.emitBulkEvents(properties, scores, valuations)
      
      summary.webhook_events_sent = sent
      summary.webhook_events_failed = failed
      summary.stages.webhooks.success = sent
      if (failed > 0) {
        summary.stages.webhooks.errors.push(`${failed} webhook events failed`)
      }
      
      // Emit high-value opportunities
      for (const property of properties) {
        const propertyScores = scores.find(s => s.property_id === property.id)
        const valuation = valuations.find(v => v.property_id === property.id)
        
        if (propertyScores && valuation && propertyScores.deal_score > 75) {
          await this.webhookService.emitHighValueOpportunity(property, propertyScores, valuation)
        }
      }
      
      console.log(`✅ Webhook emission complete: ${sent} events sent, ${failed} failed`)
      
    } catch (error) {
      const errorMsg = `Webhook emission failed: ${error instanceof Error ? error.message : String(error)}`
      summary.stages.webhooks.errors.push(errorMsg)
      console.error(`❌ ${errorMsg}`)
      // Don't throw - webhook failures shouldn't fail the pipeline
    }
  }
  
  // ===== UTILITY METHODS =====
  
  private generateRunId(): string {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const random = Math.random().toString(36).substr(2, 8)
    return `pipeline-${timestamp}-${random}`
  }
  
  // ===== HEALTH CHECK =====
  
  async healthCheck(): Promise<any> {
    console.log(`🏥 Running pipeline health check...`)
    
    const health = {
      timestamp: new Date().toISOString(),
      geocoding: await geocodeService.getCacheStats(),
      supabase: await supabaseIngestion.getIngestionHealthStats(),
      webhook: this.webhookService ? await this.webhookService.healthCheck() : { healthy: false, reason: 'not_initialized' },
      config: {
        node_version: process.version,
        environment: process.env.NODE_ENV || 'development'
      }
    }
    
    const overallHealthy = health.geocoding.hit_rate >= 0 && 
                          health.supabase.properties_total >= 0 &&
                          (health.webhook.healthy || ('reason' in health.webhook && health.webhook.reason === 'not_initialized'))
    
    console.log(`🏥 Health check ${overallHealthy ? 'PASSED' : 'FAILED'}`)
    return { ...health, healthy: overallHealthy }
  }
}

// Export singleton instance
export const ingestionOrchestrator = new IngestionOrchestrator()
