import Head from 'next/head'

export default function Changelog() {
  return (
    <>
      <Head>
        <title>Changelog - CapSight Docs</title>
        <meta name="description" content="CapSight version history and estimator updates" />
      </Head>

      <div className="prose prose-lg max-w-none">
        <h1>Changelog</h1>
        
        <div className="bg-blue-50 border-l-4 border-blue-400 p-6 my-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">Versioning Policy</h3>
          <p className="text-blue-700">
            CapSight uses semantic versioning for estimator methodology. Major version changes 
            indicate fundamental methodology updates, minor versions reflect parameter adjustments, 
            and patches are bug fixes.
          </p>
        </div>

        <div className="space-y-8">
          {/* Version 1.0 */}
          <div className="border-l-4 border-green-500 pl-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-2xl font-bold text-green-800">Version 1.0.0</h2>
              <div className="flex space-x-2">
                <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded">
                  CURRENT
                </span>
                <span className="text-sm text-gray-500">August 23, 2025</span>
              </div>
            </div>
            
            <div className="bg-white border border-gray-200 rounded-lg p-6 mb-4">
              <h3 className="font-semibold text-gray-900 mb-3">🚀 Major Release: Production Launch</h3>
              <p className="text-gray-700 mb-4">
                First production release of CapSight with robust methodology, conformal prediction, 
                and automated accuracy monitoring across 5 pilot markets.
              </p>

              <h4 className="font-semibold text-gray-900 mb-2">✨ New Features</h4>
              <ul className="text-gray-700 space-y-1 mb-4">
                <li>• <strong>Weighted Median Estimator:</strong> Robust to outliers with similarity kernels</li>
                <li>• <strong>Conformal Prediction:</strong> Empirically calibrated confidence intervals</li>
                <li>• <strong>Multi-factor Weighting:</strong> Recency, distance, size, and age factors</li>
                <li>• <strong>Automatic Fallback Rules:</strong> Graceful degradation for edge cases</li>
                <li>• <strong>Time Normalization:</strong> Market trend adjustments using Theil-Sen estimator</li>
                <li>• <strong>Nightly Backtesting:</strong> Automated SLA monitoring and alerting</li>
                <li>• <strong>Audit Trail:</strong> Full transparency with masked comparable details</li>
              </ul>

              <h4 className="font-semibold text-gray-900 mb-2">📊 SLA Targets</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
                  <div className="font-bold text-green-800">≤10%</div>
                  <div className="text-xs text-green-600">MAPE</div>
                </div>
                <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
                  <div className="font-bold text-green-800">≤50bps</div>
                  <div className="text-xs text-green-600">RMSE</div>
                </div>
                <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
                  <div className="font-bold text-green-800">78-82%</div>
                  <div className="text-xs text-green-600">Coverage</div>
                </div>
                <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
                  <div className="font-bold text-green-800">≥8</div>
                  <div className="text-xs text-green-600">Min Sample</div>
                </div>
              </div>

              <h4 className="font-semibold text-gray-900 mb-2">🏢 Market Coverage</h4>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-sm">
                <div className="bg-gray-50 border border-gray-200 rounded p-2 text-center">
                  <div className="font-bold">DFW</div>
                  <div className="text-xs text-gray-600">2,500+ props</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded p-2 text-center">
                  <div className="font-bold">IE</div>
                  <div className="text-xs text-gray-600">1,800+ props</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded p-2 text-center">
                  <div className="font-bold">ATL</div>
                  <div className="text-xs text-gray-600">2,200+ props</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded p-2 text-center">
                  <div className="font-bold">PHX</div>
                  <div className="text-xs text-gray-600">1,600+ props</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded p-2 text-center">
                  <div className="font-bold">SAV</div>
                  <div className="text-xs text-gray-600">800+ props</div>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-800 mb-2">🔧 Technical Details</h4>
              <div className="text-sm text-blue-700 space-y-1">
                <div><strong>Recency Weight:</strong> exp(-ln(2) * months_ago / 12) - 12-month half-life</div>
                <div><strong>Distance Weight:</strong> exp(-miles / 15) * submarket_bonus</div>
                <div><strong>Size Weight:</strong> Gaussian kernel, σ=0.35 on log scale</div>
                <div><strong>Age Weight:</strong> Gaussian kernel, σ=10 years</div>
                <div><strong>Outlier Removal:</strong> Winsorize at [P5, P95] per market</div>
              </div>
            </div>
          </div>

          {/* Version 0.9 */}
          <div className="border-l-4 border-blue-500 pl-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-2xl font-bold text-blue-800">Version 0.9.0</h2>
              <span className="text-sm text-gray-500">July 15, 2025</span>
            </div>
            
            <div className="bg-white border border-gray-200 rounded-lg p-6 mb-4">
              <h3 className="font-semibold text-gray-900 mb-3">🧪 Release Candidate</h3>
              
              <h4 className="font-semibold text-gray-900 mb-2">✨ New Features</h4>
              <ul className="text-gray-700 space-y-1 mb-4">
                <li>• Enhanced data validation with geofence checking</li>
                <li>• Automated review queue for flagged comparables</li>
                <li>• Admin dashboard for accuracy monitoring</li>
                <li>• Demo mode with data masking</li>
                <li>• Performance testing framework (k6)</li>
              </ul>

              <h4 className="font-semibold text-gray-900 mb-2">🐛 Bug Fixes</h4>
              <ul className="text-gray-700 space-y-1 mb-4">
                <li>• Fixed confidence interval calibration edge cases</li>
                <li>• Improved handling of sparse markets (SAV)</li>
                <li>• Resolved memory leaks in nightly accuracy script</li>
                <li>• Fixed timezone issues in trend calculations</li>
              </ul>

              <h4 className="font-semibold text-gray-900 mb-2">⚡ Performance</h4>
              <ul className="text-gray-700 space-y-1">
                <li>• 40% faster API response times through query optimization</li>
                <li>• Reduced memory usage by 25% in batch processing</li>
                <li>• Implemented caching for frequently requested valuations</li>
              </ul>
            </div>
          </div>

          {/* Version 0.8 */}
          <div className="border-l-4 border-purple-500 pl-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-2xl font-bold text-purple-800">Version 0.8.0</h2>
              <span className="text-sm text-gray-500">June 1, 2025</span>
            </div>
            
            <div className="bg-white border border-gray-200 rounded-lg p-6 mb-4">
              <h3 className="font-semibold text-gray-900 mb-3">🔄 Beta Release</h3>
              
              <h4 className="font-semibold text-gray-900 mb-2">✨ New Features</h4>
              <ul className="text-gray-700 space-y-1 mb-4">
                <li>• Conformal prediction for confidence intervals</li>
                <li>• Market-specific trend adjustments</li>
                <li>• Fallback rules for low-data scenarios</li>
                <li>• Enhanced comparable weighting algorithm</li>
              </ul>

              <h4 className="font-semibold text-gray-900 mb-2">📈 Accuracy Improvements</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="bg-green-50 border border-green-200 rounded p-2">
                  <div className="font-bold text-green-800">MAPE: 12.3% → 9.8%</div>
                  <div className="text-green-600">2.5pp improvement</div>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded p-2">
                  <div className="font-bold text-blue-800">RMSE: 58 → 48 bps</div>
                  <div className="text-blue-600">10 bps improvement</div>
                </div>
                <div className="bg-purple-50 border border-purple-200 rounded p-2">
                  <div className="font-bold text-purple-800">Coverage: 72% → 80%</div>
                  <div className="text-purple-600">Better calibration</div>
                </div>
              </div>
            </div>

            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <h4 className="font-semibold text-orange-800 mb-2">⚠️ Breaking Changes</h4>
              <ul className="text-orange-700 space-y-1">
                <li>• API response format updated to include confidence intervals</li>
                <li>• Methodology field changed from "simple_median" to "weighted_median"</li>
                <li>• Minimum sample size increased from 5 to 8 comparables</li>
              </ul>
            </div>
          </div>

          {/* Version 0.7 */}
          <div className="border-l-4 border-yellow-500 pl-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-2xl font-bold text-yellow-800">Version 0.7.0</h2>
              <span className="text-sm text-gray-500">April 20, 2025</span>
            </div>
            
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="font-semibold text-gray-900 mb-3">🏗️ Alpha Release</h3>
              
              <h4 className="font-semibold text-gray-900 mb-2">✨ New Features</h4>
              <ul className="text-gray-700 space-y-1 mb-4">
                <li>• Initial market coverage (DFW, IE, ATL)</li>
                <li>• Basic comparable weighting by recency and distance</li>
                <li>• Simple median estimator</li>
                <li>• CSV data validation</li>
                <li>• Basic API endpoints</li>
              </ul>

              <h4 className="font-semibold text-gray-900 mb-2">🎯 Baseline Performance</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                  <div className="font-bold text-yellow-800">MAPE: 15.2%</div>
                  <div className="text-yellow-600">Initial baseline</div>
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                  <div className="font-bold text-yellow-800">RMSE: 68 bps</div>
                  <div className="text-yellow-600">Room for improvement</div>
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                  <div className="font-bold text-yellow-800">Coverage: N/A</div>
                  <div className="text-yellow-600">Not yet calibrated</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <h2>Upcoming Releases</h2>

        <div className="space-y-4">
          <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-blue-800">Version 1.1.0 (Planned)</h3>
              <span className="text-sm text-blue-600">Q4 2025</span>
            </div>
            <h4 className="font-semibold text-blue-800 mb-2">🎯 Hedonic Regression Enhancement</h4>
            <ul className="text-blue-700 space-y-1">
              <li>• Property-specific feature adjustments (dock doors, ceiling height, parking)</li>
              <li>• Hedonic regression residual calibration</li>
              <li>• Expanded comparable criteria (up to 50 miles for sparse markets)</li>
              <li>• Machine learning similarity scoring</li>
            </ul>
          </div>

          <div className="bg-green-50 border-l-4 border-green-400 p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-green-800">Version 1.2.0 (Planned)</h3>
              <span className="text-sm text-green-600">Q1 2026</span>
            </div>
            <h4 className="font-semibold text-green-800 mb-2">🌐 Market Expansion</h4>
            <ul className="text-green-700 space-y-1">
              <li>• 5 additional markets (Chicago, Miami, Seattle, Denver, Austin)</li>
              <li>• Cross-market spillover modeling</li>
              <li>• Regional economic indicators integration</li>
              <li>• Multi-market portfolio valuation</li>
            </ul>
          </div>

          <div className="bg-purple-50 border-l-4 border-purple-400 p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-purple-800">Version 2.0.0 (Planned)</h3>
              <span className="text-sm text-purple-600">Q3 2026</span>
            </div>
            <h4 className="font-semibold text-purple-800 mb-2">🤖 AI-Powered Valuation</h4>
            <ul className="text-purple-700 space-y-1">
              <li>• Deep learning valuation models</li>
              <li>• Satellite imagery analysis</li>
              <li>• Real-time market sentiment indicators</li>
              <li>• Probabilistic valuation distributions</li>
            </ul>
          </div>
        </div>

        <h2>Migration Guide</h2>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 my-6">
          <h3 className="font-semibold text-yellow-800 mb-3">API Version Compatibility</h3>
          <p className="text-yellow-700 mb-4">
            CapSight maintains backward compatibility for major API versions. Current v1.0 API will be 
            supported through v2.x releases with a minimum 12-month deprecation notice.
          </p>
          
          <h4 className="font-semibold text-yellow-800 mb-2">Version Migration</h4>
          <ul className="text-yellow-700 space-y-1">
            <li>• <strong>Minor versions (1.0 → 1.1):</strong> No breaking changes, optional new fields</li>
            <li>• <strong>Major versions (1.x → 2.0):</strong> Potential breaking changes with migration guide</li>
            <li>• <strong>Deprecation policy:</strong> 12-month notice for breaking changes</li>
            <li>• <strong>Fallback support:</strong> Legacy version endpoints maintained during transition</li>
          </ul>
        </div>

        <h2>Performance History</h2>

        <div className="overflow-x-auto my-6">
          <table className="min-w-full border border-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Version</th>
                <th className="px-4 py-3 text-center font-semibold">MAPE</th>
                <th className="px-4 py-3 text-center font-semibold">RMSE (bps)</th>
                <th className="px-4 py-3 text-center font-semibold">Coverage</th>
                <th className="px-4 py-3 text-center font-semibold">Response Time</th>
                <th className="px-4 py-3 text-center font-semibold">Markets</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t bg-green-50">
                <td className="px-4 py-3 font-bold">v1.0.0</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">9.5%</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">47</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">79.8%</td>
                <td className="px-4 py-3 text-center">1.2s</td>
                <td className="px-4 py-3 text-center">5</td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">v0.9.0</td>
                <td className="px-4 py-3 text-center">9.8%</td>
                <td className="px-4 py-3 text-center">48</td>
                <td className="px-4 py-3 text-center">80.1%</td>
                <td className="px-4 py-3 text-center">2.0s</td>
                <td className="px-4 py-3 text-center">5</td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">v0.8.0</td>
                <td className="px-4 py-3 text-center">12.3%</td>
                <td className="px-4 py-3 text-center">58</td>
                <td className="px-4 py-3 text-center">72%</td>
                <td className="px-4 py-3 text-center">2.5s</td>
                <td className="px-4 py-3 text-center">4</td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">v0.7.0</td>
                <td className="px-4 py-3 text-center">15.2%</td>
                <td className="px-4 py-3 text-center">68</td>
                <td className="px-4 py-3 text-center">N/A</td>
                <td className="px-4 py-3 text-center">3.2s</td>
                <td className="px-4 py-3 text-center">3</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8">
          <p className="text-gray-700 italic">
            <strong>Note:</strong> All performance metrics are calculated using our standard 
            backtesting framework across all supported markets. Historical data is retained 
            for transparency and continuous improvement.
          </p>
        </div>
      </div>
    </>
  )
}
