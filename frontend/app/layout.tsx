import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Website Scam Risk Detector',
  description: 'Check if a website is safe or a scam — instant risk score and detailed breakdown',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  )
}
