import '../styles/globals.css'
import type { AppProps } from 'next/app'
import Link from 'next/link'

const Navigation = () => (
  <nav className="bg-white shadow-lg">
    <div className="max-w-7xl mx-auto px-4">
      <div className="flex justify-between items-center py-4">
        <div className="flex items-center space-x-8">
          <Link href="/" className="text-xl font-bold text-blue-600">
            CRE Valuator
          </Link>
          <div className="hidden md:flex space-x-6">
            <Link href="/" className="text-gray-700 hover:text-blue-600">
              Valuation
            </Link>
            <Link href="/properties" className="text-gray-700 hover:text-blue-600">
              Property Finder
            </Link>
            <Link href="/admin" className="text-gray-700 hover:text-blue-600">
              Admin
            </Link>
            <Link href="/docs" className="text-gray-700 hover:text-blue-600">
              Docs
            </Link>
          </div>
        </div>
        <div className="text-sm text-gray-500">
          AI-Powered CRE Analysis
        </div>
      </div>
    </div>
  </nav>
)

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Navigation />
      <Component {...pageProps} />
    </>
  )
}
