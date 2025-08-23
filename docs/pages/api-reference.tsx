import Head from 'next/head'
import { useState } from 'react'

export default function APIReference() {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <>
      <Head>
        <title>API Reference - CapSight Docs</title>
        <meta name="description" content="Complete API reference for CapSight valuation endpoints" />
      </Head>

      <div>
        <h1>API Reference</h1>
        
        <div className="bg-blue-50 border-l-4 border-blue-400 p-6 my-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">Base URL</h3>
          <div className="font-mono text-blue-700">
            https://app.capsight.com/api
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'overview', name: 'Overview' },
              { id: 'interactive', name: 'Interactive Docs' },
              { id: 'examples', name: 'Examples' },
              { id: 'errors', name: 'Error Codes' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="prose prose-lg max-w-none">
            <h2>Quick Start</h2>
            <p>
              The CapSight API provides industrial CRE valuations with confidence intervals.
              All requests require valid market and property data.
            </p>

            <h3>Authentication</h3>
            <p>Currently no authentication required for public endpoints. Rate limiting applies:</p>
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
              <ul className="text-yellow-700">
                <li>100 requests per minute per IP</li>
                <li>1000 requests per day per IP</li>
                <li>Enterprise plans available for higher limits</li>
              </ul>
            </div>

            <h3>Supported Markets</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
              {[
                { code: 'dfw', name: 'Dallas-Fort Worth', coverage: '2,500+ properties' },
                { code: 'ie', name: 'Inland Empire', coverage: '1,800+ properties' },
                { code: 'atl', name: 'Atlanta', coverage: '2,200+ properties' },
                { code: 'phx', name: 'Phoenix', coverage: '1,600+ properties' },
                { code: 'sav', name: 'Savannah', coverage: '800+ properties' },
              ].map((market) => (
                <div key={market.code} className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="font-semibold text-gray-900">{market.name}</div>
                  <div className="text-sm text-gray-500">Code: <code>{market.code}</code></div>
                  <div className="text-sm text-gray-500">{market.coverage}</div>
                </div>
              ))}
            </div>

            <h3>Request Format</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`POST /api/value
Content-Type: application/json

{
  "market_slug": "dfw",
  "noi_annual": 1500000,
  "building_sf": 100000,
  "year_built": 2015        // optional
}`}</code></pre>
            </div>

            <h3>Response Format</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`{
  "valuation_usd": 25000000,
  "confidence_interval": [23750000, 26250000],
  "cap_rate_pct": 6.0,
  "price_per_sf_usd": 250,
  "methodology": "weighted_median_v1.0",
  "comp_count": 12,
  "quality_score": "high",
  "top_comps": [...],
  "warnings": []
}`}</code></pre>
            </div>
          </div>
        )}

        {activeTab === 'interactive' && (
          <div>
            <div className="mb-4">
              <p className="text-gray-600">
                Interactive API documentation powered by OpenAPI specification.
              </p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-blue-800 font-semibold mb-2">OpenAPI Specification</h3>
              <p className="text-blue-700 mb-4">
                Download or view the complete OpenAPI 3.0 specification for integration with API tools.
              </p>
              <div className="flex space-x-4">
                <a
                  href="/openapi.yaml"
                  className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-800 rounded-md hover:bg-blue-200 transition-colors"
                >
                  Download OpenAPI YAML
                </a>
                <a
                  href="https://editor.swagger.io/?url=https://app.capsight.com/openapi.yaml"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-800 rounded-md hover:bg-blue-200 transition-colors"
                >
                  Open in Swagger Editor
                </a>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'examples' && (
          <div className="prose prose-lg max-w-none">
            <h2>Code Examples</h2>

            <h3>cURL</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`# Basic valuation request
curl -X POST https://app.capsight.com/api/value \\
  -H "Content-Type: application/json" \\
  -d '{
    "market_slug": "dfw",
    "noi_annual": 1500000,
    "building_sf": 100000
  }'

# With optional parameters
curl -X POST https://app.capsight.com/api/value \\
  -H "Content-Type: application/json" \\
  -d '{
    "market_slug": "ie",
    "noi_annual": 2200000,
    "building_sf": 150000,
    "year_built": 2018,
    "property_type": "warehouse"
  }'`}</code></pre>
            </div>

            <h3>JavaScript / Node.js</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`// Using fetch API
const response = await fetch('https://app.capsight.com/api/value', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    market_slug: 'dfw',
    noi_annual: 1500000,
    building_sf: 100000
  })
});

const valuation = await response.json();
console.log('Valuation:', valuation.valuation_usd);
console.log('Confidence:', valuation.confidence_interval);

// Using axios
const axios = require('axios');

const valuation = await axios.post('https://app.capsight.com/api/value', {
  market_slug: 'atl',
  noi_annual: 1200000,
  building_sf: 80000,
  year_built: 2020
});

console.log('Cap Rate:', valuation.data.cap_rate_pct + '%');`}</code></pre>
            </div>

            <h3>Python</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`import requests

# Basic request
response = requests.post('https://app.capsight.com/api/value', json={
    'market_slug': 'phx',
    'noi_annual': 1800000,
    'building_sf': 120000
})

valuation = response.json()
print(f"Valuation: $`}{`{valuation['valuation_usd']:,.0f}")
print(f"Price/SF: $`}{`{valuation['price_per_sf_usd']:.0f}")
print(f"Cap Rate: `}{`{valuation['cap_rate_pct']:.1f}%")

# With error handling
try:
    response = requests.post('https://app.capsight.com/api/value', 
        json=payload, timeout=10)
    response.raise_for_status()
    
    result = response.json()
    if result.get('warnings'):
        print("Warnings:", result['warnings'])
        
except requests.exceptions.RequestException as e:
    print(f"API Error: `}{`{e}")`}</code></pre>
            </div>

            <h3>Response Examples</h3>
            
            <h4>Successful Valuation</h4>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`{
  "valuation_usd": 18750000,
  "confidence_interval": [17500000, 20000000],
  "cap_rate_pct": 6.4,
  "price_per_sf_usd": 187,
  "methodology": "weighted_median_v1.0",
  "comp_count": 15,
  "quality_score": "high",
  "market_slug": "dfw",
  "top_comps": [
    {
      "address_masked": "****** Industrial Blvd, Dallas TX",
      "sale_date": "2024-11-15",
      "building_sf": 95000,
      "sale_price_usd": 17800000,
      "cap_rate_pct": 6.2,
      "similarity_score": 0.89
    }
  ],
  "data_quality": {
    "median_age_months": 8,
    "verification_rate": 0.87,
    "sample_size": 15
  },
  "warnings": []
}`}</code></pre>
            </div>

            <h4>Low Sample Size Warning</h4>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`{
  "valuation_usd": 22000000,
  "confidence_interval": [19500000, 25000000],
  "cap_rate_pct": 5.8,
  "price_per_sf_usd": 220,
  "methodology": "market_fallback_v1.0",
  "comp_count": 5,
  "quality_score": "low",
  "warnings": [
    {
      "type": "low_sample_size",
      "message": "Only 5 comparable sales found. Results may be less reliable.",
      "recommendation": "Consider expanding search criteria or market area."
    }
  ]
}`}</code></pre>
            </div>
          </div>
        )}

        {activeTab === 'errors' && (
          <div className="prose prose-lg max-w-none">
            <h2>Error Codes</h2>
            
            <div className="space-y-4">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-red-800 font-semibold">400 Bad Request</h3>
                <p className="text-red-700">Invalid request parameters</p>
                <div className="mt-2 text-sm font-mono bg-red-100 p-2 rounded">
                  {`{
  "error": "validation_failed",
  "message": "Invalid market_slug: 'xyz'. Must be one of: dfw, ie, atl, phx, sav",
  "details": {
    "field": "market_slug",
    "value": "xyz",
    "allowed": ["dfw", "ie", "atl", "phx", "sav"]
  }
}`}
                </div>
              </div>

              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <h3 className="text-orange-800 font-semibold">422 Unprocessable Entity</h3>
                <p className="text-orange-700">Valid format but impossible to process</p>
                <div className="mt-2 text-sm font-mono bg-orange-100 p-2 rounded">
                  {`{
  "error": "insufficient_data",
  "message": "No comparable sales found for the specified criteria",
  "details": {
    "market": "sav",
    "filters_applied": {
      "building_sf": 100000,
      "max_distance_miles": 25
    },
    "suggestion": "Try expanding search criteria or different market"
  }
}`}
                </div>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-red-800 font-semibold">429 Too Many Requests</h3>
                <p className="text-red-700">Rate limit exceeded</p>
                <div className="mt-2 text-sm font-mono bg-red-100 p-2 rounded">
                  {`{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded: 100 requests per minute",
  "retry_after": 45,
  "details": {
    "limit": 100,
    "window": "1 minute",
    "reset_time": "2025-08-23T15:30:00Z"
  }
}`}
                </div>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-red-800 font-semibold">500 Internal Server Error</h3>
                <p className="text-red-700">Unexpected server error</p>
                <div className="mt-2 text-sm font-mono bg-red-100 p-2 rounded">
                  {`{
  "error": "internal_error",
  "message": "An unexpected error occurred while processing your request",
  "request_id": "req_abc123def456",
  "support": "Contact support@capsight.com with request ID for assistance"
}`}
                </div>
              </div>
            </div>

            <h3>Common Validation Errors</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full border border-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left font-semibold">Field</th>
                    <th className="px-4 py-2 text-left font-semibold">Error</th>
                    <th className="px-4 py-2 text-left font-semibold">Solution</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t">
                    <td className="px-4 py-2 font-mono text-sm">market_slug</td>
                    <td className="px-4 py-2 text-sm">Invalid market code</td>
                    <td className="px-4 py-2 text-sm">Use: dfw, ie, atl, phx, sav</td>
                  </tr>
                  <tr className="border-t">
                    <td className="px-4 py-2 font-mono text-sm">noi_annual</td>
                    <td className="px-4 py-2 text-sm">Out of range (0-50M)</td>
                    <td className="px-4 py-2 text-sm">Provide realistic NOI</td>
                  </tr>
                  <tr className="border-t">
                    <td className="px-4 py-2 font-mono text-sm">building_sf</td>
                    <td className="px-4 py-2 text-sm">Too small (&lt;10K) or large (&gt;2M)</td>
                    <td className="px-4 py-2 text-sm">Industrial buildings 10K-2M SF</td>
                  </tr>
                  <tr className="border-t">
                    <td className="px-4 py-2 font-mono text-sm">year_built</td>
                    <td className="px-4 py-2 text-sm">Invalid year (1900-2030)</td>
                    <td className="px-4 py-2 text-sm">Reasonable construction year</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mt-6">
              <h4 className="font-semibold text-blue-800">Support</h4>
              <p className="text-blue-700">
                For API support, include the <code>request_id</code> from error responses when contacting{' '}
                <a href="mailto:support@capsight.com" className="underline">support@capsight.com</a>.
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
