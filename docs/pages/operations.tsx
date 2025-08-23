import Head from 'next/head'

export default function Operations() {
  return (
    <>
      <Head>
        <title>Operations Playbook - CapSight Docs</title>
        <meta name="description" content="CapSight operations, monitoring, and incident response procedures" />
      </Head>

      <div className="prose prose-lg max-w-none">
        <h1>Operations Playbook</h1>
        
        <div className="bg-blue-50 border-l-4 border-blue-400 p-6 my-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">Overview</h3>
          <p className="text-blue-700">
            This playbook covers monitoring and maintaining the CapSight valuation system with 
            robust estimators, conformal prediction, and automated accuracy tracking.
          </p>
        </div>

        <h2>System Architecture</h2>
        
        <h3>Core Components</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Robust Valuation API</h4>
            <p className="text-gray-600 text-sm mt-2">
              <code>pages/api/value.ts</code>
            </p>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• Weighted median estimator</li>
              <li>• Dynamic confidence bands</li>
              <li>• Automatic fallback rules</li>
              <li>• Full auditability</li>
            </ul>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Data Validator</h4>
            <p className="text-gray-600 text-sm mt-2">
              <code>validate_csv.py</code>
            </p>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• Geofence validation</li>
              <li>• NOI consistency checks</li>
              <li>• Review queue flagging</li>
              <li>• Size/age categorization</li>
            </ul>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Nightly Accuracy Monitor</h4>
            <p className="text-gray-600 text-sm mt-2">
              <code>nightly_accuracy.py</code>
            </p>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• Automated backtesting</li>
              <li>• SLA compliance tracking</li>
              <li>• Bias detection</li>
              <li>• Automated alerting</li>
            </ul>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Database Schema</h4>
            <p className="text-gray-600 text-sm mt-2">
              Core tables and views
            </p>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• <code>accuracy_metrics</code></li>
              <li>• <code>comp_review_queue</code></li>
              <li>• <code>v_comps_trimmed</code></li>
              <li>• <code>latest_accuracy</code></li>
            </ul>
          </div>
        </div>

        <h2>Daily Operations</h2>

        <h3>Morning Health Check (9 AM)</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-4">
          <pre className="text-sm"><code>{`-- Check overall system health
SELECT * FROM v_system_health ORDER BY metric;

-- Verify nightly accuracy run completed
SELECT market_slug, last_updated, mape, rmse_bps, coverage80
FROM latest_accuracy 
WHERE last_updated >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY market_slug;`}</code></pre>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h4 className="font-semibold text-green-800">Expected Results</h4>
            <ul className="text-green-700 text-sm mt-2">
              <li>• All 5 markets updated from last night</li>
              <li>• SLA passing rate >80% across markets</li>
              <li>• Review queue <20 pending items</li>
            </ul>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h4 className="font-semibold text-red-800">Red Flags</h4>
            <ul className="text-red-700 text-sm mt-2">
              <li>• Any market missing from nightly update</li>
              <li>• MAPE >15% or RMSE >75bps consistently</li>
              <li>• Coverage <75% or >85% (miscalibrated)</li>
            </ul>
          </div>
        </div>

        <h3>Weekly Performance Review (Monday 10 AM)</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-4">
          <pre className="text-sm"><code>{`-- Weekly accuracy trend
SELECT 
    market_slug,
    AVG(mape) as avg_mape,
    AVG(rmse_bps) as avg_rmse,
    AVG(coverage80) as avg_coverage,
    COUNT(*) as data_points
FROM accuracy_metrics 
WHERE last_updated >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY market_slug
ORDER BY avg_mape DESC;

-- Data quality issues
SELECT 
    market_slug,
    reason,
    COUNT(*) as count,
    MIN(created_at) as first_seen,
    MAX(created_at) as last_seen
FROM comp_review_queue 
WHERE status = 'pending'
GROUP BY market_slug, reason
ORDER BY count DESC;`}</code></pre>
        </div>

        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <h4 className="font-semibold text-blue-800">Weekly Actions</h4>
          <ul className="text-blue-700">
            <li>Review markets with degrading MAPE trends</li>
            <li>Process high-priority review queue items</li>
            <li>Update methodology documentation if needed</li>
          </ul>
        </div>

        <h2>SLA Monitoring</h2>

        <h3>Target SLAs</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 my-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-800">≤10%</div>
            <div className="text-sm text-green-700">MAPE Target</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-800">≤50bps</div>
            <div className="text-sm text-green-700">RMSE Target</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-800">78-82%</div>
            <div className="text-sm text-green-700">Coverage Range</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-800">≤24h</div>
            <div className="text-sm text-blue-700">Data Freshness</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-800">&lt;2s</div>
            <div className="text-sm text-blue-700">API Response (95th)</div>
          </div>
        </div>

        <h3>SLA Violation Response</h3>
        <div className="space-y-4">
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
            <h4 className="font-semibold text-yellow-800">Level 1: Minor Violation (1-2 markets affected)</h4>
            <ul className="text-yellow-700 mt-2">
              <li><strong>Response Time:</strong> 4 hours</li>
              <li><strong>Actions:</strong> Investigate root cause, review recent data changes</li>
              <li><strong>Escalation:</strong> If not resolved in 24 hours</li>
            </ul>
          </div>

          <div className="bg-orange-50 border-l-4 border-orange-400 p-4">
            <h4 className="font-semibold text-orange-800">Level 2: Major Violation (3+ markets or >20% MAPE)</h4>
            <ul className="text-orange-700 mt-2">
              <li><strong>Response Time:</strong> 1 hour</li>
              <li><strong>Actions:</strong> Emergency troubleshooting, disable affected markets if needed</li>
              <li><strong>Escalation:</strong> Immediate management notification</li>
            </ul>
          </div>

          <div className="bg-red-50 border-l-4 border-red-400 p-4">
            <h4 className="font-semibold text-red-800">Level 3: Critical Violation (System-wide failure)</h4>
            <ul className="text-red-700 mt-2">
              <li><strong>Response Time:</strong> 15 minutes</li>
              <li><strong>Actions:</strong> Emergency rollback, activate incident response</li>
              <li><strong>Escalation:</strong> All-hands incident bridge</li>
            </ul>
          </div>
        </div>

        <h2>Deployment Procedures</h2>

        <h3>Pre-deployment Checklist</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <pre className="text-sm"><code>{`# Run enhanced deployment script
./deploy-enhanced.sh

# Verify pre-flight checks pass:
# ✅ Data validation (all markets)
# ✅ Dry-run backtest (18m window)
# ✅ SLA compliance check
# ✅ E2E + unit tests
# ✅ Market data seeding (staging)`}</code></pre>
        </div>

        <h3>Post-deployment Validation</h3>
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-800">Immediate Validation (0-15 minutes)</h4>
            <ul className="text-blue-700">
              <li>API health check across all markets</li>
              <li>Sample valuations for each market</li>
              <li>Database connectivity verification</li>
            </ul>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-800">Extended Validation (1-4 hours)</h4>
            <ul className="text-blue-700">
              <li>Run nightly accuracy check manually</li>
              <li>Verify SLA metrics remain stable</li>
              <li>Monitor error rates and response times</li>
            </ul>
          </div>
        </div>

        <h2>Incident Response</h2>

        <h3>Common Issues & Solutions</h3>
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">High MAPE (>15%)</h4>
            <div className="text-sm text-gray-600 mt-2">
              <strong>Symptoms:</strong> Valuations significantly off from expected
            </div>
            <div className="text-sm text-gray-600 mt-1">
              <strong>Causes:</strong> Data quality issues, market shifts, methodology bugs
            </div>
            <div className="text-sm text-gray-700 mt-2">
              <strong>Response:</strong>
              <ol className="list-decimal list-inside ml-4 mt-1">
                <li>Check recent data uploads for outliers</li>
                <li>Review comp filtering and weighting logic</li>
                <li>Compare against manual valuations</li>
                <li>Consider temporary market disable if severe</li>
              </ol>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Coverage Miscalibration (<75% or >85%)</h4>
            <div className="text-sm text-gray-600 mt-2">
              <strong>Symptoms:</strong> Confidence intervals too wide/narrow
            </div>
            <div className="text-sm text-gray-600 mt-1">
              <strong>Causes:</strong> Market volatility changes, conformal prediction drift
            </div>
            <div className="text-sm text-gray-700 mt-2">
              <strong>Response:</strong>
              <ol className="list-decimal list-inside ml-4 mt-1">
                <li>Recalibrate conformal quantiles</li>
                <li>Extend backtest window if needed</li>
                <li>Review market-specific factors</li>
                <li>Update fallback band widths</li>
              </ol>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">API Response Time Degradation</h4>
            <div className="text-sm text-gray-600 mt-2">
              <strong>Symptoms:</strong> >2s response times, timeouts
            </div>
            <div className="text-sm text-gray-600 mt-1">
              <strong>Causes:</strong> Database performance, increased load, inefficient queries
            </div>
            <div className="text-sm text-gray-700 mt-2">
              <strong>Response:</strong>
              <ol className="list-decimal list-inside ml-4 mt-1">
                <li>Check database query performance</li>
                <li>Review index usage and query plans</li>
                <li>Scale database resources if needed</li>
                <li>Enable query result caching</li>
              </ol>
            </div>
          </div>
        </div>

        <h2>Monitoring & Alerting</h2>

        <h3>Key Metrics Dashboard</h3>
        <p>Monitor these metrics in real-time via your observability platform:</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Accuracy Metrics</h4>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• MAPE by market (daily)</li>
              <li>• RMSE by market (daily)</li>
              <li>• Coverage calibration (weekly)</li>
              <li>• Sample size adequacy</li>
            </ul>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">System Performance</h4>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• API response times (p95, p99)</li>
              <li>• Error rates by endpoint</li>
              <li>• Database connection health</li>
              <li>• Memory and CPU utilization</li>
            </ul>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Data Quality</h4>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• Review queue size</li>
              <li>• Data freshness by market</li>
              <li>• Verification rate trends</li>
              <li>• Outlier detection rate</li>
            </ul>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Business Metrics</h4>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• API usage by market</li>
              <li>• User retention rates</li>
              <li>• Feature adoption</li>
              <li>• Feedback sentiment</li>
            </ul>
          </div>
        </div>

        <h3>Alert Thresholds</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full border border-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left font-semibold">Metric</th>
                <th className="px-4 py-2 text-left font-semibold">Warning</th>
                <th className="px-4 py-2 text-left font-semibold">Critical</th>
                <th className="px-4 py-2 text-left font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="px-4 py-2 font-mono text-sm">MAPE</td>
                <td className="px-4 py-2 text-sm">12%</td>
                <td className="px-4 py-2 text-sm">15%</td>
                <td className="px-4 py-2 text-sm">Investigate data quality</td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-2 font-mono text-sm">RMSE</td>
                <td className="px-4 py-2 text-sm">60 bps</td>
                <td className="px-4 py-2 text-sm">75 bps</td>
                <td className="px-4 py-2 text-sm">Review methodology</td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-2 font-mono text-sm">Coverage</td>
                <td className="px-4 py-2 text-sm">&lt;76% or >84%</td>
                <td className="px-4 py-2 text-sm">&lt;74% or >86%</td>
                <td className="px-4 py-2 text-sm">Recalibrate bands</td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-2 font-mono text-sm">API Response</td>
                <td className="px-4 py-2 text-sm">2.5s (p95)</td>
                <td className="px-4 py-2 text-sm">5s (p95)</td>
                <td className="px-4 py-2 text-sm">Scale resources</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8">
          <p className="text-gray-700 italic">
            <strong>Remember:</strong> This playbook should be updated as the system evolves. 
            Regular post-incident reviews help improve our response procedures.
          </p>
        </div>
      </div>
    </>
  )
}
