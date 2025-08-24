/**
 * ===== WEBHOOK CLIENT VALIDATION TESTS =====
 * Simple validation tests for webhook client without complex mocking
 */

import { createValuationPayload, createInsufficientEvidencePayload } from '../lib/webhook-client'

// Test payload creation functions
console.log('🧪 Testing webhook payload creation...')

try {
  // Test valuation payload creation
  const valuationPayload = createValuationPayload({
    address: '123 Test Street',
    lat: 32.7767,
    lon: -96.7970,
    market: 'DFW',
    submarket: 'Downtown',
    building_sf: 50000,
    year_built: 2020,
    asset_type: 'office',
    rent_psf_yr: 28.5,
    opex_psf_yr: 8.5,
    vacancy_pct: 0.08,
    cap_rate_now_pct: 6.5,
    cap_rate_qoq_delta_bps: -25,
    current_value: {
      point: 21500000,
      low: 19350000,
      high: 23650000,
      confidence: 0.78
    },
    forecast_12m: {
      point: 22575000,
      low: 20318000,
      high: 24833000,
      confidence: 0.65
    },
    drivers: [
      'Market cap rate: 6.25%',
      'Fed funds adjustment: +15bps',
      '8 comparable sales',
      'NOI: $1,400,000'
    ],
    provenance: {
      macro: {
        source: 'FRED',
        as_of: '2024-01-15T10:00:00Z',
        from_cache: false
      },
      fundamentals: {
        source: 'supabase',
        as_of: '2024-01-10T00:00:00Z'
      },
      comps: {
        source: 'supabase', 
        as_of: '2024-01-12T00:00:00Z'
      }
    }
  })

  console.log('✅ Valuation payload created successfully')
  console.log(`   Type: ${valuationPayload.type}`)
  console.log(`   Address: ${valuationPayload.address}`)
  console.log(`   Value: $${valuationPayload.current_value.point.toLocaleString()}`)
  console.log(`   Confidence: ${(valuationPayload.current_value.confidence * 100).toFixed(1)}%`)

  // Test insufficient evidence payload creation
  const insufficientPayload = createInsufficientEvidencePayload({
    address: '456 Insufficient Data Ave',
    reason: ['stale_fundamentals', 'low_comp_count'],
    details: {
      comp_count: 1,
      fundamentals_as_of: '2023-12-01T00:00:00Z'
    },
    provenance: {
      macro: {
        source: 'FRED',
        as_of: '2024-01-15T10:00:00Z',
        from_cache: false
      },
      fundamentals: {
        source: 'supabase',
        as_of: '2023-12-01T00:00:00Z'
      },
      comps: {
        source: 'supabase',
        as_of: '2024-01-12T00:00:00Z'
      }
    }
  })

  console.log('✅ Insufficient evidence payload created successfully')
  console.log(`   Type: ${insufficientPayload.type}`)
  console.log(`   Address: ${insufficientPayload.address}`)
  console.log(`   Reasons: ${insufficientPayload.reason.join(', ')}`)
  console.log(`   Comp count: ${insufficientPayload.details.comp_count}`)

  // Validate schema versions
  if (valuationPayload.schema_version !== '1.0') {
    throw new Error('Invalid schema version for valuation payload')
  }
  if (insufficientPayload.schema_version !== '1.0') {
    throw new Error('Invalid schema version for insufficient payload')
  }

  // Validate required fields
  const requiredFields = ['schema_version', 'type', 'tenant_id', 'as_of', 'model', 'provenance']
  for (const field of requiredFields) {
    if (!(field in valuationPayload)) {
      throw new Error(`Missing required field: ${field}`)
    }
    if (!(field in insufficientPayload)) {
      throw new Error(`Missing required field in insufficient payload: ${field}`)
    }
  }

  // Validate model version format (semver)
  const semverRegex = /^\d+\.\d+\.\d+$/
  if (!semverRegex.test(valuationPayload.model.version)) {
    throw new Error(`Invalid semver format: ${valuationPayload.model.version}`)
  }

  console.log('✅ All webhook payload validations passed!')

} catch (error) {
  console.error('❌ Webhook payload test failed:', error)
  process.exit(1)
}
