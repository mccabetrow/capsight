'use client'

import { useDemo } from '@/hooks/useDemo'

export default function DemoRibbon() {
  const { isDemoMode } = useDemo()

  if (!isDemoMode) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-amber-500 to-orange-500 text-white py-2 px-4 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <svg className="h-5 w-5 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="font-bold text-lg">DEMO MODE</span>
          </div>
          <span className="text-amber-100">•</span>
          <span className="text-sm">Sample Data Only - No Real Transactions</span>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="hidden sm:flex items-center space-x-1 text-xs text-amber-100">
            <span>🔒 Addresses Masked</span>
            <span>•</span>
            <span>🚫 No Network Writes</span>
          </div>
        </div>
      </div>
    </div>
  )
}
