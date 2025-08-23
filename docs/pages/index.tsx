import Head from 'next/head'
import Link from 'next/link'

export default function Home() {
  return (
    <>
      <Head>
        <title>CapSight Documentation</title>
        <meta name="description" content="CapSight industrial CRE valuation platform documentation" />
      </Head>

      <div>
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            CapSight Documentation
          </h1>
          <p className="text-xl text-gray-600">
            Industrial commercial real estate valuation platform with bulletproof accuracy and enterprise-grade reliability.
          </p>
        </div>

        {/* Quick Start */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-6 mb-8">
          <h2 className="text-lg font-semibold text-blue-800 mb-2">Quick Start</h2>
          <p className="text-blue-700 mb-4">
            Get started with CapSight API in under 5 minutes.
          </p>
          <div className="bg-blue-100 rounded-md p-4 text-sm font-mono text-blue-900">
            curl -X POST https://api.capsight.com/v1/value \<br />
            &nbsp;&nbsp;-H "Content-Type: application/json" \<br />
            &nbsp;&nbsp;-d {`'{"market_slug": "dfw", "noi_annual": 1500000, "building_sf": 100000}'`}
          </div>
        </div>

        {/* Documentation Sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              <Link href="/methodology" className="hover:text-primary-600">
                Valuation Methodology
              </Link>
            </h3>
            <p className="text-gray-600 mb-4">
              Comprehensive overview of our robust estimator, conformal prediction, and fallback logic.
            </p>
            <div className="text-sm text-gray-500">
              ✓ Weighted median cap rates<br />
              ✓ Conformal prediction intervals<br />
              ✓ Quality gates and validation
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              <Link href="/api-reference" className="hover:text-primary-600">
                API Reference
              </Link>
            </h3>
            <p className="text-gray-600 mb-4">
              Complete API documentation with interactive examples and OpenAPI specification.
            </p>
            <div className="text-sm text-gray-500">
              ✓ REST endpoints<br />
              ✓ Request/response schemas<br />
              ✓ Rate limiting & auth
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              <Link href="/operations" className="hover:text-primary-600">
                Operations Playbook
              </Link>
            </h3>
            <p className="text-gray-600 mb-4">
              Production deployment, monitoring, and incident response procedures.
            </p>
            <div className="text-sm text-gray-500">
              ✓ Deployment automation<br />
              ✓ Monitoring & alerting<br />
              ✓ Incident response
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              <Link href="/accuracy" className="hover:text-primary-600">
                Accuracy & SLA
              </Link>
            </h3>
            <p className="text-gray-600 mb-4">
              KPI definitions, SLA commitments, and accuracy monitoring framework.
            </p>
            <div className="text-sm text-gray-500">
              ✓ MAPE ≤ 10% target<br />
              ✓ Coverage calibration<br />
              ✓ Nightly backtesting
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              <Link href="/changelog" className="hover:text-primary-600">
                Changelog
              </Link>
            </h3>
            <p className="text-gray-600 mb-4">
              Version history, estimator updates, and breaking changes.
            </p>
            <div className="text-sm text-gray-500">
              ✓ Semantic versioning<br />
              ✓ Migration guides<br />
              ✓ Feature timeline
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              <a href="/legal/privacy" className="hover:text-primary-600">
                Legal & Compliance
              </a>
            </h3>
            <p className="text-gray-600 mb-4">
              Privacy policy, terms of use, and regulatory compliance information.
            </p>
            <div className="text-sm text-gray-500">
              ✓ Data privacy<br />
              ✓ Non-USPAP disclosure<br />
              ✓ Usage terms
            </div>
          </div>
        </div>

        {/* Market Coverage */}
        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Market Coverage</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { code: 'DFW', name: 'Dallas-Fort Worth', properties: '2,500+' },
              { code: 'IE', name: 'Inland Empire', properties: '1,800+' },
              { code: 'ATL', name: 'Atlanta', properties: '2,200+' },
              { code: 'PHX', name: 'Phoenix', properties: '1,600+' },
              { code: 'SAV', name: 'Savannah', properties: '800+' },
            ].map((market) => (
              <div key={market.code} className="text-center">
                <div className="text-lg font-bold text-primary-600">{market.code}</div>
                <div className="text-sm text-gray-900">{market.name}</div>
                <div className="text-xs text-gray-500">{market.properties} properties</div>
              </div>
            ))}
          </div>
        </div>

        {/* Support */}
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-6">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">Need Help?</h3>
          <p className="text-yellow-700 mb-4">
            Contact our support team or file an issue for technical questions.
          </p>
          <div className="flex space-x-4">
            <a
              href="mailto:support@capsight.com"
              className="inline-flex items-center px-4 py-2 bg-yellow-100 text-yellow-800 rounded-md hover:bg-yellow-200 transition-colors"
            >
              Email Support
            </a>
            <a
              href="https://github.com/capsight/issues"
              className="inline-flex items-center px-4 py-2 bg-yellow-100 text-yellow-800 rounded-md hover:bg-yellow-200 transition-colors"
            >
              GitHub Issues
            </a>
          </div>
        </div>
      </div>
    </>
  )
}
