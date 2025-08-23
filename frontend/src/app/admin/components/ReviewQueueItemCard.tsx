'use client'

import { useState } from 'react'
import { ReviewQueueItem } from '../types'
import { approveReviewItem, rejectReviewItem } from '../actions'
import { formatDate, formatDateTime } from '../lib/utils'

interface ReviewQueueItemCardProps {
  item: ReviewQueueItem
}

export default function ReviewQueueItemCard({ item }: ReviewQueueItemCardProps) {
  const [isApproving, setIsApproving] = useState(false)
  const [isRejecting, setIsRejecting] = useState(false)
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [rejectComment, setRejectComment] = useState('')
  const [approveComment, setApproveComment] = useState('')
  const [showApproveForm, setShowApproveForm] = useState(false)

  const handleApprove = async () => {
    setIsApproving(true)
    try {
      await approveReviewItem(item.id, approveComment || undefined)
      setShowApproveForm(false)
      setApproveComment('')
    } catch (error) {
      console.error('Failed to approve item:', error)
      alert('Failed to approve item')
    } finally {
      setIsApproving(false)
    }
  }

  const handleReject = async () => {
    if (!rejectComment.trim()) {
      alert('Rejection comment is required')
      return
    }

    setIsRejecting(true)
    try {
      await rejectReviewItem(item.id, rejectComment)
      setShowRejectForm(false)
      setRejectComment('')
    } catch (error) {
      console.error('Failed to reject item:', error)
      alert('Failed to reject item')
    } finally {
      setIsRejecting(false)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-gray-900">{item.address}</h3>
            <div className={`px-2 py-1 rounded-full border text-xs font-medium ${getSeverityColor(item.severity)}`}>
              {item.severity.toUpperCase()}
            </div>
          </div>
          <div className="text-sm text-gray-600">
            {item.market_slug.toUpperCase()} • Sale Date: {formatDate(item.sale_date)}
          </div>
        </div>
      </div>

      {/* Property Details */}
      <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-gray-50 rounded-md">
        <div>
          <div className="text-sm font-medium text-gray-900">
            ${item.price_total_usd.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500">Total Price</div>
        </div>
        <div>
          <div className="text-sm font-medium text-gray-900">
            {item.building_sf.toLocaleString()} SF
          </div>
          <div className="text-xs text-gray-500">Building Size</div>
        </div>
        <div>
          <div className="text-sm font-medium text-gray-900">
            {item.cap_rate_pct.toFixed(2)}%
          </div>
          <div className="text-xs text-gray-500">Cap Rate</div>
        </div>
      </div>

      {/* Issue Reason */}
      <div className="mb-4">
        <div className="text-sm font-medium text-gray-900 mb-1">Issue:</div>
        <div className="text-sm text-gray-700 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          {item.reason}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          Flagged {formatDateTime(item.created_at)}
        </div>
        
        <div className="flex space-x-2">
          {!showApproveForm && !showRejectForm && (
            <>
              <button
                onClick={() => setShowApproveForm(true)}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                Approve
              </button>
              <button
                onClick={() => setShowRejectForm(true)}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Reject
              </button>
            </>
          )}
        </div>
      </div>

      {/* Approve Form */}
      {showApproveForm && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Approval Comment (Optional)
            </label>
            <textarea
              value={approveComment}
              onChange={(e) => setApproveComment(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              rows={2}
              placeholder="Any notes about this approval..."
            />
          </div>
          <div className="flex justify-end space-x-2">
            <button
              onClick={() => {
                setShowApproveForm(false)
                setApproveComment('')
              }}
              className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              onClick={handleApprove}
              disabled={isApproving}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isApproving && (
                <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              )}
              Confirm Approval
            </button>
          </div>
        </div>
      )}

      {/* Reject Form */}
      {showRejectForm && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Rejection Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm"
              rows={3}
              placeholder="Explain why this item is being rejected..."
              required
            />
          </div>
          <div className="flex justify-end space-x-2">
            <button
              onClick={() => {
                setShowRejectForm(false)
                setRejectComment('')
              }}
              className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              onClick={handleReject}
              disabled={isRejecting || !rejectComment.trim()}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRejecting && (
                <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              )}
              Confirm Rejection
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
