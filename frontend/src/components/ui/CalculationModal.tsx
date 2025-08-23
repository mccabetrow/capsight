'use client'

import { useState, useEffect, useRef } from 'react'
import { DemoData } from '@/hooks/useDemo'

interface CalculationModalProps {
  isOpen: boolean
  onClose: () => void
  data: DemoData | any // Support both demo and real data
}

export default function CalculationModal({ isOpen, onClose, data }: CalculationModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  // Trap focus within modal
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
        return
      }

      if (event.key === 'Tab') {
        const focusableElements = modalRef.current?.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        
        if (!focusableElements || focusableElements.length === 0) return

        const firstElement = focusableElements[0] as HTMLElement
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

        if (event.shiftKey) {
          if (document.activeElement === firstElement) {
            event.preventDefault()
            lastElement.focus()
          }
        } else {
          if (document.activeElement === lastElement) {
            event.preventDefault()
            firstElement.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    
    // Focus the close button when modal opens
    if (closeButtonRef.current) {
      closeButtonRef.current.focus()
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }

    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  if (!isOpen || !data) return null

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  const formatDistance = (miles: number) => {
    return `${miles.toFixed(1)} mi`
  }

  const getBadgeColor = (reason: string) => {
    const colors: Record<string, string> = {
      'low_sample': 'bg-yellow-100 text-yellow-800 border-yellow-300',
      'high_dispersion': 'bg-orange-100 text-orange-800 border-orange-300',
      'stale': 'bg-red-100 text-red-800 border-red-300'
    }
    return colors[reason] || 'bg-gray-100 text-gray-800 border-gray-300'
  }

  const fallbackLabels: Record<string, string> = {
    'low_sample': 'Low Sample Size',
    'high_dispersion': 'High Dispersion',
    'stale': 'Stale Data'
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="calculation-modal-title">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div 
          ref={modalRef}
          className="relative transform overflow-hidden rounded-lg bg-white shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 id="calculation-modal-title" className="text-lg font-semibold text-gray-900">
                How this was calculated
              </h3>
              <button
                ref={closeButtonRef}
                onClick={onClose}
                className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Close modal"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-4 max-h-96 overflow-y-auto">
            <div className="space-y-6">
              {/* Method Information */}
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">Method & Version</h4>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-500">Method</div>
                      <div className="font-medium capitalize">
                        {data.method?.replace(/_/g, ' ') || 'Not specified'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Version</div>
                      <div className="font-medium font-mono">
                        {data.method_version || 'Not specified'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Adjustments Summary */}
              {data.calculation_details && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">Adjustments Applied</h4>
                  <div className="space-y-3">
                    {data.calculation_details.time_adjustment_summary && (
                      <div className="border border-gray-200 rounded-lg p-4">
                        <div className="text-sm font-medium text-gray-900 mb-1">Time Adjustment</div>
                        <div className="text-sm text-gray-700">{data.calculation_details.time_adjustment_summary}</div>
                      </div>
                    )}
                    
                    {data.calculation_details.outlier_trim_details && (
                      <div className="border border-gray-200 rounded-lg p-4">
                        <div className="text-sm font-medium text-gray-900 mb-1">
                          Outlier Removal ({data.outliers_removed || 0} properties)
                        </div>
                        <div className="text-sm text-gray-700">{data.calculation_details.outlier_trim_details}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Fallback Reasons */}
              {data.fallback_reasons && data.fallback_reasons.length > 0 && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">Fallback Conditions</h4>
                  <div className="flex flex-wrap gap-2">
                    {data.fallback_reasons.map((reason: string, index: number) => (
                      <span
                        key={index}
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getBadgeColor(reason)}`}
                      >
                        {fallbackLabels[reason] || reason}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Top Comparables */}
              {data.top_comps && data.top_comps.length > 0 && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">
                    Top 5 Comparable Sales
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Address
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Sale Date
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Distance
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Adj. Cap Rate
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Weight
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Price
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {data.top_comps.slice(0, 5).map((comp: any, index: number) => (
                          <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                            <td className="px-3 py-2 text-sm font-mono text-gray-900">
                              {comp.masked_address || comp.address || 'Not available'}
                            </td>
                            <td className="px-3 py-2 text-sm text-gray-900">
                              {new Date(comp.sale_date).toLocaleDateString()}
                            </td>
                            <td className="px-3 py-2 text-sm text-gray-900">
                              {formatDistance(comp.distance_mi)}
                            </td>
                            <td className="px-3 py-2 text-sm text-gray-900">
                              {formatPercent(comp.adj_cap_rate || comp.cap_rate || 0)}
                            </td>
                            <td className="px-3 py-2 text-sm text-gray-900">
                              {formatPercent(comp.weight)}
                            </td>
                            <td className="px-3 py-2 text-sm text-gray-900">
                              {formatCurrency(comp.price_total_usd)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Data Quality Metrics */}
              {data.calculation_details && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">Data Quality</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-900">
                        {data.comp_count || 0}
                      </div>
                      <div className="text-xs text-gray-500">Comparables Used</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-900 capitalize">
                        {data.calculation_details.sample_quality || 'Unknown'}
                      </div>
                      <div className="text-xs text-gray-500">Sample Quality</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-900">
                        {data.calculation_details.dispersion_coefficient 
                          ? (data.calculation_details.dispersion_coefficient * 100).toFixed(1) + '%'
                          : 'N/A'}
                      </div>
                      <div className="text-xs text-gray-500">Dispersion</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
