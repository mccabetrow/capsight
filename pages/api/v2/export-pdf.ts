/**
 * ===== PDF EXPORT ENGINE =====
 * Generate investor-ready underwriting reports with provenance
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { randomUUID } from 'crypto'
import puppeteer from 'puppeteer'

interface PDFExportRequest {
  report_type: 'valuation' | 'portfolio' | 'scenario' | 'accuracy'
  data: any // The underlying data to include
  template: 'standard' | 'executive' | 'detailed' | 'pitch'
  branding?: {
    company_name?: string
    logo_url?: string
    primary_color?: string
    secondary_color?: string
  }
  export_options?: {
    include_provenance?: boolean
    include_methodology?: boolean
    include_disclaimers?: boolean
    watermark?: string
  }
}

interface PDFExportResponse {
  export_id: string
  file_url: string
  file_size_bytes: number
  page_count: number
  generated_at: string
  expires_at: string
  report_metadata: {
    title: string
    subtitle: string
    author: string
    subject: string
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<PDFExportResponse | { error: string; export_id: string }>
) {
  const exportId = randomUUID()
  
  if (req.method !== 'POST') {
    return res.status(405).json({ 
      error: 'Method not allowed',
      export_id: exportId
    })
  }
  
  try {
    console.log(`📄 PDF Export started [${exportId}]`)
    
    const {
      report_type,
      data,
      template = 'standard',
      branding = {},
      export_options = {}
    }: PDFExportRequest = req.body
    
    // Validation
    if (!report_type || !data) {
      return res.status(400).json({ 
        error: 'Missing required fields: report_type, data',
        export_id: exportId
      })
    }
    
    // Generate HTML content based on report type and template
    const htmlContent = await generateReportHTML(report_type, data, template, branding, export_options)
    
    // Convert to PDF using Puppeteer
    const pdfBuffer = await generatePDF(htmlContent, template)
    
    // In production, you'd save this to cloud storage (S3, etc.)
    // For now, we'll return a data URL
    const base64Pdf = pdfBuffer.toString('base64')
    const dataUrl = `data:application/pdf;base64,${base64Pdf}`
    
    // Calculate metadata
    const reportMetadata = generateReportMetadata(report_type, data, branding)
    
    const response: PDFExportResponse = {
      export_id: exportId,
      file_url: dataUrl, // In production: actual URL to stored file
      file_size_bytes: pdfBuffer.length,
      page_count: await estimatePageCount(pdfBuffer),
      generated_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days
      report_metadata: reportMetadata
    }
    
    console.log(`✅ PDF Export complete [${exportId}]: ${response.file_size_bytes} bytes, ${response.page_count} pages`)
    
    res.setHeader('Content-Type', 'application/json')
    res.setHeader('X-Export-Id', exportId)
    
    return res.status(200).json(response)
    
  } catch (error) {
    console.error(`❌ PDF Export error [${exportId}]:`, error)
    
    return res.status(500).json({ 
      error: `PDF generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      export_id: exportId
    })
  }
}

// ===== HTML GENERATION =====

async function generateReportHTML(
  reportType: string,
  data: any,
  template: string,
  branding: any,
  exportOptions: any
): Promise<string> {
  
  const baseStyles = generateBaseStyles(branding, template)
  const headerHTML = generateHeader(branding, reportType, data)
  const contentHTML = await generateContent(reportType, data, template, exportOptions)
  const footerHTML = generateFooter(exportOptions)
  
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>${generateTitle(reportType, data)}</title>
      <style>${baseStyles}</style>
    </head>
    <body>
      <div class="report-container">
        ${headerHTML}
        ${contentHTML}
        ${footerHTML}
      </div>
    </body>
    </html>
  `
}

function generateBaseStyles(branding: any, template: string): string {
  const primaryColor = branding.primary_color || '#1f2937'
  const secondaryColor = branding.secondary_color || '#f3f4f6'
  
  return `
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 12px;
      line-height: 1.5;
      color: #374151;
      background: white;
    }
    
    .report-container {
      max-width: 8.5in;
      margin: 0 auto;
      padding: 0.5in;
    }
    
    .header {
      border-bottom: 2px solid ${primaryColor};
      margin-bottom: 30px;
      padding-bottom: 20px;
    }
    
    .header h1 {
      color: ${primaryColor};
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    
    .header h2 {
      color: #6b7280;
      font-size: 16px;
      font-weight: 400;
    }
    
    .header .metadata {
      margin-top: 15px;
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #9ca3af;
    }
    
    .section {
      margin-bottom: 25px;
      page-break-inside: avoid;
    }
    
    .section-title {
      color: ${primaryColor};
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 12px;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 5px;
    }
    
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin: 20px 0;
    }
    
    .metric-card {
      background: ${secondaryColor};
      padding: 15px;
      border-radius: 8px;
      border-left: 4px solid ${primaryColor};
    }
    
    .metric-card .label {
      font-size: 11px;
      color: #6b7280;
      margin-bottom: 5px;
    }
    
    .metric-card .value {
      font-size: 20px;
      font-weight: 700;
      color: ${primaryColor};
    }
    
    .metric-card .change {
      font-size: 11px;
      margin-top: 3px;
    }
    
    .positive { color: #059669; }
    .negative { color: #dc2626; }
    
    .data-table {
      width: 100%;
      border-collapse: collapse;
      margin: 15px 0;
      font-size: 11px;
    }
    
    .data-table th {
      background: ${primaryColor};
      color: white;
      padding: 8px 12px;
      text-align: left;
      font-weight: 600;
    }
    
    .data-table td {
      padding: 6px 12px;
      border-bottom: 1px solid #e5e7eb;
    }
    
    .data-table tr:nth-child(even) {
      background: #f9fafb;
    }
    
    .provenance-box {
      background: #f3f4f6;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      padding: 15px;
      margin: 20px 0;
      font-size: 11px;
    }
    
    .provenance-box h4 {
      color: #374151;
      font-weight: 600;
      margin-bottom: 8px;
    }
    
    .methodology {
      background: #fef3c7;
      border-left: 4px solid #f59e0b;
      padding: 15px;
      margin: 15px 0;
      font-size: 11px;
    }
    
    .footer {
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid #e5e7eb;
      font-size: 10px;
      color: #9ca3af;
      text-align: center;
    }
    
    .disclaimer {
      background: #fef2f2;
      border: 1px solid #fecaca;
      padding: 15px;
      margin: 20px 0;
      border-radius: 6px;
      font-size: 11px;
      color: #991b1b;
    }
    
    .watermark {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) rotate(-45deg);
      font-size: 48px;
      color: rgba(0,0,0,0.1);
      z-index: -1;
      pointer-events: none;
    }
    
    @media print {
      body { -webkit-print-color-adjust: exact; }
      .page-break { page-break-before: always; }
    }
  `
}

function generateHeader(branding: any, reportType: string, data: any): string {
  const companyName = branding.company_name || 'CapSight Analytics'
  const logoHTML = branding.logo_url ? `<img src="${branding.logo_url}" style="height: 40px; float: right;">` : ''
  
  const title = generateTitle(reportType, data)
  const subtitle = generateSubtitle(reportType, data)
  
  return `
    <div class="header">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <h1>${title}</h1>
          <h2>${subtitle}</h2>
        </div>
        ${logoHTML}
      </div>
      <div class="metadata">
        <span>Generated by ${companyName}</span>
        <span>Report Date: ${new Date().toLocaleDateString()}</span>
        <span>Time: ${new Date().toLocaleTimeString()}</span>
      </div>
    </div>
  `
}

async function generateContent(reportType: string, data: any, template: string, exportOptions: any): Promise<string> {
  switch (reportType) {
    case 'valuation':
      return generateValuationContent(data, template, exportOptions)
    case 'portfolio':
      return generatePortfolioContent(data, template, exportOptions)
    case 'scenario':
      return generateScenarioContent(data, template, exportOptions)
    case 'accuracy':
      return generateAccuracyContent(data, template, exportOptions)
    default:
      return '<div class="section"><p>Unknown report type</p></div>'
  }
}

function generateValuationContent(data: any, template: string, exportOptions: any): string {
  const property = data.property || data
  const valuation = data.valuation || data
  
  let content = `
    <div class="section">
      <h3 class="section-title">Executive Summary</h3>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="label">Estimated Value</div>
          <div class="value">$${valuation.estimated_value?.toLocaleString() || 'N/A'}</div>
        </div>
        <div class="metric-card">
          <div class="label">Price Per SF</div>
          <div class="value">$${valuation.price_per_sf?.toLocaleString() || 'N/A'}</div>
        </div>
        <div class="metric-card">
          <div class="label">Cap Rate</div>
          <div class="value">${valuation.cap_rate_applied || 'N/A'}%</div>
        </div>
      </div>
    </div>
    
    <div class="section">
      <h3 class="section-title">Property Details</h3>
      <table class="data-table">
        <tr><td><strong>Address</strong></td><td>${property.address || 'N/A'}</td></tr>
        <tr><td><strong>Market</strong></td><td>${property.market?.toUpperCase() || 'N/A'}</td></tr>
        <tr><td><strong>Building Size</strong></td><td>${property.building_sf?.toLocaleString() || 'N/A'} SF</td></tr>
        <tr><td><strong>Asset Type</strong></td><td>${property.asset_type || 'N/A'}</td></tr>
        <tr><td><strong>Year Built</strong></td><td>${property.year_built || 'N/A'}</td></tr>
      </table>
    </div>
    
    <div class="section">
      <h3 class="section-title">Valuation Analysis</h3>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="label">Value Range (Low)</div>
          <div class="value">$${valuation.estimated_value_range?.low?.toLocaleString() || 'N/A'}</div>
        </div>
        <div class="metric-card">
          <div class="label">Value Range (High)</div>
          <div class="value">$${valuation.estimated_value_range?.high?.toLocaleString() || 'N/A'}</div>
        </div>
        <div class="metric-card">
          <div class="label">Confidence Score</div>
          <div class="value">${(valuation.confidence_score * 100)?.toFixed(1) || 'N/A'}%</div>
        </div>
      </div>
    </div>
  `
  
  // Add forecast section if available
  if (data.forecast_12m) {
    content += `
      <div class="section">
        <h3 class="section-title">12-Month Forecast</h3>
        <div class="metric-grid">
          <div class="metric-card">
            <div class="label">Forecast Value</div>
            <div class="value">$${data.forecast_12m.point?.toLocaleString() || 'N/A'}</div>
            <div class="change ${data.forecast_12m.point > valuation.estimated_value ? 'positive' : 'negative'}">
              ${((data.forecast_12m.point - valuation.estimated_value) / valuation.estimated_value * 100).toFixed(1)}% change
            </div>
          </div>
          <div class="metric-card">
            <div class="label">Forecast Range</div>
            <div class="value">$${data.forecast_12m.low?.toLocaleString()} - $${data.forecast_12m.high?.toLocaleString()}</div>
          </div>
          <div class="metric-card">
            <div class="label">Forecast Confidence</div>
            <div class="value">${(data.forecast_12m.confidence * 100)?.toFixed(1)}%</div>
          </div>
        </div>
      </div>
    `
  }
  
  // Add drivers section
  if (data.drivers && data.drivers.length > 0) {
    content += `
      <div class="section">
        <h3 class="section-title">Key Value Drivers</h3>
        <ul style="margin-left: 20px;">
          ${data.drivers.map((driver: string) => `<li style="margin-bottom: 5px;">${driver}</li>`).join('')}
        </ul>
      </div>
    `
  }
  
  // Add provenance if requested
  if (exportOptions.include_provenance && data.provenance) {
    content += generateProvenanceSection(data.provenance)
  }
  
  // Add methodology if requested
  if (exportOptions.include_methodology) {
    content += generateMethodologySection('valuation')
  }
  
  return content
}

function generatePortfolioContent(data: any, template: string, exportOptions: any): string {
  let content = `
    <div class="section">
      <h3 class="section-title">Portfolio Summary</h3>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="label">Total Properties</div>
          <div class="value">${data.total_properties}</div>
        </div>
        <div class="metric-card">
          <div class="label">Portfolio Value</div>
          <div class="value">$${data.total_value?.toLocaleString()}</div>
        </div>
        <div class="metric-card">
          <div class="label">Avg. Confidence</div>
          <div class="value">${(data.avg_confidence * 100)?.toFixed(1)}%</div>
        </div>
      </div>
    </div>
    
    <div class="section">
      <h3 class="section-title">Portfolio Metrics</h3>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="label">Weighted Cap Rate</div>
          <div class="value">${data.portfolio_metrics?.value_weighted_cap_rate?.toFixed(2)}%</div>
        </div>
        <div class="metric-card">
          <div class="label">Diversification Score</div>
          <div class="value">${data.portfolio_metrics?.diversification_score}/100</div>
        </div>
        <div class="metric-card">
          <div class="label">Risk-Adj. Return</div>
          <div class="value">${data.portfolio_metrics?.risk_adjusted_return?.toFixed(2)}%</div>
        </div>
      </div>
    </div>
  `
  
  // Property table
  if (data.properties && data.properties.length > 0) {
    content += `
      <div class="section page-break">
        <h3 class="section-title">Property Details</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Property</th>
              <th>Market</th>
              <th>Size (SF)</th>
              <th>Value</th>
              <th>Price/SF</th>
              <th>Cap Rate</th>
              <th>MTS</th>
            </tr>
          </thead>
          <tbody>
            ${data.properties.slice(0, 20).map((prop: any) => `
              <tr>
                <td>${prop.property.address || prop.property.id}</td>
                <td>${prop.property.market.toUpperCase()}</td>
                <td>${prop.property.building_sf.toLocaleString()}</td>
                <td>$${prop.valuation.estimated_value.toLocaleString()}</td>
                <td>$${prop.valuation.price_per_sf}</td>
                <td>${prop.valuation.cap_rate_applied}%</td>
                <td>${prop.valuation.mts_score || 'N/A'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        ${data.properties.length > 20 ? `<p style="margin-top: 10px; font-style: italic;">Showing first 20 of ${data.properties.length} properties</p>` : ''}
      </div>
    `
  }
  
  // Scenario analysis if available
  if (data.scenario_analysis) {
    content += generateScenarioSummaryTable(data.scenario_analysis)
  }
  
  return content
}

function generateScenarioContent(data: any, template: string, exportOptions: any): string {
  let content = `
    <div class="section">
      <h3 class="section-title">Scenario Analysis Summary</h3>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="label">Baseline Portfolio</div>
          <div class="value">$${data.baseline_portfolio_value?.toLocaleString()}</div>
        </div>
        <div class="metric-card">
          <div class="label">Scenarios Tested</div>
          <div class="value">${data.total_scenarios}</div>
        </div>
        <div class="metric-card">
          <div class="label">Stress Test Grade</div>
          <div class="value">${data.risk_summary?.stress_test_grade}</div>
        </div>
      </div>
    </div>
    
    <div class="section">
      <h3 class="section-title">Risk Assessment</h3>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="label">Most Vulnerable</div>
          <div class="value" style="font-size: 14px;">${data.risk_summary?.most_vulnerable_scenario}</div>
        </div>
        <div class="metric-card">
          <div class="label">Max Decline</div>
          <div class="value negative">-${data.risk_summary?.max_portfolio_decline_pct}%</div>
        </div>
        <div class="metric-card">
          <div class="label">Properties at Risk</div>
          <div class="value">${data.scenario_results?.[0]?.portfolio_impact?.properties_at_risk || 0}</div>
        </div>
      </div>
    </div>
  `
  
  // Scenario results table
  if (data.scenario_results) {
    content += `
      <div class="section">
        <h3 class="section-title">Scenario Results</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Portfolio Value</th>
              <th>Change (%)</th>
              <th>Change ($)</th>
              <th>Avg IRR Impact</th>
              <th>Properties at Risk</th>
            </tr>
          </thead>
          <tbody>
            ${data.scenario_results.map((scenario: any) => `
              <tr>
                <td>${scenario.scenario.name}</td>
                <td>$${scenario.portfolio_impact.total_scenario_value.toLocaleString()}</td>
                <td class="${scenario.portfolio_impact.portfolio_change_pct >= 0 ? 'positive' : 'negative'}">
                  ${scenario.portfolio_impact.portfolio_change_pct.toFixed(1)}%
                </td>
                <td class="${scenario.portfolio_impact.portfolio_change_dollars >= 0 ? 'positive' : 'negative'}">
                  $${scenario.portfolio_impact.portfolio_change_dollars.toLocaleString()}
                </td>
                <td>${scenario.portfolio_impact.avg_irr_impact_bps}bps</td>
                <td>${scenario.portfolio_impact.properties_at_risk}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `
  }
  
  // Risk summary
  if (data.risk_summary?.key_risks?.length > 0) {
    content += `
      <div class="section">
        <h3 class="section-title">Key Risks Identified</h3>
        <ul style="margin-left: 20px;">
          ${data.risk_summary.key_risks.map((risk: string) => `<li style="margin-bottom: 8px;">${risk}</li>`).join('')}
        </ul>
      </div>
    `
  }
  
  // Recommendations
  if (data.risk_summary?.recommendations?.length > 0) {
    content += `
      <div class="section">
        <h3 class="section-title">Recommendations</h3>
        <ol style="margin-left: 20px;">
          ${data.risk_summary.recommendations.map((rec: string) => `<li style="margin-bottom: 8px;">${rec}</li>`).join('')}
        </ol>
      </div>
    `
  }
  
  return content
}

function generateAccuracyContent(data: any, template: string, exportOptions: any): string {
  return `
    <div class="section">
      <h3 class="section-title">Accuracy Metrics</h3>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="label">Mean Accuracy</div>
          <div class="value">${data.mean_accuracy_pct?.toFixed(1) || 'N/A'}%</div>
        </div>
        <div class="metric-card">
          <div class="label">Median Error</div>
          <div class="value">${data.median_error_pct?.toFixed(1) || 'N/A'}%</div>
        </div>
        <div class="metric-card">
          <div class="label">Predictions Tested</div>
          <div class="value">${data.total_predictions || 'N/A'}</div>
        </div>
      </div>
    </div>
    
    <div class="section">
      <h3 class="section-title">Performance by Market</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Market</th>
            <th>Predictions</th>
            <th>Mean Error</th>
            <th>Accuracy</th>
            <th>Grade</th>
          </tr>
        </thead>
        <tbody>
          ${(data.market_performance || []).map((market: any) => `
            <tr>
              <td>${market.market_name}</td>
              <td>${market.prediction_count}</td>
              <td>${market.mean_error_pct?.toFixed(1)}%</td>
              <td>${market.accuracy_pct?.toFixed(1)}%</td>
              <td>${market.grade}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `
}

function generateProvenanceSection(provenance: any): string {
  return `
    <div class="section">
      <h3 class="section-title">Data Provenance</h3>
      <div class="provenance-box">
        <h4>Data Sources & Freshness</h4>
        <table class="data-table">
          <thead>
            <tr><th>Source</th><th>Provider</th><th>As Of</th><th>Cache Status</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>Macro Data</td>
              <td>${provenance.macro?.source || 'N/A'}</td>
              <td>${provenance.macro?.as_of || 'N/A'}</td>
              <td>${provenance.macro?.from_cache ? 'Cached' : 'Live'}</td>
            </tr>
            <tr>
              <td>Market Fundamentals</td>
              <td>${provenance.fundamentals?.source || 'N/A'}</td>
              <td>${provenance.fundamentals?.as_of || 'N/A'}</td>
              <td>Live</td>
            </tr>
            <tr>
              <td>Comparable Sales</td>
              <td>${provenance.comps?.source || 'N/A'}</td>
              <td>${provenance.comps?.as_of || 'N/A'}</td>
              <td>Live</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `
}

function generateMethodologySection(reportType: string): string {
  const methodologies = {
    valuation: `
      <div class="methodology">
        <h4>Valuation Methodology</h4>
        <p><strong>Income Approach:</strong> Net Operating Income (NOI) divided by market-derived capitalization rate, adjusted for current macro conditions.</p>
        <p><strong>Sales Comparison:</strong> Analysis of comparable sales transactions adjusted for size, location, and timing differences.</p>
        <p><strong>Dual-Engine Validation:</strong> Both approaches are weighted based on data quality and market conditions to produce final valuation.</p>
        <p><strong>Risk Adjustments:</strong> Cap rates adjusted for Federal Reserve policy, credit spreads, and market-specific risk factors.</p>
      </div>
    `,
    portfolio: `
      <div class="methodology">
        <h4>Portfolio Analytics Methodology</h4>
        <p><strong>Individual Valuations:</strong> Each property valued using dual-engine approach (Income + Sales Comparison).</p>
        <p><strong>Portfolio Metrics:</strong> Value-weighted averages and risk-adjusted returns calculated across entire portfolio.</p>
        <p><strong>Diversification Scoring:</strong> Based on geographic and asset-type distribution across portfolio holdings.</p>
        <p><strong>Market Timing Score (MTS):</strong> 0-100 scale considering interest rates, rent growth, vacancy, and cap rate spreads.</p>
      </div>
    `
  }
  
  return methodologies[reportType as keyof typeof methodologies] || ''
}

function generateScenarioSummaryTable(scenarioAnalysis: any): string {
  return `
    <div class="section">
      <h3 class="section-title">Scenario Analysis Summary</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Portfolio Value</th>
            <th>Change (%)</th>
            <th>Properties at Risk</th>
          </tr>
        </thead>
        <tbody>
          ${Object.entries(scenarioAnalysis).map(([name, result]: [string, any]) => `
            <tr>
              <td>${name}</td>
              <td>$${result.portfolio_value?.toLocaleString()}</td>
              <td class="${result.value_change_pct >= 0 ? 'positive' : 'negative'}">
                ${result.value_change_pct?.toFixed(1)}%
              </td>
              <td>${result.properties_at_risk}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `
}

function generateFooter(exportOptions: any): string {
  const disclaimer = exportOptions.include_disclaimers ? `
    <div class="disclaimer">
      <strong>IMPORTANT DISCLAIMER:</strong> This valuation analysis is for informational purposes only and should not be considered as investment advice. 
      Property valuations are estimates based on available market data and mathematical models. Actual market values may vary significantly. 
      Past performance does not guarantee future results. Consult with qualified professionals before making investment decisions.
    </div>
  ` : ''
  
  const watermark = exportOptions.watermark ? `<div class="watermark">${exportOptions.watermark}</div>` : ''
  
  return `
    ${disclaimer}
    ${watermark}
    <div class="footer">
      <p>Generated by CapSight Analytics Platform | © ${new Date().getFullYear()} | Confidential and Proprietary</p>
      <p>For questions about this report, please contact your CapSight representative.</p>
    </div>
  `
}

function generateTitle(reportType: string, data: any): string {
  const titles = {
    valuation: data.property?.address ? `Property Valuation: ${data.property.address}` : 'Property Valuation Report',
    portfolio: `Portfolio Analysis: ${data.portfolio_id || 'Portfolio Report'}`,
    scenario: `Scenario Analysis: ${data.total_properties || 'Portfolio'} Properties`,
    accuracy: 'Model Accuracy & Performance Report'
  }
  
  return titles[reportType as keyof typeof titles] || 'Investment Analysis Report'
}

function generateSubtitle(reportType: string, data: any): string {
  const date = new Date().toLocaleDateString()
  
  const subtitles = {
    valuation: `${data.property?.market?.toUpperCase() || 'Market'} • ${data.property?.building_sf?.toLocaleString() || '0'} SF • ${date}`,
    portfolio: `${data.total_properties || 0} Properties • $${data.total_value?.toLocaleString() || '0'} Total Value • ${date}`,
    scenario: `${data.total_scenarios || 0} Scenarios • Risk Grade: ${data.risk_summary?.stress_test_grade || 'N/A'} • ${date}`,
    accuracy: `Model Performance Analysis • ${date}`
  }
  
  return subtitles[reportType as keyof typeof subtitles] || `Analysis Report • ${date}`
}

function generateReportMetadata(reportType: string, data: any, branding: any) {
  return {
    title: generateTitle(reportType, data),
    subtitle: generateSubtitle(reportType, data),
    author: branding.company_name || 'CapSight Analytics',
    subject: `${reportType} analysis generated by CapSight platform`
  }
}

// ===== PDF GENERATION =====

async function generatePDF(htmlContent: string, template: string): Promise<Buffer> {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  })
  
  try {
    const page = await browser.newPage()
    await page.setContent(htmlContent, { waitUntil: 'networkidle0' })
    
    const pdfOptions: any = {
      format: 'A4',
      printBackground: true,
      margin: {
        top: '0.5in',
        right: '0.5in',
        bottom: '0.5in',
        left: '0.5in'
      }
    }
    
    // Template-specific options
    if (template === 'executive') {
      pdfOptions.landscape = true
    }
    
    const pdfBuffer = await page.pdf(pdfOptions)
    return Buffer.from(pdfBuffer)
    
  } finally {
    await browser.close()
  }
}

async function estimatePageCount(pdfBuffer: Buffer): Promise<number> {
  // Simple estimation based on file size
  // In production, you'd use a proper PDF parser
  const sizeKB = pdfBuffer.length / 1024
  return Math.max(1, Math.ceil(sizeKB / 50)) // Rough estimate: 50KB per page
}
