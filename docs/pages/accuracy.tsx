import Head from 'next/head'

export default function Accuracy() {
  return (
    <>
      <Head>
        <title>Accuracy & SLA - CapSight Docs</title>
        <meta name="description" content="CapSight accuracy KPIs, SLA commitments, and monitoring framework" />
      </Head>

      <div className="prose prose-lg max-w-none">
        <h1>Accuracy KPIs & SLA Policy</h1>
        
        <div className="bg-green-50 border-l-4 border-green-400 p-6 my-6">
          <h3 className="text-lg font-semibold text-green-800 mb-2">SLA Commitment</h3>
          <p className="text-green-700">
            CapSight commits to maintaining high accuracy standards across all supported markets 
            with transparent monitoring and continuous improvement.
          </p>
        </div>

        <h2>Key Performance Indicators</h2>

        <h3>Primary Accuracy Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-6">
          <div className="bg-white border-2 border-green-200 rounded-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-green-800 font-bold text-xl">M</span>
              </div>
              <div>
                <h4 className="font-bold text-green-800 text-lg">MAPE</h4>
                <p className="text-green-600 text-sm">Mean Absolute Percentage Error</p>
              </div>
            </div>
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Target</span>
                <span className="font-bold text-green-700">≤ 10%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-green-500 h-2 rounded-full w-4/5"></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Measures average absolute percentage difference between predicted and actual values. 
              Lower is better.
            </p>
          </div>

          <div className="bg-white border-2 border-blue-200 rounded-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-blue-800 font-bold text-xl">R</span>
              </div>
              <div>
                <h4 className="font-bold text-blue-800 text-lg">RMSE</h4>
                <p className="text-blue-600 text-sm">Root Mean Square Error</p>
              </div>
            </div>
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Target</span>
                <span className="font-bold text-blue-700">≤ 50 basis points</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full w-3/4"></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Measures prediction errors in cap rate terms. Penalizes large errors more heavily 
              than MAPE.
            </p>
          </div>

          <div className="bg-white border-2 border-purple-200 rounded-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-purple-800 font-bold text-xl">C</span>
              </div>
              <div>
                <h4 className="font-bold text-purple-800 text-lg">Coverage</h4>
                <p className="text-purple-600 text-sm">Confidence Interval Calibration</p>
              </div>
            </div>
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Target Range</span>
                <span className="font-bold text-purple-700">78% - 82%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-purple-500 h-2 rounded-full w-4/5"></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Percentage of actual sales falling within predicted 80% confidence intervals. 
              Well-calibrated = ~80%.
            </p>
          </div>

          <div className="bg-white border-2 border-orange-200 rounded-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-orange-800 font-bold text-xl">S</span>
              </div>
              <div>
                <h4 className="font-bold text-orange-800 text-lg">Sample Size</h4>
                <p className="text-orange-600 text-sm">Comparable Count Adequacy</p>
              </div>
            </div>
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Minimum</span>
                <span className="font-bold text-orange-700">≥ 8 comps</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-orange-500 h-2 rounded-full w-5/6"></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Minimum number of comparable sales required for reliable valuation. 
              Below threshold triggers fallback logic.
            </p>
          </div>
        </div>

        <h3>Secondary Quality Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-800">&lt; 150 bps</div>
            <div className="text-sm text-gray-600">Weighted IQR</div>
            <div className="text-xs text-gray-500 mt-1">Dispersion measure</div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-800">&lt; 18 months</div>
            <div className="text-sm text-gray-600">Median Age</div>
            <div className="text-xs text-gray-500 mt-1">Data freshness</div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-800">&gt; 80%</div>
            <div className="text-sm text-gray-600">Verification Rate</div>
            <div className="text-xs text-gray-500 mt-1">Data quality</div>
          </div>
        </div>

        <h2>SLA Commitment Levels</h2>

        <div className="space-y-4 my-6">
          <div className="bg-green-50 border-l-4 border-green-500 p-4">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold text-green-800">Gold Standard</h4>
              <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded">Target</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="font-medium text-green-700">MAPE ≤ 8%</div>
                <div className="text-green-600">Excellent accuracy</div>
              </div>
              <div>
                <div className="font-medium text-green-700">RMSE ≤ 40 bps</div>
                <div className="text-green-600">Low volatility</div>
              </div>
              <div>
                <div className="font-medium text-green-700">Coverage 79-81%</div>
                <div className="text-green-600">Well calibrated</div>
              </div>
              <div>
                <div className="font-medium text-green-700">Sample ≥ 15</div>
                <div className="text-green-600">High confidence</div>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 border-l-4 border-blue-500 p-4">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold text-blue-800">Standard SLA</h4>
              <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-1 rounded">Committed</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="font-medium text-blue-700">MAPE ≤ 10%</div>
                <div className="text-blue-600">Good accuracy</div>
              </div>
              <div>
                <div className="font-medium text-blue-700">RMSE ≤ 50 bps</div>
                <div className="text-blue-600">Acceptable volatility</div>
              </div>
              <div>
                <div className="font-medium text-blue-700">Coverage 78-82%</div>
                <div className="text-blue-600">Reasonably calibrated</div>
              </div>
              <div>
                <div className="font-medium text-blue-700">Sample ≥ 8</div>
                <div className="text-blue-600">Minimum viable</div>
              </div>
            </div>
          </div>

          <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold text-yellow-800">Acceptable Range</h4>
              <span className="bg-yellow-100 text-yellow-800 text-xs font-semibold px-2 py-1 rounded">Warning</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="font-medium text-yellow-700">MAPE ≤ 12%</div>
                <div className="text-yellow-600">Monitoring required</div>
              </div>
              <div>
                <div className="font-medium text-yellow-700">RMSE ≤ 60 bps</div>
                <div className="text-yellow-600">Higher volatility</div>
              </div>
              <div>
                <div className="font-medium text-yellow-700">Coverage 76-84%</div>
                <div className="text-yellow-600">Needs recalibration</div>
              </div>
              <div>
                <div className="font-medium text-yellow-700">Sample ≥ 5</div>
                <div className="text-yellow-600">Fallback triggered</div>
              </div>
            </div>
          </div>

          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold text-red-800">SLA Breach</h4>
              <span className="bg-red-100 text-red-800 text-xs font-semibold px-2 py-1 rounded">Critical</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="font-medium text-red-700">MAPE &gt; 12%</div>
                <div className="text-red-600">Immediate action required</div>
              </div>
              <div>
                <div className="font-medium text-red-700">RMSE &gt; 60 bps</div>
                <div className="text-red-600">High prediction error</div>
              </div>
              <div>
                <div className="font-medium text-red-700">Coverage &lt; 76% or &gt; 84%</div>
                <div className="text-red-600">Miscalibrated</div>
              </div>
              <div>
                <div className="font-medium text-red-700">Sample &lt; 5</div>
                <div className="text-red-600">Insufficient data</div>
              </div>
            </div>
          </div>
        </div>

        <h2>Monitoring Framework</h2>

        <h3>Automated Backtesting</h3>
        <p>
          CapSight runs nightly backtests to continuously validate accuracy across all markets:
        </p>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-4">
          <h4 className="font-semibold text-gray-900 mb-2">Backtesting Process</h4>
          <ol className="text-sm text-gray-700 space-y-1">
            <li><strong>1. Data Collection:</strong> Gather all sales from last 18 months</li>
            <li><strong>2. Time-Split Validation:</strong> Use 12-month training, 6-month test window</li>
            <li><strong>3. Prediction Generation:</strong> Apply current methodology to historical context</li>
            <li><strong>4. Error Calculation:</strong> Compute MAPE, RMSE, and coverage metrics</li>
            <li><strong>5. Trend Analysis:</strong> Compare against previous periods for drift detection</li>
            <li><strong>6. Alert Generation:</strong> Trigger notifications for SLA breaches</li>
          </ol>
        </div>

        <h3>Real-time Quality Gates</h3>
        <p>
          Every valuation request includes quality checks and fallback mechanisms:
        </p>

        <div className="space-y-4 my-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Sample Size Check</h4>
            <div className="flex items-center mt-2">
              <div className="flex-1">
                <div className="text-sm text-gray-600">
                  If fewer than 8 comparable sales found → trigger fallback to market median
                </div>
              </div>
              <div className="ml-4">
                <span className="bg-yellow-100 text-yellow-800 text-xs font-semibold px-2 py-1 rounded">
                  LOW SAMPLE
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Dispersion Check</h4>
            <div className="flex items-center mt-2">
              <div className="flex-1">
                <div className="text-sm text-gray-600">
                  If weighted IQR &gt; 150 bps → widen confidence intervals by 200-300 bps
                </div>
              </div>
              <div className="ml-4">
                <span className="bg-orange-100 text-orange-800 text-xs font-semibold px-2 py-1 rounded">
                  HIGH DISPERSION
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Staleness Check</h4>
            <div className="flex items-center mt-2">
              <div className="flex-1">
                <div className="text-sm text-gray-600">
                  If all comps &gt; 18 months old → require user confirmation and widen bands
                </div>
              </div>
              <div className="ml-4">
                <span className="bg-red-100 text-red-800 text-xs font-semibold px-2 py-1 rounded">
                  STALE DATA
                </span>
              </div>
            </div>
          </div>
        </div>

        <h2>Market-Specific Performance</h2>

        <div className="overflow-x-auto my-6">
          <table className="min-w-full border border-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Market</th>
                <th className="px-4 py-3 text-center font-semibold">MAPE</th>
                <th className="px-4 py-3 text-center font-semibold">RMSE (bps)</th>
                <th className="px-4 py-3 text-center font-semibold">Coverage</th>
                <th className="px-4 py-3 text-center font-semibold">Sample Size</th>
                <th className="px-4 py-3 text-center font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">Dallas-Fort Worth (DFW)</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">8.2%</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">42</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">80.1%</td>
                <td className="px-4 py-3 text-center">18</td>
                <td className="px-4 py-3 text-center">
                  <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded">
                    GOLD
                  </span>
                </td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">Inland Empire (IE)</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">9.1%</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">47</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">79.8%</td>
                <td className="px-4 py-3 text-center">15</td>
                <td className="px-4 py-3 text-center">
                  <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-1 rounded">
                    SLA MET
                  </span>
                </td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">Atlanta (ATL)</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">9.7%</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">49</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">81.2%</td>
                <td className="px-4 py-3 text-center">12</td>
                <td className="px-4 py-3 text-center">
                  <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-1 rounded">
                    SLA MET
                  </span>
                </td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">Phoenix (PHX)</td>
                <td className="px-4 py-3 text-center text-yellow-600 font-bold">11.3%</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">53</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">78.9%</td>
                <td className="px-4 py-3 text-center">9</td>
                <td className="px-4 py-3 text-center">
                  <span className="bg-yellow-100 text-yellow-800 text-xs font-semibold px-2 py-1 rounded">
                    WARNING
                  </span>
                </td>
              </tr>
              <tr className="border-t">
                <td className="px-4 py-3 font-semibold">Savannah (SAV)</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">9.4%</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">46</td>
                <td className="px-4 py-3 text-center text-green-600 font-bold">79.1%</td>
                <td className="px-4 py-3 text-center">8</td>
                <td className="px-4 py-3 text-center">
                  <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-1 rounded">
                    SLA MET
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 my-6">
          <h4 className="font-semibold text-blue-800">Performance Summary</h4>
          <ul className="text-blue-700 mt-2 space-y-1">
            <li>• <strong>4 of 5 markets</strong> meeting or exceeding SLA commitments</li>
            <li>• <strong>Phoenix</strong> flagged for elevated MAPE - investigation in progress</li>
            <li>• <strong>Overall system MAPE:</strong> 9.5% (well within 10% target)</li>
            <li>• <strong>Last updated:</strong> August 23, 2025, 2:00 AM UTC</li>
          </ul>
        </div>

        <h2>Continuous Improvement</h2>

        <h3>Monthly Reviews</h3>
        <p>
          CapSight conducts monthly accuracy reviews to identify improvement opportunities:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Methodology Updates</h4>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• Parameter recalibration based on new data</li>
              <li>• Market-specific adjustments</li>
              <li>• Algorithm improvements</li>
              <li>• A/B testing of new approaches</li>
            </ul>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900">Data Quality Enhancements</h4>
            <ul className="text-sm text-gray-600 mt-2 space-y-1">
              <li>• Additional verification sources</li>
              <li>• Expanded comparable criteria</li>
              <li>• Enhanced outlier detection</li>
              <li>• Improved property matching</li>
            </ul>
          </div>
        </div>

        <h3>Transparency Commitment</h3>
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 my-6">
          <h4 className="font-semibold text-green-800 mb-2">What We Promise</h4>
          <ul className="text-green-700 space-y-2">
            <li>• <strong>Real-time metrics:</strong> Current accuracy data available 24/7</li>
            <li>• <strong>Methodology transparency:</strong> Full documentation of our approach</li>
            <li>• <strong>Proactive communication:</strong> Advance notice of significant changes</li>
            <li>• <strong>Continuous improvement:</strong> Regular updates based on performance data</li>
            <li>• <strong>Independent validation:</strong> Third-party audits of our methodology</li>
          </ul>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8">
          <p className="text-gray-700 italic">
            <strong>Note:</strong> These metrics are updated nightly via automated backtesting. 
            Historical performance data is available through our admin dashboard and API endpoints.
          </p>
        </div>
      </div>
    </>
  )
}
