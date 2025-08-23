import type { Metadata } from 'next'
import '../styles/globals.css'

export const metadata: Metadata = {
  title: 'CapSight - Industrial valuations in seconds',
  description: 'Get transparent industrial CRE value ranges backed by verified comps. Enter NOI and get instant valuations with ±50 bps confidence bands.',
  keywords: 'industrial real estate, CRE valuation, cap rates, property valuation, commercial real estate',
  openGraph: {
    title: 'CapSight - Industrial valuations in seconds',
    description: 'Get transparent industrial CRE value ranges backed by verified comps.',
    url: 'https://capsight.com',
    siteName: 'CapSight',
    images: [
      {
        url: '/og.jpg',
        width: 1200,
        height: 630,
        alt: 'CapSight - Industrial valuations in seconds',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CapSight - Industrial valuations in seconds',
    description: 'Get transparent industrial CRE value ranges backed by verified comps.',
    images: ['/og.jpg'],
  },
  viewport: 'width=device-width, initial-scale=1',
  robots: 'index, follow',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossOrigin="" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body className="min-h-screen bg-gray-50 font-sans antialiased">
        <header className="border-b border-gray-200 bg-white">
          <div className="container mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold text-gray-900">CapSight</h1>
            </div>
            <a
              href="#demo"
              className="btn btn-secondary focus-ring"
              aria-label="Book a demo"
            >
              Book a Demo
            </a>
          </div>
        </header>
        <main className="flex-1">
          {children}
        </main>
      </body>
    </html>
  )
}
