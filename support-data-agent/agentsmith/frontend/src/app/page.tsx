import Link from 'next/link'

export default function Home() {
  return (
    <div className="px-4 py-12 sm:py-16">
      <div className="text-center max-w-5xl mx-auto">
        <h1 className="text-5xl font-serif font-semibold tracking-tight text-parchment-100 sm:text-6xl md:text-7xl">
          AgentSmith
        </h1>
        <p className="mt-8 text-xl leading-relaxed text-parchment-200 max-w-3xl mx-auto">
          Analyze chatbot conversations to identify performance issues and optimize agent design
        </p>
        <div className="mt-12 flex items-center justify-center gap-x-6">
          <Link
            href="/projects"
            className="rounded-lg bg-strategic-600 px-8 py-4 text-base font-medium text-parchment-50 shadow-lg shadow-strategic-600/20 hover:bg-strategic-500 hover:shadow-xl hover:shadow-strategic-500/30 hover:scale-105 transition-all duration-200"
          >
            Get Started
          </Link>
        </div>
      </div>

      <div className="mt-24 grid grid-cols-1 gap-8 sm:grid-cols-3 max-w-7xl mx-auto">
        <div className="group relative p-8 bg-slate-850 rounded-lg border-2 border-bronze-500/40 shadow-lg hover:border-bronze-500/60 hover:shadow-2xl hover:shadow-bronze-500/10 hover:-translate-y-1 transition-all duration-300">
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 rounded-full border-2 border-bronze-500 bg-slate-800 flex items-center justify-center group-hover:border-bronze-400 group-hover:shadow-lg group-hover:shadow-bronze-500/20 transition-all duration-300">
              <span className="text-4xl font-serif font-semibold text-bronze-400 group-hover:text-bronze-300 transition-colors">I</span>
            </div>
          </div>
          <h3 className="text-xl font-serif font-semibold text-parchment-100 text-center tracking-wide uppercase whitespace-nowrap" style={{letterSpacing: '0.1em'}}>Connect Data Source</h3>
          <p className="mt-4 text-base text-parchment-200 text-center leading-relaxed">
            Link your chatbot deployment and conversation logs
          </p>
        </div>
        <div className="group relative p-8 bg-slate-850 rounded-lg border-2 border-teal-600/40 shadow-lg hover:border-teal-500/60 hover:shadow-2xl hover:shadow-teal-500/10 hover:-translate-y-1 transition-all duration-300">
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 rounded-full border-2 border-teal-500 bg-slate-800 flex items-center justify-center group-hover:border-teal-400 group-hover:shadow-lg group-hover:shadow-teal-500/20 transition-all duration-300">
              <span className="text-4xl font-serif font-semibold text-teal-500 group-hover:text-teal-400 transition-colors">II</span>
            </div>
          </div>
          <h3 className="text-xl font-serif font-semibold text-parchment-100 text-center tracking-wide uppercase whitespace-nowrap" style={{letterSpacing: '0.1em'}}>Analyze Conversations</h3>
          <p className="mt-4 text-base text-parchment-200 text-center leading-relaxed">
            Review real customer interactions and performance metrics
          </p>
        </div>
        <div className="group relative p-8 bg-slate-850 rounded-lg border-2 border-amber-600/40 shadow-lg hover:border-amber-500/60 hover:shadow-2xl hover:shadow-amber-500/10 hover:-translate-y-1 transition-all duration-300">
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 rounded-full border-2 border-amber-500 bg-slate-800 flex items-center justify-center group-hover:border-amber-400 group-hover:shadow-lg group-hover:shadow-amber-500/20 transition-all duration-300">
              <span className="text-4xl font-serif font-semibold text-amber-500 group-hover:text-amber-400 transition-colors">III</span>
            </div>
          </div>
          <h3 className="text-xl font-serif font-semibold text-parchment-100 text-center tracking-wide uppercase whitespace-nowrap" style={{letterSpacing: '0.1em'}}>Get Recommendations</h3>
          <p className="mt-4 text-base text-parchment-200 text-center leading-relaxed">
            Receive AI-powered insights and optimization suggestions
          </p>
        </div>
      </div>
    </div>
  )
}
