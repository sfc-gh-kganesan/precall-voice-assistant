import type { Metadata } from "next"
import "./globals.css"
import Link from "next/link"

export const metadata: Metadata = {
  title: "AgentSmith - Chatbot Performance Analysis Platform",
  description: "Analyze chatbot conversations and optimize agent design",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen bg-slate-950">
          <nav className="bg-slate-900 border-b-2 border-slate-700">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <Link href="/" className="flex items-center">
                    <span className="text-xl font-serif font-semibold text-parchment-100 tracking-wide">AgentSmith</span>
                  </Link>
                  <div className="hidden sm:ml-8 sm:flex sm:space-x-6">
                    <Link href="/projects" className="inline-flex items-center px-1 pt-1 text-sm font-medium text-parchment-200 hover:text-parchment-50 transition-colors">
                      Deployments
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </nav>
          <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
