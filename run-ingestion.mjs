#!/usr/bin/env node

/**
 * ===== CAPSIGHT INGESTION PIPELINE CLI =====
 * Command-line interface for running the property ingestion pipeline
 * 
 * Usage:
 *   node run-ingestion.mjs --help
 *   node run-ingestion.mjs --max-properties 100 --enable-webhooks
 *   node run-ingestion.mjs --dry-run --county-data sample.csv
 *   node run-ingestion.mjs --health-check
 */

import { ingestionOrchestrator } from './lib/ingestion-orchestrator.ts'
import { getIngestionConfig } from './lib/ingestion-config.ts'

// CLI argument parsing
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    maxProperties: undefined,
    enableWebhooks: true,
    countyDataSource: undefined,
    skipStages: [],
    dryRun: false,
    healthCheck: false,
    runId: undefined,
    help: false
  }
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    
    switch (arg) {
      case '--help':
      case '-h':
        options.help = true
        break
        
      case '--max-properties':
      case '-m':
        options.maxProperties = parseInt(args[++i])
        break
        
      case '--disable-webhooks':
        options.enableWebhooks = false
        break
        
      case '--enable-webhooks':
        options.enableWebhooks = true
        break
        
      case '--county-data':
      case '-c':
        options.countyDataSource = args[++i]
        break
        
      case '--skip-stages':
        options.skipStages = args[++i].split(',')
        break
        
      case '--dry-run':
      case '-d':
        options.dryRun = true
        break
        
      case '--health-check':
        options.healthCheck = true
        break
        
      case '--run-id':
        options.runId = args[++i]
        break
        
      default:
        console.error(`❌ Unknown argument: ${arg}`)
        options.help = true
        break
    }
  }
  
  return options
}

function printHelp() {
  console.log(`
🏗️  CapSight Ingestion Pipeline CLI

USAGE:
  node run-ingestion.mjs [OPTIONS]

OPTIONS:
  --help, -h              Show this help message
  --max-properties, -m    Maximum number of properties to process
  --enable-webhooks       Enable webhook events (default: true)
  --disable-webhooks      Disable webhook events
  --county-data, -c       County data source (file path or identifier)
  --skip-stages          Comma-separated list of stages to skip
                         (ingestion,normalization,enrichment,valuation,scoring,persistence,webhooks)
  --dry-run, -d          Run pipeline without saving to database
  --health-check         Run health check and exit
  --run-id               Custom run ID for this pipeline execution

EXAMPLES:
  # Run full pipeline with 100 properties
  node run-ingestion.mjs --max-properties 100

  # Dry run without webhooks
  node run-ingestion.mjs --dry-run --disable-webhooks

  # Skip persistence and webhooks for testing
  node run-ingestion.mjs --skip-stages persistence,webhooks

  # Health check
  node run-ingestion.mjs --health-check

  # Custom data source
  node run-ingestion.mjs --county-data county_assessor_2024.csv

ENVIRONMENT VARIABLES:
  See .env.example for required configuration variables.

STAGES:
  1. Ingestion     - Fetch raw property data from connectors
  2. Normalization - Clean and standardize property data
  3. Enrichment    - Add market data, demographics, risk factors
  4. Valuation     - Compute property valuations
  5. Scoring       - Calculate Deal Score, MTS, and classifications
  6. Persistence   - Save results to Supabase database
  7. Webhooks      - Emit events to n8n webhook

`)
}

async function runHealthCheck() {
  console.log(`🏥 Running health check...`)
  
  try {
    const health = await ingestionOrchestrator.healthCheck()
    
    console.log(`\n📊 HEALTH CHECK RESULTS`)
    console.log(`=======================`)
    console.log(`Overall Status: ${health.healthy ? '✅ HEALTHY' : '❌ UNHEALTHY'}`)
    console.log(`Timestamp: ${health.timestamp}`)
    console.log(`Node Version: ${health.config.node_version}`)
    console.log(`Environment: ${health.config.environment}`)
    console.log(`Max Batch Size: ${health.config.max_batch_size}`)
    
    console.log(`\n🗺️  GEOCODING SERVICE`)
    console.log(`Cache Size: ${health.geocoding.cache_size}`)
    console.log(`Cache Hit Rate: ${(health.geocoding.cache_hit_rate * 100).toFixed(1)}%`)
    console.log(`Total Requests: ${health.geocoding.total_requests}`)
    
    console.log(`\n💾 SUPABASE DATABASE`)
    console.log(`Properties: ${health.supabase.properties_total.toLocaleString()}`)
    console.log(`Valuations: ${health.supabase.valuations_total.toLocaleString()}`)
    console.log(`Scores: ${health.supabase.scores_total.toLocaleString()}`)
    console.log(`Features: ${health.supabase.features_total.toLocaleString()}`)
    
    console.log(`\n🔗 WEBHOOK SERVICE`)
    if (health.webhook.healthy) {
      console.log(`Status: ✅ Connected (${health.webhook.latencyMs}ms)`)
    } else {
      console.log(`Status: ❌ ${health.webhook.reason || 'Disconnected'}`)
    }
    
    process.exit(health.healthy ? 0 : 1)
    
  } catch (error) {
    console.error(`❌ Health check failed:`, error.message)
    process.exit(1)
  }
}

async function runPipeline(options) {
  console.log(`🚀 Starting CapSight Ingestion Pipeline`)
  console.log(`=====================================`)
  
  // Validate configuration
  try {
    const config = getIngestionConfig()
    console.log(`✅ Configuration validated`)
  } catch (error) {
    console.error(`❌ Configuration error:`, error.message)
    console.error(`💡 Check your .env file and ensure all required variables are set`)
    process.exit(1)
  }
  
  const startTime = Date.now()
  
  try {
    const pipelineOptions = {
      run_id: options.runId,
      max_properties: options.maxProperties,
      enable_webhooks: options.enableWebhooks,
      county_data_source: options.countyDataSource,
      skip_stages: options.skipStages,
      dry_run: options.dryRun
    }
    
    const summary = await ingestionOrchestrator.runFullPipeline(pipelineOptions)
    
    // Print detailed summary
    console.log(`\n📊 PIPELINE EXECUTION SUMMARY`)
    console.log(`==============================`)
    console.log(`Run ID: ${summary.run_id}`)
    console.log(`Started: ${summary.started_at}`)
    console.log(`Completed: ${summary.completed_at}`)
    console.log(`Duration: ${Math.round(summary.duration_ms / 1000)}s`)
    console.log(`Total Processed: ${summary.total_processed}`)
    console.log(`Successful: ${summary.successful_properties}`)
    console.log(`Failed: ${summary.failed_properties}`)
    console.log(`Webhook Events Sent: ${summary.webhook_events_sent}`)
    console.log(`Webhook Events Failed: ${summary.webhook_events_failed}`)
    
    console.log(`\n📈 STAGE BREAKDOWN`)
    console.log(`==================`)
    for (const [stage, result] of Object.entries(summary.stages)) {
      const status = result.errors.length > 0 ? '⚠️ ' : '✅'
      console.log(`${status} ${stage.padEnd(12)}: ${result.success} successful`)
      if (result.errors.length > 0) {
        result.errors.forEach(error => console.log(`   ❌ ${error}`))
      }
    }
    
    const successRate = (summary.successful_properties / summary.total_processed * 100).toFixed(1)
    console.log(`\n🎯 SUCCESS RATE: ${successRate}%`)
    
    if (summary.failed_properties > 0) {
      console.log(`⚠️  ${summary.failed_properties} properties failed processing`)
      process.exit(1)
    } else {
      console.log(`✅ Pipeline completed successfully!`)
      process.exit(0)
    }
    
  } catch (error) {
    const duration = Date.now() - startTime
    console.error(`\n❌ PIPELINE FAILED after ${Math.round(duration / 1000)}s`)
    console.error(`Error: ${error.message}`)
    
    if (error.stack) {
      console.error(`\nStack trace:`)
      console.error(error.stack)
    }
    
    process.exit(1)
  }
}

// Main execution
async function main() {
  const options = parseArgs()
  
  if (options.help) {
    printHelp()
    process.exit(0)
  }
  
  if (options.healthCheck) {
    await runHealthCheck()
    return
  }
  
  await runPipeline(options)
}

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  console.error(`💥 Uncaught Exception:`, error)
  process.exit(1)
})

process.on('unhandledRejection', (reason, promise) => {
  console.error(`💥 Unhandled Rejection at:`, promise, 'reason:', reason)
  process.exit(1)
})

// Graceful shutdown
process.on('SIGINT', () => {
  console.log(`\n🛑 Received SIGINT, shutting down gracefully...`)
  process.exit(0)
})

process.on('SIGTERM', () => {
  console.log(`\n🛑 Received SIGTERM, shutting down gracefully...`)
  process.exit(0)
})

// Run the CLI
main().catch((error) => {
  console.error(`💥 Fatal error:`, error)
  process.exit(1)
})
