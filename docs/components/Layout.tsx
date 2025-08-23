import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'

interface LayoutProps {
  children: React.ReactNode
}

const navigation = [
  { name: 'Home', href: '/' },
  { name: 'Methodology', href: '/methodology' },
  { name: 'API Reference', href: '/api-reference' },
  { name: 'Operations', href: '/operations' },
  { name: 'Accuracy & SLA', href: '/accuracy' },
  { name: 'Changelog', href: '/changelog' },
]

export default function Layout({ children }: LayoutProps) {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-primary-600">
                CapSight Docs
              </Link>
              <span className="ml-2 text-sm text-gray-500">v1.0</span>
            </div>
            <nav className="hidden md:flex space-x-6">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`text-sm font-medium transition-colors ${
                    router.pathname === item.href
                      ? 'text-primary-600 border-b-2 border-primary-600 pb-1'
                      : 'text-gray-600 hover:text-primary-600'
                  }`}
                >
                  {item.name}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex">
          {/* Sidebar */}
          <aside className="w-64 hidden lg:block">
            <nav className="sticky top-8">
              <ul className="space-y-2">
                {navigation.map((item) => (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={`block px-3 py-2 text-sm rounded-md transition-colors ${
                        router.pathname === item.href
                          ? 'bg-primary-50 text-primary-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }`}
                    >
                      {item.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>

          {/* Content */}
          <main className="flex-1 lg:ml-8">
            <div className="prose prose-lg max-w-none">
              {children}
            </div>
          </main>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-500">
              © 2025 CapSight. Documentation v1.0
            </div>
            <div className="flex space-x-6 text-sm">
              <a href="/legal/privacy" className="text-gray-500 hover:text-primary-600">
                Privacy Policy
              </a>
              <a href="/legal/terms" className="text-gray-500 hover:text-primary-600">
                Terms of Use
              </a>
              <a href="https://github.com/capsight/issues" className="text-gray-500 hover:text-primary-600">
                Report Issue
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
