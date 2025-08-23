import type { Metadata } from 'next'
import './globals.css'
import DemoRibbon from '@/components/ui/DemoRibbon'
import DemoToggle from '@/components/ui/DemoToggle'
import FeedbackWidget from '@/components/ui/FeedbackWidget'

export const metadata: Metadata = {
  title: 'CapSight - Commercial Real Estate Valuation',
  description: 'Accurate, data-driven commercial real estate valuations powered by advanced analytics',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <DemoRibbon />
        <main className="relative">
          {children}
        </main>
        <DemoToggle />
        <FeedbackWidget />
      </body>
    </html>
  )
}
