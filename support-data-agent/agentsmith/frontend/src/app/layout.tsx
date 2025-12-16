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
        <div className="min-h-screen bg-navy-900">
          <nav className="bg-navy-950 border-b border-navy-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <Link href="/" className="flex items-center">
                    <span className="text-xl font-semibold text-text-primary tracking-wide">AgentSmith</span>
                  </Link>
                  <div className="hidden sm:ml-8 sm:flex sm:space-x-6">
                    <Link href="/projects" className="inline-flex items-center px-1 pt-1 text-sm font-medium text-text-secondary hover:text-cyan-400 transition-colors">
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
