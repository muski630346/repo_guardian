import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const inter = Inter({ 
  subsets: ["latin"],
  variable: '--font-inter',
})

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ["latin"],
  variable: '--font-jetbrains',
})

export const metadata: Metadata = {
  title: 'RepoGuardian AI | Autonomous Security Command Center',
  description: 'Next-generation AI-powered cybersecurity platform. Protect your repositories with autonomous threat detection, intelligent remediation, and real-time security orchestration.',
  keywords: ['cybersecurity', 'AI security', 'repository protection', 'threat detection', 'autonomous agents'],
}

export const viewport: Viewport = {
  themeColor: '#050505',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark bg-[#050505]">
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-[#050505] text-white min-h-screen overflow-x-hidden`}>
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
