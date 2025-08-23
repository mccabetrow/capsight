import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md mx-auto text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-6">
          CapSight
        </h1>
        <p className="text-lg text-gray-600 mb-8">
          Commercial Real Estate Valuation Platform
        </p>
        
        <div className="space-y-4">
          <Link
            href="/valuation"
            className="block w-full px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Get Property Valuation
          </Link>
          
          <Link
            href="/admin"
            className="block w-full px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Admin Console
          </Link>
        </div>
        
        <div className="mt-8 text-sm text-gray-500">
          <p>Try demo mode to explore with sample data</p>
          <p className="mt-1">Add <code className="bg-gray-100 px-1 rounded">?demo=1</code> to any URL</p>
        </div>
      </div>
    </div>
  )
}
