'use client'

import { useState, useEffect } from 'react'
import { AccuracyMetrics, MarketStatus, ReviewQueueItem } from './types'
import { getAccuracyMetrics, getMarketStatus, getReviewQueue } from './actions'
import AccuracyCard from './components/AccuracyCard'
import MarketCard from './components/MarketCard'
import ReviewQueueTab from './components/ReviewQueueTab'
import FeedbackTab from './FeedbackTab'

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<'accuracy' | 'markets' | 'review' | 'feedback'>('accuracy')
  const [accuracyMetrics, setAccuracyMetrics] = useState<AccuracyMetrics | null>(null)
  const [marketStatus, setMarketStatus] = useState<MarketStatus[]>([])
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([])
  const [isLoadingAccuracy, setIsLoadingAccuracy] = useState(false)
  const [isLoadingMarkets, setIsLoadingMarkets] = useState(false)
  const [isLoadingReview, setIsLoadingReview] = useState(false)

  // Load accuracy metrics
  useEffect(() => {
    if (activeTab === 'accuracy') {
      setIsLoadingAccuracy(true)
      getAccuracyMetrics()
        .then(setAccuracyMetrics)
        .catch(console.error)
        .finally(() => setIsLoadingAccuracy(false))
    }
  }, [activeTab])

  // Load market status
  useEffect(() => {
    if (activeTab === 'markets') {
      setIsLoadingMarkets(true)
      getMarketStatus()
        .then(setMarketStatus)
        .catch(console.error)
        .finally(() => setIsLoadingMarkets(false))
    }
  }, [activeTab])

  // Load review queue
  useEffect(() => {
    if (activeTab === 'review') {
      setIsLoadingReview(true)
      getReviewQueue()
        .then(setReviewQueue)
        .catch(console.error)
        .finally(() => setIsLoadingReview(false))
    }
  }, [activeTab])

  const tabs = [
    { 
      id: 'accuracy' as const, 
      label: 'Accuracy', 
      count: accuracyMetrics?.sla_breaches || 0,
      urgent: (accuracyMetrics?.sla_breaches || 0) > 0
    },
    { 
      id: 'markets' as const, 
      label: 'Markets', 
      count: marketStatus.filter(m => m.status !== 'active').length,
      urgent: marketStatus.some(m => m.status === 'down')
    },
    { 
      id: 'review' as const, 
      label: 'Review Queue', 
      count: reviewQueue.length,
      urgent: reviewQueue.some(item => item.severity === 'high')
    },
    { 
      id: 'feedback' as const, 
      label: 'Feedback', 
      count: 0, // Will be updated by FeedbackTab component
      urgent: false
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  CapSight Admin Console
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  Monitor accuracy, markets, review flagged properties, and user feedback
                </p>
              </div>
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                System Online
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="pt-6">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`group relative min-w-0 flex-1 overflow-hidden bg-white py-4 px-6 text-sm font-medium text-center hover:bg-gray-50 focus:z-10 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-500 bg-blue-50'
                    : 'text-gray-500 border-b border-gray-200'
                } rounded-t-lg border-l border-r border-t`}
                aria-current={activeTab === tab.id ? 'page' : undefined}
              >
                <div className="flex items-center justify-center space-x-2">
                  <span>{tab.label}</span>
                  {tab.count > 0 && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      tab.urgent 
                        ? 'bg-red-100 text-red-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {tab.count}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white rounded-b-lg shadow-sm border border-t-0 border-gray-200 p-6">
          {activeTab === 'accuracy' && (
            <AccuracyCard 
              metrics={accuracyMetrics} 
              isLoading={isLoadingAccuracy} 
            />
          )}
          
          {activeTab === 'markets' && (
            <div className="space-y-6">
              {isLoadingMarkets ? (
                <div className="animate-pulse space-y-4">
                  {[1, 2, 3, 4, 5].map(i => (
                    <div key={i} className="bg-gray-200 h-20 rounded-lg" />
                  ))}
                </div>
              ) : (
                marketStatus.map((market) => (
                  <MarketCard key={market.market_slug} market={market} />
                ))
              )}
            </div>
          )}

          {activeTab === 'review' && (
            <ReviewQueueTab 
              items={reviewQueue} 
              isLoading={isLoadingReview} 
            />
          )}

          {activeTab === 'feedback' && (
            <FeedbackTab />
          )}
        </div>
      </div>
    </div>
  )
}
