import React from 'react'
import { PropertyFinder } from '../components/PropertyFinder'

export default function PropertySearchPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            CRE Investment Property Finder
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            AI-powered commercial real estate analysis. Enter any city to discover 
            the top 5 investment opportunities based on market data, cap rates, 
            and growth potential.
          </p>
        </div>

        <PropertyFinder />

        <div className="mt-16 text-center">
          <div className="bg-blue-50 rounded-lg p-8 max-w-4xl mx-auto">
            <h2 className="text-2xl font-semibold text-blue-900 mb-4">
              How Our AI Analysis Works
            </h2>
            <div className="grid md:grid-cols-3 gap-6 text-left">
              <div className="bg-white rounded-lg p-6">
                <div className="text-3xl mb-3">📊</div>
                <h3 className="font-semibold text-gray-900 mb-2">Market Analysis</h3>
                <p className="text-gray-600 text-sm">
                  Real-time vacancy rates, rent growth trends, and market fundamentals
                  from 12+ months of commercial property data.
                </p>
              </div>
              <div className="bg-white rounded-lg p-6">
                <div className="text-3xl mb-3">🤖</div>
                <h3 className="font-semibold text-gray-900 mb-2">ML Scoring</h3>
                <p className="text-gray-600 text-sm">
                  Machine learning models evaluate cap rates, NOI potential, 
                  building quality, and investment risk factors.
                </p>
              </div>
              <div className="bg-white rounded-lg p-6">
                <div className="text-3xl mb-3">📈</div>
                <h3 className="font-semibold text-gray-900 mb-2">Investment Grade</h3>
                <p className="text-gray-600 text-sm">
                  Institutional-quality analysis with confidence scoring and
                  detailed reasoning for each recommendation.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Add this for Next.js static generation if needed
export async function getStaticProps() {
  return {
    props: {
      title: 'Property Finder - CRE Investment Analysis'
    }
  }
}
