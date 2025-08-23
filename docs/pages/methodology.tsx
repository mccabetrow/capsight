import Head from 'next/head'
import { useEffect, useState } from 'react'

export default function Methodology() {
  const [activeSection, setActiveSection] = useState('')

  useEffect(() => {
    const handleScroll = () => {
      const sections = document.querySelectorAll('h2[id]')
      const scrollPos = window.scrollY + 100
      
      for (let section of sections) {
        const element = section as HTMLElement
        if (element.offsetTop <= scrollPos && element.offsetTop + element.offsetHeight > scrollPos) {
          setActiveSection(element.id)
          break
        }
      }
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const sections = [
    { id: 'overview', title: 'Overview' },
    { id: 'data-quality', title: 'Data Quality Gates' },
    { id: 'similarity', title: 'Similarity Weighting' },
    { id: 'time-adjustment', title: 'Time Normalization' },
    { id: 'estimator', title: 'Final Estimator' },
    { id: 'confidence', title: 'Confidence Intervals' },
    { id: 'metrics', title: 'Quality Metrics' },
    { id: 'auditability', title: 'Auditability' },
    { id: 'versioning', title: 'Version Control' },
    { id: 'validation', title: 'Validation & Testing' },
  ]

  return (
    <>
      <Head>
        <title>Valuation Methodology - CapSight Docs</title>
        <meta name="description" content="CapSight industrial CRE valuation methodology and approach" />
      </Head>

      <div className="flex">
        {/* Table of Contents */}
        <nav className="w-64 fixed top-24 h-screen overflow-y-auto hidden xl:block">
          <div className="p-4">
            <h3 className="font-semibold text-gray-900 mb-3">On This Page</h3>
            <ul className="space-y-2">
              {sections.map((section) => (
                <li key={section.id}>
                  <a
                    href={`#${section.id}`}
                    className={`block text-sm py-1 px-2 rounded transition-colors ${
                      activeSection === section.id
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    {section.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </nav>

        {/* Main Content */}
        <div className="flex-1 xl:ml-64">
          <div className="prose prose-lg max-w-none">
            <h1 id="overview">CapSight Valuation Methodology v1.0</h1>
            
            <div className="bg-blue-50 border-l-4 border-blue-400 p-6 my-6">
              <h3 className="text-lg font-semibold text-blue-800 mb-2">Overview</h3>
              <p className="text-blue-700">
                This document defines the exact methodology used by CapSight for industrial CRE valuations, 
                including outlier handling, similarity weighting, time adjustments, and confidence interval calibration.
              </p>
            </div>

            <h2 id="data-quality">1. Data Quality Gates</h2>
            
            <h3>Outlier Policy</h3>
            <ul>
              <li><strong>Cap rate bounds:</strong> Reject comps with cap_rate &lt; 2% or &gt; 15%</li>
              <li><strong>Price per SF bounds:</strong> Reject comps outside [P5, P95] per market</li>
              <li><strong>Market-level winsorization:</strong> Winsorize cap rates at [P5, P95] per market</li>
              <li><strong>Required fields:</strong> NOI must be stabilized; reject TTM or pro-forma without conversion</li>
            </ul>

            <h3>Data Validation</h3>
            <ul>
              <li>Geofence validation by market polygon</li>
              <li>Size and age within reasonable bounds</li>
              <li>Verification status must be 'verified' or 'broker-confirmed'</li>
              <li>Sale date within 18 months for primary analysis</li>
            </ul>

            <h2 id="similarity">2. Similarity Weighting</h2>
            <p>Weights are multiplicative and normalized to sum=1. Each component:</p>

            <h3>Recency Weight</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 font-mono text-sm">
              w_t = exp(-ln(2) * months_ago / 12)
            </div>
            <ul>
              <li>12-month half-life decay</li>
              <li>Recent sales weighted more heavily</li>
              <li>Applied to all comps regardless of age</li>
            </ul>

            <h3>Distance Weight</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 font-mono text-sm">
              w_d = exp(-miles / 15) * submarket_bonus
            </div>
            <ul>
              <li>15-mile exponential decay</li>
              <li><code>submarket_bonus = 2.0</code> if same submarket, <code>1.0</code> otherwise</li>
              <li>Distance calculated from property centroids</li>
            </ul>

            <h3>Size Weight</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 font-mono text-sm">
              w_s = exp(-0.5 * ((log(comp_sf) - log(subject_sf)) / 0.35)^2)
            </div>
            <ul>
              <li>Gaussian kernel on log-scale square footage</li>
              <li>σ = 0.35 (approximately ±35% size tolerance)</li>
              <li>Heavily penalizes size mismatches</li>
            </ul>

            <h3>Age/Quality Weight (when available)</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 font-mono text-sm">
              w_a = exp(-0.5 * ((comp_year - subject_year) / 10)^2)
            </div>
            <ul>
              <li>Gaussian kernel on year built</li>
              <li>σ = 10 years tolerance</li>
              <li>Applied only when both ages are known</li>
            </ul>

            <h3>Combined Weight</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 font-mono text-sm">
              w_final = (w_t * w_d * w_s * w_a) / sum(all_weights)
            </div>

            <h2 id="time-adjustment">3. Time Normalization</h2>
            
            <h3>Market Trend Adjustment</h3>
            <ul>
              <li>Fit monthly cap rate trend per market using LOESS or robust linear regression</li>
              <li>Minimum 24 months of data required for trend fitting</li>
              <li>Outlier-resistant: use Theil-Sen estimator for linear trends</li>
              <li>Adjust each comp's cap rate forward to valuation date</li>
            </ul>

            <h3>Implementation</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`-- Market trend calculation (simplified)
SELECT market_slug,
       regr_slope(cap_rate_pct, extract(epoch from sale_date)) as trend_bps_per_day
FROM v_verified_sales_18mo 
WHERE cap_rate_pct IS NOT NULL
GROUP BY market_slug
HAVING count(*) >= 24;`}</code></pre>
            </div>

            <h2 id="estimator">4. Final Estimator</h2>
            
            <h3>Weighted Trimmed Median</h3>
            <ul>
              <li>Apply all weights to time-adjusted cap rates</li>
              <li>Use weighted median (not mean) for robustness</li>
              <li>Trim extreme 5% of weighted distribution before calculation</li>
            </ul>

            <h3>Fallback Rules</h3>
            <div className="space-y-4">
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <h4 className="font-semibold text-yellow-800">1. Low sample size (&lt; 8 valid comps)</h4>
                <ul className="text-yellow-700 mt-2">
                  <li>Fall back to market median cap rate (last 12 months)</li>
                  <li>Widen confidence interval to max(10%, conformal_q)</li>
                  <li>Display "Low sample" warning badge</li>
                </ul>
              </div>
              
              <div className="bg-orange-50 border-l-4 border-orange-400 p-4">
                <h4 className="font-semibold text-orange-800">2. High dispersion (weighted IQR &gt; 150 bps)</h4>
                <ul className="text-orange-700 mt-2">
                  <li>Widen confidence interval by +200-300 bps</li>
                  <li>Display "High dispersion" warning</li>
                </ul>
              </div>
              
              <div className="bg-red-50 border-l-4 border-red-400 p-4">
                <h4 className="font-semibold text-red-800">3. Stale data (all comps &gt; 18 months old)</h4>
                <ul className="text-red-700 mt-2">
                  <li>Require user confirmation to proceed</li>
                  <li>Widen confidence interval by +400-500 bps</li>
                  <li>Display "Stale data" warning</li>
                </ul>
              </div>
            </div>

            <h2 id="confidence">5. Confidence Interval Calibration</h2>
            
            <h3>Conformal Prediction Method</h3>
            <ol>
              <li>Create backtest set from historical sales</li>
              <li>For each comp, predict value using contemporaneous comps</li>
              <li>Calculate Absolute Percentage Error (APE) for each prediction</li>
              <li>Use conformal quantile for desired coverage:</li>
            </ol>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <pre className="text-sm"><code>{`def conformal_width(apes, coverage=0.80):
    apes = np.asarray([a for a in apes if np.isfinite(a)])
    if len(apes) < 50:  # Minimum sample size
        return 0.10     # Conservative 10% default
    return float(np.quantile(apes, coverage))`}</code></pre>
            </div>

            <h3>Dynamic Band Logic</h3>
            <ul>
              <li><strong>Target:</strong> 80% coverage (±5% aspiration)</li>
              <li><strong>SLA met:</strong> MAPE ≤ 10%, RMSE ≤ 50 bps, coverage ∈ [78%, 82%]</li>
              <li><strong>Display:</strong> ±min(5%, conformal_q) if SLA met, otherwise ±conformal_q with warning</li>
            </ul>

            <h2 id="metrics">6. Quality Metrics & SLA Targets</h2>
            
            <h3>Primary Metrics</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-semibold text-green-800">MAPE</h4>
                <p className="text-green-700">≤ 10% target</p>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-semibold text-green-800">RMSE</h4>
                <p className="text-green-700">≤ 50 basis points</p>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-semibold text-green-800">Coverage</h4>
                <p className="text-green-700">78-82% within bands</p>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-semibold text-green-800">Sample Size</h4>
                <p className="text-green-700">≥ 8 comps minimum</p>
              </div>
            </div>

            <h3>Secondary Metrics</h3>
            <ul>
              <li><strong>Weighted IQR:</strong> &lt; 150 basis points (dispersion check)</li>
              <li><strong>Data freshness:</strong> &lt; 18 months median age</li>
              <li><strong>Verification rate:</strong> &gt; 80% verified or broker-confirmed</li>
            </ul>

            <h2 id="auditability">7. Auditability & Transparency</h2>
            
            <h3>Valuation Output Includes</h3>
            <ol>
              <li><strong>Primary estimate:</strong> Weighted median cap rate</li>
              <li><strong>Confidence interval:</strong> Calibrated or fallback width</li>
              <li><strong>Top 5 comps:</strong> Address (masked), date, adjusted cap, weight</li>
              <li><strong>Quality indicators:</strong> Sample size, dispersion, data age</li>
              <li><strong>Method version:</strong> v1.0 timestamp</li>
            </ol>

            <h3>Explainability Panel</h3>
            <ul>
              <li>Methodology summary and key assumptions</li>
              <li>Comp weighting breakdown by factor</li>
              <li>Time adjustments applied</li>
              <li>Fallback rules triggered (if any)</li>
            </ul>

            <h2 id="versioning">8. Version Control & Updates</h2>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 my-4">
              <h3 className="text-blue-800 font-semibold">Version 1.0 (Current)</h3>
              <ul className="text-blue-700 mt-2">
                <li>Weighted median with multiplicative similarity kernels</li>
                <li>Conformal prediction calibration</li>
                <li>Market trend time adjustment</li>
                <li>Robust outlier handling</li>
              </ul>
            </div>

            <h3>Future Enhancements</h3>
            <ul>
              <li><strong>v1.1:</strong> Hedonic regression residual calibration</li>
              <li><strong>v1.2:</strong> Property-specific feature adjustments</li>
              <li><strong>v1.3:</strong> Cross-market spillover modeling</li>
            </ul>

            <h3>Change Policy</h3>
            <ul>
              <li>Minor version bump for kernel parameter changes</li>
              <li>Major version bump for fundamental methodology changes</li>
              <li>All versions stored in accuracy_metrics table</li>
              <li>A/B testing required for major changes</li>
            </ul>

            <h2 id="validation">9. Validation & Testing</h2>
            
            <h3>Golden Test Set</h3>
            <ul>
              <li>Frozen comp bundle with expected outputs</li>
              <li>±5-10 bps tolerance for regression testing</li>
              <li>Covers edge cases (large/small, old/new, remote locations)</li>
            </ul>

            <h3>Nightly Backtesting</h3>
            <ul>
              <li>Rolling 12-18 month validation window</li>
              <li>Per-market accuracy metrics calculation</li>
              <li>SLA breach alerting</li>
              <li>Historical trend analysis</li>
            </ul>

            <h3>CI/CD Gates</h3>
            <ul>
              <li>MAPE regression &gt; 1 percentage point: Fail PR</li>
              <li>Coverage regression &gt; 1 percentage point: Fail PR</li>
              <li>Golden test deviations &gt; tolerance: Fail PR</li>
            </ul>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mt-8">
              <p className="text-gray-700 italic">
                <strong>Note:</strong> This methodology is designed to be robust, transparent, and continuously 
                improving based on empirical validation. All parameters are data-driven and regularly recalibrated.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
