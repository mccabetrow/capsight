import React from 'react';
import Head from 'next/head';

export default function TermsOfUse() {
  const lastUpdated = "August 23, 2025";

  return (
    <>
      <Head>
        <title>Terms of Use - CapSight</title>
        <meta name="description" content="CapSight terms of use and service agreement" />
      </Head>
      
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white shadow-sm rounded-lg">
            <div className="px-6 py-8">
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Terms of Use</h1>
                <p className="mt-2 text-sm text-gray-500">Last updated: {lastUpdated}</p>
              </div>

              <div className="prose prose-lg max-w-none">
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
                  <p className="text-blue-700">
                    <strong>Plain English Summary:</strong> CapSight provides indicative CRE valuations 
                    for informational purposes only. Our estimates are not formal appraisals and should 
                    not be used for lending or legal purposes.
                  </p>
                </div>

                <h2>Acceptance of Terms</h2>
                <p>
                  By accessing or using CapSight's valuation services ("Service"), you agree to be bound by these 
                  Terms of Use ("Terms"). If you do not agree to these Terms, do not use our Service.
                </p>

                <h2>Service Description</h2>

                <h3>What CapSight Provides</h3>
                <p>
                  CapSight is an automated industrial commercial real estate valuation platform that provides:
                </p>
                <ul>
                  <li><strong>Indicative Valuations:</strong> Statistical estimates based on comparable sales data</li>
                  <li><strong>Market Analysis:</strong> Cap rate trends and market fundamentals</li>
                  <li><strong>Confidence Intervals:</strong> Calibrated uncertainty ranges for estimates</li>
                  <li><strong>Comparable Sales:</strong> Masked details of similar property transactions</li>
                </ul>

                <h3>What CapSight Does NOT Provide</h3>
                <div className="bg-red-50 border-l-4 border-red-400 p-4 my-4">
                  <div className="text-red-800 font-semibold mb-2">Important Limitations:</div>
                  <ul className="text-red-700 space-y-1">
                    <li>• <strong>Formal Appraisals:</strong> Not USPAP-compliant professional appraisals</li>
                    <li>• <strong>Investment Advice:</strong> Not recommendations to buy, sell, or hold</li>
                    <li>• <strong>Legal Valuations:</strong> Not suitable for legal proceedings or disputes</li>
                    <li>• <strong>Lending Support:</strong> Not acceptable for mortgage or financing purposes</li>
                    <li>• <strong>Tax Assessments:</strong> Not for property tax or assessment challenges</li>
                  </ul>
                </div>

                <h2>Non-USPAP Disclosure</h2>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 my-6">
                  <h3 className="text-yellow-800 font-semibold mb-3">🏢 Real Estate Professional Notice</h3>
                  <p className="text-yellow-700 mb-3">
                    <strong>CapSight valuations are NOT appraisals</strong> and do not comply with the Uniform 
                    Standards of Professional Appraisal Practice (USPAP). Our estimates:
                  </p>
                  <ul className="text-yellow-700 space-y-1">
                    <li>• Are produced by automated algorithms, not licensed appraisers</li>
                    <li>• Do not include physical property inspections</li>
                    <li>• May not account for unique property characteristics</li>
                    <li>• Are based on historical data that may not reflect current conditions</li>
                    <li>• Cannot replace professional judgment and market expertise</li>
                  </ul>
                </div>

                <h2>Acceptable Use</h2>

                <h3>Permitted Uses</h3>
                <p>You may use CapSight for:</p>
                <ul>
                  <li><strong>Market Research:</strong> Initial market analysis and trend research</li>
                  <li><strong>Portfolio Analysis:</strong> High-level portfolio evaluation (informational only)</li>
                  <li><strong>Academic Research:</strong> Educational and research purposes</li>
                  <li><strong>Business Intelligence:</strong> Market trend analysis for business planning</li>
                </ul>

                <h3>Prohibited Uses</h3>
                <p>You may NOT use CapSight for:</p>
                <ul>
                  <li><strong>Automated Systems:</strong> High-volume automated requests or scraping</li>
                  <li><strong>Resale:</strong> Redistributing valuations as your own service</li>
                  <li><strong>Competitive Intelligence:</strong> Building competing valuation products</li>
                  <li><strong>Unlawful Activities:</strong> Any illegal or fraudulent purposes</li>
                  <li><strong>System Interference:</strong> Attempting to disrupt or hack our systems</li>
                </ul>

                <h2>Rate Limits and Fair Use</h2>

                <h3>Usage Limits</h3>
                <p>To ensure fair access for all users:</p>
                <ul>
                  <li><strong>Rate Limit:</strong> 100 requests per minute, 1,000 requests per day per IP address</li>
                  <li><strong>Reasonable Use:</strong> Intended for human users, not automated systems</li>
                  <li><strong>Enterprise Plans:</strong> Higher limits available for commercial users</li>
                </ul>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 my-4">
                  <p className="text-blue-700">
                    <strong>Need Higher Limits?</strong> Contact us at{' '}
                    <a href="mailto:enterprise@capsight.com" className="underline">enterprise@capsight.com</a>{' '}
                    for commercial licensing options.
                  </p>
                </div>

                <h2>Accuracy and Reliability</h2>

                <h3>Best Efforts Standard</h3>
                <p>
                  CapSight strives to provide accurate valuations but makes no guarantees. Our methodology:
                </p>
                <ul>
                  <li>Targets ≤10% Mean Absolute Percentage Error (MAPE)</li>
                  <li>Uses robust statistical methods and quality gates</li>
                  <li>Is continuously monitored and improved</li>
                  <li>Includes confidence intervals to indicate uncertainty</li>
                </ul>

                <h3>Factors Affecting Accuracy</h3>
                <p>Valuation accuracy may be impacted by:</p>
                <ul>
                  <li><strong>Market Conditions:</strong> Volatile or rapidly changing markets</li>
                  <li><strong>Data Availability:</strong> Limited comparable sales in some areas</li>
                  <li><strong>Property Uniqueness:</strong> Unusual or specialized properties</li>
                  <li><strong>Timing:</strong> Market conditions may have changed since comparable sales</li>
                </ul>

                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 my-4">
                  <p className="text-yellow-800">
                    <strong>Always Verify:</strong> CapSight estimates should be verified with professional 
                    appraisers, brokers, or other qualified experts before making significant decisions.
                  </p>
                </div>

                <h2>Intellectual Property</h2>

                <h3>CapSight's Rights</h3>
                <p>CapSight owns or licenses:</p>
                <ul>
                  <li>Valuation algorithms and methodology</li>
                  <li>Software, user interfaces, and documentation</li>
                  <li>Aggregated market data and analytics</li>
                  <li>Trademarks, logos, and branding</li>
                </ul>

                <h3>Your Rights</h3>
                <p>You may:</p>
                <ul>
                  <li>Use valuation results for permitted purposes listed above</li>
                  <li>Reference CapSight as the source of estimates (required)</li>
                  <li>Include estimates in reports with proper attribution</li>
                </ul>

                <h2>Data Sources and Accuracy</h2>

                <h3>Data Sources</h3>
                <p>CapSight valuations are based on:</p>
                <ul>
                  <li><strong>Public Records:</strong> County assessor and recorder data</li>
                  <li><strong>MLS Systems:</strong> Multiple listing service transaction data</li>
                  <li><strong>Commercial Databases:</strong> Licensed commercial real estate data</li>
                  <li><strong>Broker Networks:</strong> Verified comparable sales from brokers</li>
                </ul>

                <h3>Data Quality</h3>
                <p>We implement quality controls including:</p>
                <ul>
                  <li>Automated outlier detection and removal</li>
                  <li>Geographic validation (market boundaries)</li>
                  <li>Cross-reference verification when possible</li>
                  <li>Regular data freshness audits</li>
                </ul>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 my-4">
                  <p className="text-blue-700">
                    <strong>Data Issues?</strong> Report suspected data errors to{' '}
                    <a href="mailto:data@capsight.com" className="underline">data@capsight.com</a>{' '}
                    with specific details for investigation.
                  </p>
                </div>

                <h2>Disclaimers and Limitations</h2>

                <h3>No Warranty</h3>
                <p>
                  CapSight is provided "AS IS" without warranties of any kind. We disclaim all warranties, 
                  express or implied, including:
                </p>
                <ul>
                  <li>Accuracy, completeness, or reliability of valuations</li>
                  <li>Fitness for any particular purpose</li>
                  <li>Uninterrupted or error-free operation</li>
                  <li>Security or data protection</li>
                </ul>

                <div className="bg-red-50 border-l-4 border-red-400 p-4 my-4">
                  <p className="text-red-800">
                    <strong>⚖️ Legal Counsel Recommended:</strong> Warranty disclaimers and liability 
                    limitations must be reviewed for enforceability under applicable state and federal law.
                  </p>
                </div>

                <h3>Limitation of Liability</h3>
                <p>
                  To the maximum extent permitted by law, CapSight shall not be liable for:
                </p>
                <ul>
                  <li><strong>Indirect Damages:</strong> Consequential, incidental, or special damages</li>
                  <li><strong>Lost Profits:</strong> Business losses or opportunity costs</li>
                  <li><strong>Reliance Damages:</strong> Losses from relying on our estimates</li>
                  <li><strong>Third Party Claims:</strong> Claims arising from your use of our service</li>
                </ul>

                <p className="font-semibold">
                  Our total liability for any claim shall not exceed the amount paid by you for our service 
                  in the 12 months preceding the claim.
                </p>

                <h2>Privacy and Data Protection</h2>

                <p>
                  Your privacy is important to us. Please review our{' '}
                  <a href="/legal/privacy" className="text-blue-600 hover:text-blue-800 underline">
                    Privacy Policy
                  </a>
                  {' '}for information about how we collect, use, and protect your data.
                </p>

                <h3>Cookies and Analytics</h3>
                <p>We use cookies for:</p>
                <ul>
                  <li>Essential service functionality</li>
                  <li>Security and rate limiting</li>
                  <li>Anonymous usage analytics</li>
                </ul>

                <h2>Account Suspension and Termination</h2>

                <h3>Grounds for Suspension</h3>
                <p>We may suspend or terminate access for:</p>
                <ul>
                  <li><strong>Terms Violation:</strong> Breach of these Terms of Use</li>
                  <li><strong>Abuse:</strong> Excessive usage or system interference</li>
                  <li><strong>Unlawful Use:</strong> Illegal or fraudulent activities</li>
                  <li><strong>Security Risks:</strong> Compromised accounts or suspicious activity</li>
                </ul>

                <h3>Effect of Termination</h3>
                <p>Upon termination:</p>
                <ul>
                  <li>Access to CapSight services will cease immediately</li>
                  <li>Previously obtained valuations remain subject to these Terms</li>
                  <li>Data retention follows our Privacy Policy</li>
                </ul>

                <h2>Changes to Service and Terms</h2>

                <h3>Service Updates</h3>
                <p>CapSight may:</p>
                <ul>
                  <li>Update valuation methodology and algorithms</li>
                  <li>Add or remove markets and features</li>
                  <li>Change pricing or usage limits</li>
                  <li>Discontinue service with reasonable notice</li>
                </ul>

                <h3>Terms Updates</h3>
                <p>
                  We may modify these Terms at any time. Material changes will be communicated through:
                </p>
                <ul>
                  <li>Prominent website notice</li>
                  <li>Email notification (if available)</li>
                  <li>API response headers</li>
                </ul>

                <h2>Governing Law and Disputes</h2>

                <div className="bg-red-50 border-l-4 border-red-400 p-4 my-4">
                  <p className="text-red-800">
                    <strong>⚖️ Legal Counsel Required:</strong> Governing law, jurisdiction, and dispute 
                    resolution clauses must be drafted by qualified legal counsel.
                  </p>
                </div>

                <h3>Governing Law</h3>
                <p>
                  These Terms shall be governed by the laws of [STATE TO BE DETERMINED BY COUNSEL], 
                  without regard to conflict of law principles.
                </p>

                <h3>Dispute Resolution</h3>
                <p>
                  [DISPUTE RESOLUTION MECHANISM TO BE DETERMINED BY COUNSEL - may include arbitration, 
                  mediation, or court jurisdiction requirements]
                </p>

                <h2>Contact Information</h2>

                <p>
                  For questions about these Terms of Use:
                </p>

                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-4">
                  <p><strong>CapSight Legal Team</strong></p>
                  <p>Email: <a href="mailto:legal@capsight.com" className="text-blue-600 hover:text-blue-800 underline">legal@capsight.com</a></p>
                  <p>General Support: <a href="mailto:support@capsight.com" className="text-blue-600 hover:text-blue-800 underline">support@capsight.com</a></p>
                  <p>Mailing Address:</p>
                  <p className="ml-4">
                    CapSight, LLC<br />
                    Legal Department<br />
                    [Address to be provided by legal counsel]<br />
                    [City, State, ZIP Code]
                  </p>
                </div>

                <h2>Miscellaneous</h2>

                <h3>Severability</h3>
                <p>
                  If any provision of these Terms is found unenforceable, the remainder shall remain in full effect.
                </p>

                <h3>Entire Agreement</h3>
                <p>
                  These Terms, together with our Privacy Policy, constitute the entire agreement between 
                  you and CapSight regarding use of our service.
                </p>

                <h3>No Waiver</h3>
                <p>
                  Our failure to enforce any right or provision of these Terms shall not constitute a waiver 
                  of such right or provision.
                </p>

                <div className="bg-red-50 border border-red-200 rounded-lg p-6 mt-8">
                  <h3 className="text-red-800 font-semibold mb-2">⚖️ Legal Review Required</h3>
                  <p className="text-red-700 text-sm">
                    This Terms of Use template requires comprehensive review by qualified legal counsel 
                    to ensure compliance with:
                  </p>
                  <ul className="text-red-700 text-sm mt-2 space-y-1">
                    <li>• Applicable state and federal contract law</li>
                    <li>• Industry-specific regulations (real estate, technology)</li>
                    <li>• Liability limitation enforceability</li>
                    <li>• Dispute resolution and jurisdiction requirements</li>
                    <li>• Consumer protection laws</li>
                  </ul>
                  <p className="text-red-700 text-sm mt-2">
                    <strong>Do not use these terms in production without legal review and approval.</strong>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
