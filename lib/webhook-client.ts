/**
 * Production-grade webhook client for n8n integration
 * Handles HMAC signing, retries, circuit breaker, and observability
 */

import crypto from 'crypto'
import { getEnvConfig } from './env-config'

// ===== TYPE DEFINITIONS =====

export interface WebhookPayload {
  id: string
  type: string
  timestamp: string
  [key: string]: any
}

export interface PortfolioAnalytics extends WebhookPayload {
  type: 'portfolio.analytics'
  portfolio_id: string
  total_properties: number
  total_value: number
  performance_metrics: any
  scenario_analysis?: any
  accuracy_grade: string
  provenance: {
    data_sources: Array<{
      name: string
      as_of: string
      from_cache: boolean
    }>
    calculation_id: string
    model_version: string
    computed_at: string
  }
}

export interface PortfolioBatch extends WebhookPayload {
  type: 'portfolio.batch'
  schema_version: string
  tenant_id: string
  as_of: string
  model: {
    name: string
    version: string
  }
  portfolio_id: string
  property_count: number
  portfolio_value: {
    point: number
    low: number
    high: number
    confidence: number
  }
  portfolio_metrics: any
  scenario_analysis?: any
  top_performers: Array<{
    property_id: string
    address: string
    estimated_value: number
    mts_score: number
  }>
  calculated_at: string
}

// ===== WEBHOOK CLIENT =====

export class ProductionWebhookClient {
  private readonly baseUrl: string
  private readonly secret: string
  private readonly maxRetries: number
  private readonly timeout: number
  private circuitBreakerOpen: boolean = false
  private consecutiveFailures: number = 0
  private readonly maxFailures: number = 5

  constructor(config?: {
    baseUrl?: string
    secret?: string
    maxRetries?: number
    timeout?: number
  }) {
    const envConfig = getEnvConfig()
    this.baseUrl = config?.baseUrl || envConfig.n8n_ingest_url || 'https://n8n-webhook.capsight.io/webhook'
    this.secret = config?.secret || envConfig.webhook_secret || 'fallback-secret'
    this.maxRetries = config?.maxRetries || 3
    this.timeout = config?.timeout || 30000
  }

  private generateHMAC(payload: string): string {
    return crypto
      .createHmac('sha256', this.secret)
      .update(payload)
      .digest('hex')
  }

  private async makeRequest(payload: WebhookPayload, retryCount: number = 0): Promise<boolean> {
    if (this.circuitBreakerOpen) {
      throw new Error('Circuit breaker is open - webhook delivery suspended')
    }

    const payloadStr = JSON.stringify(payload)
    const signature = this.generateHMAC(payloadStr)

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.timeout)

      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Signature-SHA256': `sha256=${signature}`,
          'X-Timestamp': new Date().toISOString(),
          'User-Agent': 'CREValuation-Webhook/1.0'
        },
        body: payloadStr,
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      // Reset circuit breaker on success
      this.consecutiveFailures = 0
      this.circuitBreakerOpen = false

      console.log(`✅ Webhook delivered successfully [${payload.type}:${payload.id}]`)
      return true

    } catch (error) {
      this.consecutiveFailures++
      
      if (this.consecutiveFailures >= this.maxFailures) {
        this.circuitBreakerOpen = true
        console.error(`🚫 Circuit breaker opened after ${this.maxFailures} failures`)
      }

      if (retryCount < this.maxRetries) {
        const backoffMs = Math.pow(2, retryCount) * 1000
        console.warn(`⚠️ Webhook failed, retrying in ${backoffMs}ms... (${retryCount + 1}/${this.maxRetries})`)
        
        await new Promise(resolve => setTimeout(resolve, backoffMs))
        return this.makeRequest(payload, retryCount + 1)
      }

      throw error
    }
  }

  async send(payload: WebhookPayload, requestId?: string): Promise<boolean> {
    try {
      const enrichedPayload = {
        ...payload,
        id: payload.id || crypto.randomUUID(),
        timestamp: payload.timestamp || new Date().toISOString(),
        request_id: requestId
      }

      return await this.makeRequest(enrichedPayload)
    } catch (error) {
      console.error('❌ Webhook delivery failed:', error)
      return false
    }
  }

  // Health check method
  getCircuitBreakerStatus(): { open: boolean; failures: number } {
    return {
      open: this.circuitBreakerOpen,
      failures: this.consecutiveFailures
    }
  }
}

// ===== FACTORY FUNCTION =====

let webhookClientInstance: ProductionWebhookClient | null = null

export function getWebhookClient(): ProductionWebhookClient {
  if (!webhookClientInstance) {
    webhookClientInstance = new ProductionWebhookClient()
  }
  return webhookClientInstance
}

// ===== HELPER FUNCTIONS =====

export function createWebhookPayload<T extends WebhookPayload>(type: string, data: Omit<T, 'id' | 'type' | 'timestamp'>): T {
  return {
    id: crypto.randomUUID(),
    type,
    timestamp: new Date().toISOString(),
    ...data
  } as T
}
