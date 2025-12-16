import Link from 'next/link'
import { Database, LineChart, Lightbulb } from 'lucide-react'

export default function Home() {
  return (
    <div className="px-4 py-12 sm:py-16">
      <div className="text-center max-w-5xl mx-auto">
        <h1 className="text-5xl font-semibold tracking-tight text-text-primary sm:text-6xl md:text-7xl">
          AgentSmith
        </h1>
        <p className="mt-8 text-xl leading-relaxed text-text-secondary max-w-3xl mx-auto">
          Analyze chatbot conversations to identify performance issues and optimize agent design
        </p>
        <div className="mt-12 flex items-center justify-center gap-x-6">
          <Link
            href="/projects"
            className="rounded-lg bg-cyan-500 px-8 py-4 text-base font-medium text-white shadow-lg hover:bg-cyan-400 hover:shadow-cyan-500/20 transition-all duration-200"
          >
            Get Started
          </Link>
        </div>
      </div>

      <div className="mt-24 grid grid-cols-1 gap-8 sm:grid-cols-3 max-w-7xl mx-auto">
        <div className="group relative p-8 bg-navy-950 rounded-lg border border-navy-800 hover:border-cyan-400 transition-all duration-300">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-navy-900 flex items-center justify-center group-hover:bg-cyan-500/10 transition-all duration-300">
              <Database className="w-8 h-8 text-cyan-400" />
            </div>
          </div>
          <h3 className="text-xl font-semibold text-text-primary text-center">Connect Data Source</h3>
          <p className="mt-4 text-base text-text-secondary text-center leading-relaxed">
            Link your chatbot deployment and conversation logs
          </p>
        </div>
        <div className="group relative p-8 bg-navy-950 rounded-lg border border-navy-800 hover:border-cyan-400 transition-all duration-300">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-navy-900 flex items-center justify-center group-hover:bg-cyan-500/10 transition-all duration-300">
              <LineChart className="w-8 h-8 text-cyan-400" />
            </div>
          </div>
          <h3 className="text-xl font-semibold text-text-primary text-center">Analyze Conversations</h3>
          <p className="mt-4 text-base text-text-secondary text-center leading-relaxed">
            Review real customer interactions and performance metrics
          </p>
        </div>
        <div className="group relative p-8 bg-navy-950 rounded-lg border border-navy-800 hover:border-cyan-400 transition-all duration-300">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-navy-900 flex items-center justify-center group-hover:bg-cyan-500/10 transition-all duration-300">
              <Lightbulb className="w-8 h-8 text-cyan-400" />
            </div>
          </div>
          <h3 className="text-xl font-semibold text-text-primary text-center">Get Recommendations</h3>
          <p className="mt-4 text-base text-text-secondary text-center leading-relaxed">
            Receive AI-powered insights and optimization suggestions
          </p>
        </div>
      </div>
    </div>
  )
}
