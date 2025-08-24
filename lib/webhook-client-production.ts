/**
 * ===== PRODUCTION WEBHOOK CLIENT =====
 * HMAC-signed, idempotent, observable webhook client for n8n integration
 */

import { createHash, createHmac, randomUUID } from 'crypto'
import { getEnvConfig } from './env-config'

// ===== TYPE DEFINITIONS =====
interface Provenance {
  macro: {
    source: string
    as_of: string
    from_cache: boolean
  }
  fundamentals: {
    source: string
    as_of: string
  }
  comps: {
    source: string
    as_of: string
  }
}

interface BaseWebhookPayload {
  schema_version: '1.0'
  type: 'valuation.upsert' | 'valuation.insufficient'
  tenant_id: string
  as_of: string
  model: {
    name: string
    version: string
  }
  provenance: Provenance
}

export interface ValuationUpsert extends BaseWebhookPayload {
  type: 'valuation.upsert'
  address?: string
  geo: {
    lat: number
    lon: number
    market: string
    submarket: string
  }
  property_snapshot: {
    building_sf: number
    year_built?: number
    last_sale_price?: number
    last_sale_date?: string
  }
  inputs: {
    asset_type: 'office' | 'industrial' | 'retail' | 'multifamily' | 'mixed-use'
    rent_psf_yr: number
    opex_psf_yr: number
    vacancy_pct: number
    cap_rate_now_pct: number
    cap_rate_qoq_delta_bps: number
  }
  current_value: {
    point: number
    low: number
    high: number
    confidence: number
  }
  forecast_12m: {
    point: number
    low: number
    high: number
    confidence: number
  }
  drivers: string[]
  status?: 'FRESH' | 'STALE_DATA'
  warning?: string
}

export interface ValuationInsufficient extends BaseWebhookPayload {
  type: 'valuation.insufficient'
  address?: string
  reason: Array<'stale_fundamentals' | 'low_comp_count' | 'no_macro_data' | 'invalid_inputs'>
  details: {
    comp_count?: number
    fundamentals_as_of?: string
    macro_as_of?: string
  }
  status: 'INSUFFICIENT_DATA'
}

type WebhookPayload = ValuationUpsert | ValuationInsufficient

// ===== CIRCUIT BREAKER =====
class CircuitBreaker {
  private failures = 0
  private lastFailureTime: number | null = null
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED'
  private readonly timeout: number

  constructor(private threshold: number, timeoutMinutes: number = 2) {
    this.timeout = timeoutMinutes * 60 * 1000
  }

  canExecute(): boolean {
    if (this.state === 'CLOSED') return true
    
    if (this.state === 'OPEN') {
      if (this.lastFailureTime && Date.now() - this.lastFailureTime > this.timeout) {
        this.state = 'HALF_OPEN'
        return true
      }
      return false
    }
    
    return true
  }

  onSuccess(): void {
    this.failures = 0
    this.state = 'CLOSED'
    this.lastFailureTime = null
  }

  onFailure(): void {
    this.failures++
    this.lastFailureTime = Date.now()
    
    if (this.failures >= this.threshold) {
      this.state = 'OPEN'
    }
  }

  getState() {
    return {
      state: this.state,
      failures: this.failures,
      lastFailureTime: this.lastFailureTime ? new Date(this.lastFailureTime).toISOString() : null
    }
  }
}

// ===== WEBHOOK METRICS =====
class WebhookMetrics {
  private static latencies: number[] = []
  private static retryCount = 0
  private static successCount = 0
  private static failureCount = 0

  static recordLatency(ms: number) {
    this.latencies.push(ms)
    if (this.latencies.length > 1000) {
      this.latencies.shift()
    }
  }

  static recordRetry() { this.retryCount++ }
  static recordSuccess() { this.successCount++ }
  static recordFailure() { this.failureCount++ }

  static getMetrics() {
    const sortedLatencies = [...this.latencies].sort((a, b) => a - b)
    const p50 = sortedLatencies[Math.floor(sortedLatencies.length * 0.5)] || 0
    const p95 = sortedLatencies[Math.floor(sortedLatencies.length * 0.95)] || 0
    
    const total = this.successCount + this.failureCount
    const successRatio = total > 0 ? this.successCount / total : 0
    
    return {
      webhook_post_latency_ms_p50: p50,
      webhook_post_latency_ms_p95: p95,
      webhook_retries_total: this.retryCount,
      webhook_success_ratio: successRatio,
      total_requests: total
    }
  }
}

// ===== MAIN WEBHOOK CLIENT =====
export class ProductionWebhookClient {
  private circuitBreaker: CircuitBreaker
  private config = getEnvConfig()
  private static auditLog: Array<{
    timestamp: string
    request_id: string
    tenant_id: string
    type: string
    payload_hash: string
    status_code: number
    attempt: number
    duration_ms: number
    bytes: number
  }> = []

  constructor() {
    this.circuitBreaker = new CircuitBreaker(
      this.config.circuit_breaker_failure_threshold,
      this.config.circuit_breaker_timeout_minutes
    )
  }

  async send(payload: WebhookPayload, correlationId?: string): Promise<{
    success: boolean
    requestId: string
    attempts: number
    finalStatusCode?: number
    error?: string
  }> {
    const requestId = correlationId || randomUUID()
    const startTime = Date.now()

    try {
      // 1. VALIDATE PAYLOAD
      const validationResult = this.validatePayload(payload)
      if (!validationResult.valid) {
        console.error(`❌ Webhook validation failed [${requestId}]:`, validationResult.errors)
        return {
          success: false,
          requestId,
          attempts: 0,
          error: `Validation failed: ${validationResult.errors.join(', ')}`
        }
      }

      // 2. ADJUST FOR STALE DATA
      const adjustedPayload = this.adjustForStaleness(payload)

      // 3. ADD PAYLOAD HASH FOR IDEMPOTENCY
      const hashedPayload = this.addPayloadHash(adjustedPayload)

      // 4. CHECK CIRCUIT BREAKER
      if (!this.circuitBreaker.canExecute()) {
        console.warn(`⚡ Circuit breaker OPEN [${requestId}]`)
        return {
          success: false,
          requestId,
          attempts: 0,
          error: 'Circuit breaker open'
        }
      }

      // 5. SEND WITH RETRIES
      const result = await this.sendWithRetries(hashedPayload, requestId)

      // 6. UPDATE CIRCUIT BREAKER
      if (result.success) {
        this.circuitBreaker.onSuccess()
      } else if (result.finalStatusCode && result.finalStatusCode >= 500) {
        this.circuitBreaker.onFailure()
      }

      // 7. AUDIT LOG
      if (result.success) {
        this.logAuditRecord({
          timestamp: new Date().toISOString(),
          request_id: requestId,
          tenant_id: hashedPayload.tenant_id,
          type: hashedPayload.type,
          payload_hash: hashedPayload.payload_hash,
          status_code: result.finalStatusCode || 200,
          attempt: result.attempts,
          duration_ms: Date.now() - startTime,
          bytes: JSON.stringify(hashedPayload).length
        })
      }

      return { ...result, requestId }

    } catch (error) {
      console.error(`❌ Webhook send failed [${requestId}]:`, error)
      return {
        success: false,
        requestId,
        attempts: 0,
        error: error instanceof Error ? error.message : String(error)
      }
    }
  }

  getMetrics() {
    return {
      ...WebhookMetrics.getMetrics(),
      circuit_breaker: this.circuitBreaker.getState(),
      audit_records: ProductionWebhookClient.auditLog.length
    }
  }

  // ===== PRIVATE METHODS =====
  
  private async sendWithRetries(payload: WebhookPayload & { payload_hash: string }, requestId: string) {
    const maxRetries = 5
    const baseDelay = 500
    let attempt = 0
    let lastError = ''
    let lastStatusCode: number | undefined

    while (attempt < maxRetries) {
      attempt++
      const startTime = Date.now()

      try {
        const response = await this.makeHttpRequest(payload, requestId, attempt)
        const latency = Date.now() - startTime
        
        WebhookMetrics.recordLatency(latency)

        if (response.ok) {
          WebhookMetrics.recordSuccess()
          console.log(`✅ Webhook sent [${requestId}] (${latency}ms, attempt ${attempt})`)
          return {
            success: true,
            attempts: attempt,
            finalStatusCode: response.status
          }
        }

        lastStatusCode = response.status

        // Handle rate limiting (429)
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After')
          const waitMs = retryAfter ? parseInt(retryAfter) * 1000 : baseDelay * Math.pow(2, attempt - 1)
          
          console.warn(`⏰ Rate limited [${requestId}] - waiting ${waitMs}ms (attempt ${attempt}/${maxRetries})`)
          WebhookMetrics.recordRetry()
          
          if (attempt < maxRetries) {
            await this.sleep(waitMs)
            continue
          }
        }

        // Handle server errors (5xx) - retry
        if (response.status >= 500) {
          const backoffMs = baseDelay * Math.pow(2, attempt - 1)
          lastError = `HTTP ${response.status}: ${response.statusText}`
          
          console.warn(`⚠️ Server error [${requestId}] - retrying in ${backoffMs}ms (attempt ${attempt}/${maxRetries})`)
          WebhookMetrics.recordRetry()
          
          if (attempt < maxRetries) {
            await this.sleep(backoffMs)
            continue
          }
        }

        // Client errors (4xx) - don't retry
        if (response.status >= 400 && response.status < 500) {
          const errorText = await response.text().catch(() => 'Unknown error')
          lastError = `HTTP ${response.status}: ${errorText}`
          console.error(`❌ Client error [${requestId}] - not retrying: ${lastError}`)
          break
        }

      } catch (error) {
        lastError = error instanceof Error ? error.message : String(error)
        const backoffMs = baseDelay * Math.pow(2, attempt - 1)
        
        console.warn(`⚠️ Network error [${requestId}] - retrying in ${backoffMs}ms (attempt ${attempt}/${maxRetries}): ${lastError}`)
        WebhookMetrics.recordRetry()
        
        if (attempt < maxRetries) {
          await this.sleep(backoffMs)
        }
      }
    }

    WebhookMetrics.recordFailure()
    return {
      success: false,
      attempts: attempt,
      finalStatusCode: lastStatusCode,
      error: lastError
    }
  }

  private async makeHttpRequest(payload: WebhookPayload & { payload_hash: string }, requestId: string, attempt: number): Promise<Response> {
    const body = JSON.stringify(payload)
    const timestamp = new Date().toISOString()
    
    // Generate HMAC signature
    const signature = createHmac('sha256', this.config.webhook_secret).update(body).digest('hex')
    
    const headers = {
      'Content-Type': 'application/json',
      'X-Capsight-Tenant': this.config.tenant_id,
      'X-Request-Id': requestId,
      'X-Timestamp': timestamp,
      'X-Payload-Hash': payload.payload_hash,
      'X-Capsight-Signature': `sha256=${signature}`,
      'User-Agent': 'CapSight-Webhook-Client/1.0.0'
    }

    console.log(`📤 Sending webhook [${requestId}] attempt ${attempt}: ${payload.type}`)

    return fetch(this.config.n8n_ingest_url, {
      method: 'POST',
      headers,
      body,
      signal: AbortSignal.timeout(20000)
    })
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  private validatePayload(payload: WebhookPayload): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    // Required fields
    if (!payload.schema_version) errors.push('schema_version is required')
    if (!payload.type) errors.push('type is required')
    if (!payload.tenant_id) errors.push('tenant_id is required')
    if (!payload.as_of) errors.push('as_of is required')
    if (!payload.model?.name) errors.push('model.name is required')
    if (!payload.model?.version) errors.push('model.version is required')
    if (!payload.provenance) errors.push('provenance is required')

    // Semver format
    if (payload.model?.version && !/^\d+\.\d+\.\d+$/.test(payload.model.version)) {
      errors.push('model.version must be valid semver')
    }

    // Type-specific validation
    if (payload.type === 'valuation.upsert') {
      const valuation = payload as ValuationUpsert
      
      // Range checks
      if (valuation.inputs) {
        if (valuation.inputs.vacancy_pct < 0 || valuation.inputs.vacancy_pct > 0.40) {
          errors.push('vacancy_pct must be between 0 and 0.40')
        }
        if (valuation.inputs.cap_rate_now_pct < 2 || valuation.inputs.cap_rate_now_pct > 20) {
          errors.push('cap_rate_now_pct must be between 2 and 20')
        }
        if (valuation.inputs.rent_psf_yr < 0.5 || valuation.inputs.rent_psf_yr > 300) {
          errors.push('rent_psf_yr must be between 0.5 and 300')
        }
      }

      // Confidence bounds
      if (valuation.current_value?.confidence != null) {
        if (valuation.current_value.confidence < 0 || valuation.current_value.confidence > 1) {
          errors.push('confidence must be between 0 and 1')
        }
      }
    }

    return { valid: errors.length === 0, errors }
  }

  private adjustForStaleness(payload: WebhookPayload): WebhookPayload {
    const now = new Date()
    let isStale = false

    // Check data freshness
    const macroAge = this.daysBetween(new Date(payload.provenance.macro.as_of), now)
    const fundamentalsAge = this.daysBetween(new Date(payload.provenance.fundamentals.as_of), now)
    const compsAge = this.daysBetween(new Date(payload.provenance.comps.as_of), now)

    if (macroAge > this.config.freshness_macro_days) isStale = true
    if (fundamentalsAge > this.config.freshness_fundamentals_days) isStale = true
    if (compsAge > this.config.freshness_comps_days) isStale = true

    if (isStale && payload.type === 'valuation.upsert') {
      const adjustedPayload = { ...payload } as ValuationUpsert
      adjustedPayload.status = 'STALE_DATA'
      
      // Reduce confidence by 0.2
      adjustedPayload.current_value.confidence = Math.max(0, adjustedPayload.current_value.confidence - 0.2)
      adjustedPayload.forecast_12m.confidence = Math.max(0, adjustedPayload.forecast_12m.confidence - 0.2)
      
      return adjustedPayload
    }

    return payload
  }

  private daysBetween(date1: Date, date2: Date): number {
    return Math.floor(Math.abs(date2.getTime() - date1.getTime()) / (24 * 60 * 60 * 1000))
  }

  private addPayloadHash(payload: WebhookPayload): WebhookPayload & { payload_hash: string } {
    const payloadString = JSON.stringify(payload)
    const hash = createHash('sha256').update(payloadString).digest('hex')
    
    return {
      ...payload,
      payload_hash: hash
    }
  }

  private logAuditRecord(record: {
    timestamp: string
    request_id: string
    tenant_id: string
    type: string
    payload_hash: string
    status_code: number
    attempt: number
    duration_ms: number
    bytes: number
  }): void {
    ProductionWebhookClient.auditLog.push(record)
    
    // Keep only last 10000 records
    if (ProductionWebhookClient.auditLog.length > 10000) {
      ProductionWebhookClient.auditLog.shift()
    }

    console.log(`📋 Webhook audit [${record.request_id}]: ${record.type} | ${record.status_code} | ${record.duration_ms}ms | ${record.bytes}B`)
  }
}

// ===== SINGLETON INSTANCE =====
let webhookClient: ProductionWebhookClient | null = null

export function getWebhookClient(): ProductionWebhookClient {
  if (!webhookClient) {
    webhookClient = new ProductionWebhookClient()
  }
  return webhookClient
}
