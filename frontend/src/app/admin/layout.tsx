import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'CapSight Admin Console',
  description: 'Admin dashboard for monitoring accuracy, markets, and review queue',
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {children}
    </div>
  )
}
