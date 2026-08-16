import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ScamShield AI - Website Scam Risk Detector',
  description:
    'Zero-cost, multi-signal website safety scanner. SSL, domain age, DNS, content heuristics, typosquatting, OpenPhish, URLhaus and a local ML classifier - 0-100 risk score in seconds, no API keys required.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
          {children}
        </div>
      </body>
    </html>
  )
}