/**
 * ===== WEBHOOK EMISSION SERVICE FOR INGESTION PIPELINE =====
 * Emits property events to n8n webhook with HMAC security and retry logic
 */

import { ProductionWebhookClient } from './webhook-client'
import { getIngestionConfig } from './ingestion-config'
import type { 
  CapsightProperty, 
  PropertyScores, 
  ValuationResult,
  PropertyFeatures 
} from './ingestion-types'

export interface PropertyEvent {
  event_type: 'property_ingested' | 'property_scored' | 'property_valued' | 'batch_complete'
  event_id: string
  timestamp: string
  data: {
    property?: CapsightProperty
    scores?: PropertyScores
    valuation?: ValuationResult
    features?: PropertyFeatures
    batch_summary?: {
      total_processed: number
      successful: number
      failed: number
      duration_ms: number
      pipeline_run_id: string
    }
  }
  metadata: {
    source: 'ingestion_pipeline'
    version: string
    pipeline_run_id: string
    environment: string
  }
}

export class WebhookEmissionService {
  private webhookClient: ProductionWebhookClient
  private config = getIngestionConfig()
  private pipelineRunId: string
  
  constructor(pipelineRunId?: string) {
    this.pipelineRunId = pipelineRunId || this.generateRunId()
    this.webhookClient = new ProductionWebhookClient({
      baseUrl: this.config.n8n_ingest_url,
      secret: this.config.webhook_secret,
      maxRetries: 3,
      timeout: 30000
    })
    
    console.log(`🔗 Webhook emission service initialized for run: ${this.pipelineRunId}`)
  }
  
  // ===== INDIVIDUAL PROPERTY EVENTS =====
  
  async emitPropertyIngested(property: CapsightProperty): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'property_ingested',
      timestamp: new Date().toISOString(),
      data: { property },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`🔗 Property ingested event sent: ${property.id}`)
  }
  
  async emitPropertyScored(property: CapsightProperty, scores: PropertyScores): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'property_scored',
      timestamp: new Date().toISOString(),
      data: { property, scores },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`🔗 Property scored event sent: ${property.id} (${scores.classification}/${scores.deal_score})`)
  }
  
  async emitPropertyValued(property: CapsightProperty, valuation: ValuationResult): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'property_valued',
      timestamp: new Date().toISOString(),
      data: { property, valuation },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`🔗 Property valued event sent: ${property.id} ($${valuation.current_value.point.toLocaleString()})`)
  }
  
  // ===== BATCH EVENTS =====
  
  async emitBatchComplete(
    totalProcessed: number,
    successful: number,
    failed: number,
    durationMs: number
  ): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'batch_complete',
      timestamp: new Date().toISOString(),
      data: {
        batch_summary: {
          total_processed: totalProcessed,
          successful: successful,
          failed: failed,
          duration_ms: durationMs,
          pipeline_run_id: this.pipelineRunId
        }
      },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`🔗 Batch complete event sent: ${successful}/${totalProcessed} successful (${Math.round(durationMs/1000)}s)`)
  }
  
  // ===== BULK EMISSION FOR HIGH-VOLUME BATCHES =====
  
  async emitBulkEvents(
    properties: CapsightProperty[],
    scores: PropertyScores[],
    valuations: ValuationResult[]
  ): Promise<{ sent: number, failed: number }> {
    console.log(`🔗 Emitting bulk events for ${properties.length} properties...`)
    
    let sent = 0
    let failed = 0
    const startTime = Date.now()
    
    // Create lookup maps
    const scoresMap = new Map(scores.map(s => [s.property_id, s]))
    const valuationsMap = new Map(valuations.map(v => [v.property_id, v]))
    
    // Process properties in smaller batches to avoid overwhelming webhook
    const batchSize = 10
    for (let i = 0; i < properties.length; i += batchSize) {
      const batch = properties.slice(i, i + batchSize)
      
      // Send events for this batch
      const batchPromises = batch.map(async (property) => {
        try {
          // Send all available events for this property
          await this.emitPropertyIngested(property)
          
          const propertyScores = scoresMap.get(property.id)
          if (propertyScores) {
            await this.emitPropertyScored(property, propertyScores)
          }
          
          const valuation = valuationsMap.get(property.id)
          if (valuation) {
            await this.emitPropertyValued(property, valuation)
          }
          
          sent++
          
        } catch (error) {
          console.error(`❌ Failed to emit events for property ${property.id}:`, error)
          failed++
        }
      })
      
      await Promise.all(batchPromises)
      
      // Rate limiting: 500ms between batches
      if (i + batchSize < properties.length) {
        await new Promise(resolve => setTimeout(resolve, 500))
      }
      
      console.log(`🔗 Batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(properties.length/batchSize)} events sent`)
    }
    
    const durationMs = Date.now() - startTime
    
    // Send batch completion event
    try {
      await this.emitBatchComplete(properties.length, sent, failed, durationMs)
    } catch (error) {
      console.error(`❌ Failed to send batch complete event:`, error)
    }
    
    console.log(`🔗 Bulk emission complete: ${sent} sent, ${failed} failed (${Math.round(durationMs/1000)}s)`)
    return { sent, failed }
  }
  
  // ===== SPECIALIZED EVENTS =====
  
  async emitHighValueOpportunity(property: CapsightProperty, scores: PropertyScores, valuation: ValuationResult): Promise<void> {
    // Special event for high-value opportunities (Deal Score > 75)
    if (scores.deal_score <= 75) return
    
    const event = {
      id: this.generateEventId(),
      type: 'high_value_opportunity',
      timestamp: new Date().toISOString(),
      data: { 
        property, 
        scores, 
        valuation,
        opportunity_flags: {
          deal_score: scores.deal_score,
          classification: scores.classification,
          estimated_value: valuation.current_value.point,
          confidence: scores.confidence
        }
      },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development',
        priority: 'high'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`🚨 HIGH VALUE OPPORTUNITY: ${property.address} - Deal Score: ${scores.deal_score}`)
  }
  
  async emitMarketAnomalyDetected(property: CapsightProperty, anomalyType: string, details: any): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'market_anomaly',
      timestamp: new Date().toISOString(),
      data: { 
        property,
        anomaly: {
          type: anomalyType,
          details,
          detected_at: new Date().toISOString()
        }
      },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development',
        priority: 'medium'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`⚠️ Market anomaly detected: ${anomalyType} for ${property.address}`)
  }
  
  // ===== HEALTH AND STATUS EVENTS =====
  
  async emitPipelineStarted(expectedCount?: number): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'pipeline_started',
      timestamp: new Date().toISOString(),
      data: {
        pipeline_run_id: this.pipelineRunId,
        expected_properties: expectedCount || null
      },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`🚀 Pipeline started event sent: ${this.pipelineRunId}`)
  }
  
  async emitPipelineCompleted(summary: any): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'pipeline_completed',
      timestamp: new Date().toISOString(),
      data: {
        pipeline_run_id: this.pipelineRunId,
        summary
      },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development'
      }
    }
    
    await this.webhookClient.send(event)
    console.log(`✅ Pipeline completed event sent: ${this.pipelineRunId}`)
  }
  
  async emitPipelineError(error: Error, stage?: string): Promise<void> {
    const event = {
      id: this.generateEventId(),
      type: 'pipeline_error',
      timestamp: new Date().toISOString(),
      data: {
        pipeline_run_id: this.pipelineRunId,
        error: {
          message: error.message,
          stack: error.stack,
          stage: stage || 'unknown'
        }
      },
      metadata: {
        source: 'ingestion_pipeline',
        version: '1.0.0',
        pipeline_run_id: this.pipelineRunId,
        environment: process.env.NODE_ENV || 'development',
        priority: 'high'
      }
    }
    
    await this.webhookClient.send(event)
    console.error(`❌ Pipeline error event sent: ${error.message}`)
  }
  
  // ===== UTILITY METHODS =====
  
  private generateRunId(): string {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const random = Math.random().toString(36).substr(2, 8)
    return `ingestion-${timestamp}-${random}`
  }
  
  private generateEventId(): string {
    const timestamp = Date.now()
    const random = Math.random().toString(36).substr(2, 12)
    return `evt-${timestamp}-${random}`
  }
  
  // ===== HEALTH CHECK =====
  
  async healthCheck(): Promise<{ healthy: boolean, latencyMs?: number }> {
    try {
      const startTime = Date.now()
      
      const testEvent = {
        id: this.generateEventId(),
        type: 'health_check',
        timestamp: new Date().toISOString(),
        data: { test: true },
        metadata: {
          source: 'ingestion_pipeline',
          version: '1.0.0',
          pipeline_run_id: this.pipelineRunId,
          environment: process.env.NODE_ENV || 'development'
        }
      }
      
      await this.webhookClient.send(testEvent)
      
      const latencyMs = Date.now() - startTime
      console.log(`✅ Webhook health check passed (${latencyMs}ms)`)
      
      return { healthy: true, latencyMs }
      
    } catch (error) {
      console.error(`❌ Webhook health check failed:`, error)
      return { healthy: false }
    }
  }
}

// Export factory function
export function createWebhookEmissionService(pipelineRunId?: string): WebhookEmissionService {
  return new WebhookEmissionService(pipelineRunId)
}
