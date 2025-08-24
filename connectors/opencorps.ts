/**
 * ===== OPENCORPORATES CONNECTOR =====
 * Unmasks LLC owners and resolves entity hierarchies
 * Uses OpenCorporates API to find beneficial ownership
 */

import type { ConnectorResult, DataProvenance } from '../lib/ingestion-types'

interface OpenCorpsCompany {
  name: string
  company_number: string
  jurisdiction_code: string
  company_type?: string
  incorporation_date?: string
  dissolution_date?: string
  registry_url?: string
  current_status?: string
  registered_address?: {
    street_address?: string
    locality?: string
    region?: string
    postal_code?: string
    country?: string
  }
  officers?: OpenCorpsOfficer[]
  beneficial_owners?: OpenCorpsBeneficialOwner[]
}

interface OpenCorpsOfficer {
  name: string
  position?: string
  start_date?: string
  end_date?: string
  address?: string
}

interface OpenCorpsBeneficialOwner {
  name: string
  kind?: string
  percentage?: number
  start_date?: string
  end_date?: string
}

interface EntityResolution {
  original_name: string
  resolved_company: OpenCorpsCompany | null
  parent_entities: OpenCorpsCompany[]
  beneficial_owners: string[]
  confidence_score: number
  resolution_method: 'exact_match' | 'fuzzy_match' | 'manual' | 'failed'
}

export class OpenCorporatesConnector {
  private readonly baseUrl = 'https://api.opencorporates.com/v0.4'
  private readonly cache = new Map<string, { data: EntityResolution, timestamp: number }>()
  private readonly cacheMs = 7 * 24 * 60 * 60 * 1000 // 7 days - entity data changes slowly
  private readonly rateLimitMs = 1000 // 1 request per second for free tier

  constructor(private apiToken?: string) {
    if (!apiToken) {
      console.warn('⚠️ OpenCorporates API token not provided - limited to free tier (200 requests/month)')
    }
  }

  async resolveEntities(
    entityNames: string[]
  ): Promise<ConnectorResult<EntityResolution>> {
    const startTime = Date.now()
    
    console.log(`🏢 Resolving ${entityNames.length} entities via OpenCorporates...`)

    try {
      const resolutions: EntityResolution[] = []
      const errors: string[] = []
      let processedCount = 0

      for (const entityName of entityNames) {
        try {
          const cached = this.getFromCache(entityName)
          if (cached) {
            resolutions.push(cached)
            processedCount++
            continue
          }

          const resolution = await this.resolveEntity(entityName)
          resolutions.push(resolution)
          this.setCache(entityName, resolution)
          processedCount++

          // Rate limiting
          await this.sleep(this.rateLimitMs)

        } catch (error) {
          const message = `Failed to resolve entity ${entityName}: ${error instanceof Error ? error.message : String(error)}`
          console.warn(`⚠️ ${message}`)
          errors.push(message)
          
          // Add failed resolution
          resolutions.push({
            original_name: entityName,
            resolved_company: null,
            parent_entities: [],
            beneficial_owners: [],
            confidence_score: 0,
            resolution_method: 'failed'
          })
        }
      }

      const duration = Date.now() - startTime
      console.log(`✅ Entity resolution completed: ${processedCount}/${entityNames.length} entities in ${duration}ms`)

      return {
        rows: resolutions,
        provenance: this.createProvenance(),
        stats: {
          total_fetched: entityNames.length,
          total_valid: resolutions.filter(r => r.resolved_company !== null).length,
          total_skipped: entityNames.length - processedCount,
          errors
        }
      }

    } catch (error) {
      console.error(`❌ OpenCorporates connector failed: ${error instanceof Error ? error.message : String(error)}`)
      return {
        rows: [],
        provenance: this.createProvenance(true),
        stats: {
          total_fetched: 0,
          total_valid: 0,
          total_skipped: 0,
          errors: [error instanceof Error ? error.message : String(error)]
        }
      }
    }
  }

  async resolveEntity(entityName: string): Promise<EntityResolution> {
    const cleanName = this.cleanEntityName(entityName)
    
    try {
      // First try exact search
      const exactMatches = await this.searchCompanies(cleanName, true)
      
      if (exactMatches.length > 0) {
        const company = exactMatches[0]
        const parents = await this.findParentEntities(company)
        
        return {
          original_name: entityName,
          resolved_company: company,
          parent_entities: parents,
          beneficial_owners: this.extractBeneficialOwners(company, parents),
          confidence_score: 0.95,
          resolution_method: 'exact_match'
        }
      }

      // Try fuzzy search
      const fuzzyMatches = await this.searchCompanies(cleanName, false)
      
      if (fuzzyMatches.length > 0) {
        const bestMatch = this.selectBestMatch(cleanName, fuzzyMatches)
        const parents = await this.findParentEntities(bestMatch)
        
        return {
          original_name: entityName,
          resolved_company: bestMatch,
          parent_entities: parents,
          beneficial_owners: this.extractBeneficialOwners(bestMatch, parents),
          confidence_score: this.calculateConfidenceScore(cleanName, bestMatch.name),
          resolution_method: 'fuzzy_match'
        }
      }

      // No matches found
      return {
        original_name: entityName,
        resolved_company: null,
        parent_entities: [],
        beneficial_owners: [],
        confidence_score: 0,
        resolution_method: 'failed'
      }

    } catch (error) {
      throw new Error(`Entity resolution failed for ${entityName}: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private async searchCompanies(query: string, exact: boolean = false): Promise<OpenCorpsCompany[]> {
    const params = new URLSearchParams({
      q: query,
      order: 'score',
      per_page: exact ? '1' : '5'
    })

    if (this.apiToken) {
      params.set('api_token', this.apiToken)
    }

    const url = `${this.baseUrl}/companies/search?${params}`

    try {
      const response = await fetch(url, {
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'CapSight/1.0'
        }
      })

      if (!response.ok) {
        throw new Error(`OpenCorporates API error: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      
      if (!data.results || !data.results.companies) {
        return []
      }

      return data.results.companies.map((item: any) => this.parseCompany(item.company))

    } catch (error) {
      throw new Error(`Company search failed: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private async findParentEntities(company: OpenCorpsCompany): Promise<OpenCorpsCompany[]> {
    // This would require following ownership chains
    // For now, return empty array - would need to implement recursive ownership lookup
    console.log(`🔍 Parent entity lookup not fully implemented for ${company.name}`)
    return []
  }

  private parseCompany(companyData: any): OpenCorpsCompany {
    return {
      name: companyData.name || '',
      company_number: companyData.company_number || '',
      jurisdiction_code: companyData.jurisdiction_code || '',
      company_type: companyData.company_type,
      incorporation_date: companyData.incorporation_date,
      dissolution_date: companyData.dissolution_date,
      registry_url: companyData.registry_url,
      current_status: companyData.current_status,
      registered_address: companyData.registered_address_in_full ? {
        street_address: companyData.registered_address?.street_address,
        locality: companyData.registered_address?.locality,
        region: companyData.registered_address?.region,
        postal_code: companyData.registered_address?.postal_code,
        country: companyData.registered_address?.country
      } : undefined,
      officers: this.parseOfficers(companyData.officers),
      beneficial_owners: this.parseBeneficialOwners(companyData.beneficial_owners)
    }
  }

  private parseOfficers(officers: any[]): OpenCorpsOfficer[] | undefined {
    if (!Array.isArray(officers)) return undefined
    
    return officers.map(officer => ({
      name: officer.name || '',
      position: officer.position,
      start_date: officer.start_date,
      end_date: officer.end_date,
      address: officer.address
    }))
  }

  private parseBeneficialOwners(beneficialOwners: any[]): OpenCorpsBeneficialOwner[] | undefined {
    if (!Array.isArray(beneficialOwners)) return undefined
    
    return beneficialOwners.map(owner => ({
      name: owner.name || '',
      kind: owner.kind,
      percentage: parseFloat(owner.percentage) || undefined,
      start_date: owner.start_date,
      end_date: owner.end_date
    }))
  }

  private cleanEntityName(name: string): string {
    return name
      .trim()
      .replace(/\b(LLC|L\.L\.C\.?|LIMITED LIABILITY COMPANY|CORP\.?|CORPORATION|INC\.?|INCORPORATED|LP|L\.P\.?|LIMITED PARTNERSHIP)\b/gi, '')
      .replace(/[^\w\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  }

  private selectBestMatch(query: string, candidates: OpenCorpsCompany[]): OpenCorpsCompany {
    // Simple scoring based on name similarity
    let bestMatch = candidates[0]
    let bestScore = this.calculateConfidenceScore(query, bestMatch.name)
    
    for (const candidate of candidates.slice(1)) {
      const score = this.calculateConfidenceScore(query, candidate.name)
      if (score > bestScore) {
        bestScore = score
        bestMatch = candidate
      }
    }
    
    return bestMatch
  }

  private calculateConfidenceScore(query: string, match: string): number {
    const cleanQuery = this.cleanEntityName(query.toLowerCase())
    const cleanMatch = this.cleanEntityName(match.toLowerCase())
    
    if (cleanQuery === cleanMatch) return 1.0
    
    // Simple Jaccard similarity
    const queryWords = new Set(cleanQuery.split(' '))
    const matchWords = new Set(cleanMatch.split(' '))
    
    const intersection = new Set(Array.from(queryWords).filter(x => matchWords.has(x)))
    const union = new Set([...Array.from(queryWords), ...Array.from(matchWords)])
    
    return intersection.size / union.size
  }

  private extractBeneficialOwners(company: OpenCorpsCompany, parents: OpenCorpsCompany[]): string[] {
    const owners: string[] = []
    
    // Add beneficial owners if available
    if (company.beneficial_owners) {
      owners.push(...company.beneficial_owners.map(owner => owner.name))
    }
    
    // Add officers as potential beneficial owners
    if (company.officers) {
      owners.push(...company.officers
        .filter(officer => officer.position && 
          ['president', 'ceo', 'managing member', 'owner'].some(role => 
            officer.position!.toLowerCase().includes(role)
          )
        )
        .map(officer => officer.name)
      )
    }
    
    // Add parent entities
    owners.push(...parents.map(parent => parent.name))
    
    // Remove duplicates and return
    return Array.from(new Set(owners)).filter(Boolean)
  }

  private getFromCache(entityName: string): EntityResolution | null {
    const cached = this.cache.get(entityName.toLowerCase())
    if (!cached) return null
    
    if (Date.now() - cached.timestamp > this.cacheMs) {
      this.cache.delete(entityName.toLowerCase())
      return null
    }
    
    console.log(`🏢 Using cached entity resolution for ${entityName}`)
    return cached.data
  }

  private setCache(entityName: string, resolution: EntityResolution): void {
    this.cache.set(entityName.toLowerCase(), {
      data: resolution,
      timestamp: Date.now()
    })
  }

  private createProvenance(hasError: boolean = false): DataProvenance {
    return {
      source: 'OpenCorporates',
      as_of: new Date().toISOString(),
      from_cache: this.cache.size > 0,
      ...(hasError && { error: true })
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // Helper methods
  
  getUltimateOwner(resolution: EntityResolution): string | null {
    if (resolution.beneficial_owners.length === 0) return null
    
    // Return the first beneficial owner or the deepest parent entity
    if (resolution.parent_entities.length > 0) {
      return resolution.parent_entities[resolution.parent_entities.length - 1].name
    }
    
    return resolution.beneficial_owners[0]
  }

  isPublicCompany(resolution: EntityResolution): boolean {
    if (!resolution.resolved_company) return false
    
    const publicIndicators = ['public', 'plc', 'corp', 'corporation']
    const companyType = resolution.resolved_company.company_type?.toLowerCase() || ''
    
    return publicIndicators.some(indicator => companyType.includes(indicator))
  }

  getCacheStats() {
    return {
      total_cached_entities: this.cache.size,
      cache_ttl_days: this.cacheMs / (24 * 60 * 60 * 1000),
      rate_limit_ms: this.rateLimitMs
    }
  }
}

// Singleton export
export const openCorporatesConnector = new OpenCorporatesConnector(process.env.OPEN_CORPORATES_API_KEY)
