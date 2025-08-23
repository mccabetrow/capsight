'use client'

import { ReviewQueueItem } from '../types'
import ReviewQueueItemCard from './ReviewQueueItemCard'

interface ReviewQueueTabProps {
  items: ReviewQueueItem[]
  isLoading: boolean
}

export default function ReviewQueueTab({ items, isLoading }: ReviewQueueTabProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-gray-200 h-48 rounded-lg mb-4" />
          ))}
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-green-500 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Review Queue Clear</h3>
        <p className="text-gray-600">
          All flagged properties have been reviewed. Great work!
        </p>
      </div>
    )
  }

  // Group by severity for better organization
  const groupedItems = items.reduce((acc, item) => {
    if (!acc[item.severity]) {
      acc[item.severity] = []
    }
    acc[item.severity].push(item)
    return acc
  }, {} as Record<string, ReviewQueueItem[]>)

  const severityOrder = ['high', 'medium', 'low']

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Review Queue ({items.length} items)
        </h2>
        <div className="flex items-center space-x-4 text-sm text-gray-600">
          {severityOrder.map(severity => {
            const count = groupedItems[severity]?.length || 0
            if (count === 0) return null
            
            const colors = {
              high: 'text-red-600',
              medium: 'text-yellow-600', 
              low: 'text-green-600'
            }
            
            return (
              <div key={severity} className={`flex items-center ${colors[severity as keyof typeof colors]}`}>
                <div className="w-2 h-2 rounded-full bg-current mr-1" />
                {count} {severity}
              </div>
            )
          })}
        </div>
      </div>

      {severityOrder.map(severity => {
        const severityItems = groupedItems[severity]
        if (!severityItems || severityItems.length === 0) return null

        return (
          <div key={severity}>
            <h3 className="text-md font-medium text-gray-800 mb-4 capitalize">
              {severity} Priority ({severityItems.length})
            </h3>
            <div className="space-y-4">
              {severityItems.map(item => (
                <ReviewQueueItemCard key={item.id} item={item} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
