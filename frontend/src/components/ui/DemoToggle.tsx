'use client'

import { useDemo } from '@/hooks/useDemo'

export default function DemoToggle() {
  const { isDemoMode, toggleDemo } = useDemo()

  // Only show in development
  if (process.env.NODE_ENV !== 'development') {
    return null
  }

  return (
    <div className="fixed bottom-4 right-4 z-40">
      <button
        onClick={toggleDemo}
        className={`flex items-center space-x-2 px-4 py-2 rounded-lg shadow-lg border font-medium transition-all ${
          isDemoMode
            ? 'bg-amber-500 text-white border-amber-600 hover:bg-amber-600'
            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
        }`}
        title={isDemoMode ? 'Exit Demo Mode' : 'Enter Demo Mode'}
      >
        <div className={`w-2 h-2 rounded-full ${
          isDemoMode ? 'bg-white animate-pulse' : 'bg-gray-400'
        }`} />
        <span className="text-sm">
          {isDemoMode ? 'Demo ON' : 'Demo OFF'}
        </span>
      </button>
    </div>
  )
}
