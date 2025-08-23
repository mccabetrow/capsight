import React from 'react';
import Head from 'next/head';

export default function PrivacyPolicy() {
  const lastUpdated = "August 23, 2025";

  return (
    <>
      <Head>
        <title>Privacy Policy - CapSight</title>
        <meta name="description" content="CapSight privacy policy and data handling practices" />
      </Head>
      
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white shadow-sm rounded-lg">
            <div className="px-6 py-8">
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Privacy Policy</h1>
                <p className="mt-2 text-sm text-gray-500">Last updated: {lastUpdated}</p>
              </div>

              <div className="prose prose-lg max-w-none">
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
                  <p className="text-blue-700">
                    <strong>Plain English Summary:</strong> CapSight collects minimal data to provide 
                    CRE valuations. We don't sell your information, use strong security measures, 
                    and give you control over your data.
                  </p>
                </div>

                <h2>Information We Collect</h2>

                <h3>Valuation Requests</h3>
                <p>
                  When you request property valuations, we collect and process:
                </p>
                <ul>
                  <li><strong>Property Details:</strong> Market location, building square footage, annual NOI, year built (optional)</li>
                  <li><strong>Request Metadata:</strong> Timestamp, IP address, user agent for rate limiting and security</li>
                  <li><strong>Session Data:</strong> Temporary session identifiers for service continuity</li>
                </ul>

                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 my-4">
                  <p className="text-yellow-800">
                    <strong>Important:</strong> We do not collect property addresses, owner names, 
                    or other personally identifiable information about specific properties.
                  </p>
                </div>

                <h3>Usage Analytics</h3>
                <p>
                  We collect aggregated usage data to improve our service:
                </p>
                <ul>
                  <li>API endpoint usage patterns</li>
                  <li>Response times and error rates</li>
                  <li>Market popularity and feature usage</li>
                  <li>General geographic regions (not specific locations)</li>
                </ul>

                <h3>Cookies and Tracking</h3>
                <p>
                  CapSight uses minimal cookies for essential functions:
                </p>
                <ul>
                  <li><strong>Essential Cookies:</strong> Session management, rate limiting, security</li>
                  <li><strong>Analytics Cookies:</strong> Aggregated usage statistics (anonymous)</li>
                  <li><strong>No Third-Party Tracking:</strong> We don't use advertising or marketing cookies</li>
                </ul>

                <h2>How We Use Information</h2>

                <h3>Primary Purposes</h3>
                <ul>
                  <li><strong>Valuation Services:</strong> Process property valuations and provide estimates</li>
                  <li><strong>Quality Assurance:</strong> Monitor accuracy and improve methodology</li>
                  <li><strong>Security:</strong> Prevent abuse, rate limiting, and fraud detection</li>
                  <li><strong>Support:</strong> Respond to technical issues and user inquiries</li>
                </ul>

                <h3>Data Processing Legal Basis</h3>
                <p>
                  We process your data based on:
                </p>
                <ul>
                  <li><strong>Legitimate Interest:</strong> Providing accurate CRE valuation services</li>
                  <li><strong>Service Performance:</strong> Delivering requested valuations and maintaining quality</li>
                  <li><strong>Legal Compliance:</strong> Meeting regulatory requirements and industry standards</li>
                </ul>

                <h2>Data Sharing and Disclosure</h2>

                <h3>We Do Not Sell Data</h3>
                <p>
                  CapSight does not sell, rent, or trade your personal information or property data to third parties.
                </p>

                <h3>Limited Sharing</h3>
                <p>
                  We may share aggregated, non-identifying data with:
                </p>
                <ul>
                  <li><strong>Service Providers:</strong> Cloud infrastructure, security monitoring (under strict confidentiality)</li>
                  <li><strong>Legal Requirements:</strong> When required by law, court order, or regulatory request</li>
                  <li><strong>Business Transfer:</strong> In case of merger or acquisition (with user notification)</li>
                </ul>

                <div className="bg-red-50 border-l-4 border-red-400 p-4 my-4">
                  <p className="text-red-800">
                    <strong>⚖️ Legal Counsel Recommended:</strong> This section requires review by legal counsel 
                    for compliance with GDPR, CCPA, and other privacy regulations.
                  </p>
                </div>

                <h2>Data Security</h2>

                <h3>Security Measures</h3>
                <p>
                  We implement industry-standard security practices:
                </p>
                <ul>
                  <li><strong>Encryption:</strong> TLS 1.3 for data in transit, AES-256 for data at rest</li>
                  <li><strong>Access Controls:</strong> Role-based access, multi-factor authentication</li>
                  <li><strong>Network Security:</strong> Firewalls, intrusion detection, rate limiting</li>
                  <li><strong>Regular Audits:</strong> Security assessments and vulnerability testing</li>
                </ul>

                <h3>Data Retention</h3>
                <ul>
                  <li><strong>Valuation Requests:</strong> Retained for 2 years for accuracy monitoring</li>
                  <li><strong>Session Data:</strong> Automatically deleted after 24 hours</li>
                  <li><strong>Analytics Data:</strong> Aggregated data retained indefinitely (no personal identifiers)</li>
                  <li><strong>Audit Logs:</strong> Security logs retained for 1 year</li>
                </ul>

                <h2>Your Rights and Choices</h2>

                <h3>Data Subject Rights</h3>
                <p>
                  You have the right to:
                </p>
                <ul>
                  <li><strong>Access:</strong> Request information about data we hold about you</li>
                  <li><strong>Correction:</strong> Request correction of inaccurate information</li>
                  <li><strong>Deletion:</strong> Request deletion of your data (subject to legal requirements)</li>
                  <li><strong>Portability:</strong> Request export of your data in machine-readable format</li>
                  <li><strong>Objection:</strong> Object to processing for direct marketing or research</li>
                </ul>

                <h3>Exercising Your Rights</h3>
                <p>
                  To exercise these rights, contact us at{' '}
                  <a href="mailto:privacy@capsight.com" className="text-blue-600 hover:text-blue-800 underline">
                    privacy@capsight.com
                  </a>
                  {' '}with:
                </p>
                <ul>
                  <li>Clear description of your request</li>
                  <li>Verification of your identity</li>
                  <li>Specific time period or data categories (if applicable)</li>
                </ul>

                <h2>Third-Party Services</h2>

                <h3>Service Providers</h3>
                <p>
                  CapSight uses these third-party services:
                </p>
                <ul>
                  <li><strong>Supabase:</strong> Database hosting and authentication (privacy policy: supabase.com/privacy)</li>
                  <li><strong>Vercel:</strong> Web hosting and CDN (privacy policy: vercel.com/legal/privacy-policy)</li>
                  <li><strong>Cloudflare:</strong> Security and performance (privacy policy: cloudflare.com/privacypolicy/)</li>
                </ul>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 my-4">
                  <p className="text-blue-700">
                    All service providers are bound by strict data processing agreements and 
                    cannot use your data for their own purposes.
                  </p>
                </div>

                <h2>CRE Industry Specific</h2>

                <h3>Non-USPAP Disclosure</h3>
                <p>
                  <strong>Important Notice:</strong> CapSight valuations are analytical estimates for informational 
                  purposes only and do not constitute formal appraisals under the Uniform Standards of Professional 
                  Appraisal Practice (USPAP). Our estimates:
                </p>
                <ul>
                  <li>Are not suitable for lending, legal, or official purposes</li>
                  <li>Should not replace professional appraisals</li>
                  <li>Are based on comparable sales data and statistical models</li>
                  <li>May not reflect current market conditions or property-specific factors</li>
                </ul>

                <h3>Data Sources</h3>
                <p>
                  Our valuations are based on:
                </p>
                <ul>
                  <li>Publicly available commercial real estate transaction data</li>
                  <li>Property records from county assessors and MLS systems</li>
                  <li>Broker-provided comparable sales (verified when possible)</li>
                  <li>Market research from commercial real estate databases</li>
                </ul>

                <h2>International Users</h2>

                <h3>Data Transfers</h3>
                <p>
                  CapSight is based in the United States. If you access our service from outside the US, 
                  your data may be transferred to and processed in the United States. We ensure adequate 
                  protection through:
                </p>
                <ul>
                  <li>Standard Contractual Clauses (SCCs) for EU data transfers</li>
                  <li>Adequate security measures equivalent to your jurisdiction</li>
                  <li>Compliance with applicable international privacy laws</li>
                </ul>

                <h2>Changes to This Policy</h2>

                <p>
                  We may update this privacy policy periodically. Changes will be posted here with an 
                  updated "Last Modified" date. Material changes will be communicated via:
                </p>
                <ul>
                  <li>Email notification (if we have your email address)</li>
                  <li>Prominent notice on our website</li>
                  <li>API response headers indicating policy updates</li>
                </ul>

                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 my-4">
                  <p className="text-yellow-800">
                    <strong>⚖️ Legal Counsel Recommended:</strong> Privacy policy updates and notification 
                    procedures should be reviewed for compliance with applicable privacy laws.
                  </p>
                </div>

                <h2>Contact Information</h2>

                <p>
                  For privacy-related questions or concerns:
                </p>

                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-4">
                  <p><strong>CapSight Privacy Team</strong></p>
                  <p>Email: <a href="mailto:privacy@capsight.com" className="text-blue-600 hover:text-blue-800 underline">privacy@capsight.com</a></p>
                  <p>Mailing Address:</p>
                  <p className="ml-4">
                    CapSight, LLC<br />
                    Privacy Officer<br />
                    [Address to be provided by legal counsel]<br />
                    [City, State, ZIP Code]
                  </p>
                  <p className="mt-2 text-sm text-gray-600">
                    Response time: We aim to respond to privacy requests within 30 days.
                  </p>
                </div>

                <div className="bg-red-50 border border-red-200 rounded-lg p-6 mt-8">
                  <h3 className="text-red-800 font-semibold mb-2">⚖️ Legal Review Required</h3>
                  <p className="text-red-700 text-sm">
                    This privacy policy template requires comprehensive review by qualified legal counsel 
                    to ensure compliance with:
                  </p>
                  <ul className="text-red-700 text-sm mt-2 space-y-1">
                    <li>• GDPR (EU General Data Protection Regulation)</li>
                    <li>• CCPA (California Consumer Privacy Act)</li>
                    <li>• State-specific privacy laws</li>
                    <li>• Industry-specific regulations (real estate, financial services)</li>
                    <li>• Cross-border data transfer requirements</li>
                  </ul>
                  <p className="text-red-700 text-sm mt-2">
                    <strong>Do not use this policy in production without legal review and approval.</strong>
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
