'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { simulationsApi, conversationsApi } from '@/lib/api'
import type { SimulationResults, ConversationSummary, Conversation } from '@/lib/types'

// Helper function to format milliseconds into human-readable format
function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`
  } else if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`
  } else {
    return `${(ms / 60000).toFixed(1)} min`
  }
}

export default function ResultsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const simulationId = parseInt(id)
  const [results, setResults] = useState<SimulationResults | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [resRes, convRes] = await Promise.all([
        simulationsApi.getResults(simulationId),
        simulationsApi.getConversations(simulationId)
      ])
      setResults(resRes.data)
      setConversations(convRes.data)
      setLoading(false)
    } catch (err) {
      console.error(err)
      setLoading(false)
    }
  }

  const loadConversation = async (id: number) => {
    try {
      const res = await conversationsApi.get(id)
      setSelectedConv(res.data)
    } catch (err) {
      alert('Failed to load conversation')
    }
  }

  if (loading) return <div className="p-8 text-center text-parchment-200">Loading...</div>
  if (!results) return <div className="p-8 text-center text-parchment-200">No results available</div>

  const successRate = (results.successful / results.num_simulations) * 100

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-serif font-semibold text-parchment-100">Simulation Results</h1>
          <p className="text-sm text-parchment-300 mt-2">ID: {results.id}</p>
        </div>
        <div className="flex gap-2">
          <Link href={`/simulations/${simulationId}/insights`} className="px-4 py-2 border-2 border-strategic-600 text-strategic-500 rounded hover:bg-strategic-600/10 transition-colors">
            View Insights
          </Link>
          <button onClick={() => {
            const data = JSON.stringify({ results, conversations }, null, 2)
            const blob = new Blob([data], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `simulation-${simulationId}.json`
            a.click()
          }} className="px-4 py-2 bg-strategic-600 text-parchment-50 rounded hover:bg-strategic-500 transition-colors">
            Export
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
          <div className="text-sm font-medium text-parchment-300">Total</div>
          <div className="text-3xl font-serif font-semibold text-parchment-100 mt-2">{results.num_simulations}</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
          <div className="text-sm font-medium text-parchment-300">Success Rate</div>
          <div className="text-3xl font-serif font-semibold text-green-400 mt-2">{successRate.toFixed(1)}%</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
          <div className="text-sm font-medium text-parchment-300">Successful</div>
          <div className="text-3xl font-serif font-semibold text-green-400 mt-2">{results.successful}</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
          <div className="text-sm font-medium text-parchment-300">Failed</div>
          <div className="text-3xl font-serif font-semibold text-red-400 mt-2">{results.failed}</div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 mb-8">
        <h2 className="text-lg font-serif font-semibold text-parchment-100 mb-4">Aggregate Metrics</h2>
        <div className="grid grid-cols-4 gap-4">
          {Object.entries(results.aggregate_metrics).map(([key, value]) => {
            // Format duration metrics
            const displayValue = key.toLowerCase().includes('duration') || key.toLowerCase().includes('latency')
              ? formatDuration(value as number)
              : typeof value === 'number' ? value.toFixed(2) : value

            // Clean up label: remove _ms suffix for duration/latency metrics since values are auto-formatted
            let displayLabel = key.replace(/_/g, ' ')
            if (key.toLowerCase().includes('duration') || key.toLowerCase().includes('latency')) {
              displayLabel = displayLabel.replace(/\s*ms\s*$/i, '').trim()
            }

            return (
              <div key={key} className="border-l-4 border-strategic-600 pl-4">
                <div className="text-xs font-medium text-parchment-300 uppercase">{displayLabel}</div>
                <div className="text-xl font-semibold text-parchment-100 mt-1">{displayValue}</div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700 bg-slate-800/50">
          <h2 className="text-lg font-serif font-semibold text-parchment-100">All Conversations</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-700">
            <thead className="bg-slate-800/30">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Persona</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Turns</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Duration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-slate-900 divide-y divide-slate-800">
              {conversations.map(conv => (
                <tr key={conv.id} className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-6 py-4 text-sm text-parchment-200">{conv.id}</td>
                  <td className="px-6 py-4 text-sm text-parchment-200">{conv.persona?.name || 'Unknown'}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border ${conv.success ? 'bg-green-900/40 text-green-400 border-green-700' : 'bg-red-900/40 text-red-400 border-red-700'}`}>
                      {conv.success ? 'Success' : 'Failed'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-parchment-200">{conv.num_turns}</td>
                  <td className="px-6 py-4 text-sm text-parchment-200">{formatDuration(conv.total_duration_ms)}</td>
                  <td className="px-6 py-4">
                    <button onClick={() => loadConversation(conv.id)} className="text-strategic-500 hover:text-strategic-400 text-sm font-medium">
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedConv && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm overflow-y-auto z-50" onClick={() => setSelectedConv(null)}>
          <div className="relative top-20 mx-auto p-5 border-2 border-slate-700 w-11/12 max-w-4xl shadow-2xl rounded-lg bg-slate-900" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between mb-4">
              <div>
                <h3 className="text-lg font-serif font-semibold text-parchment-100">Conversation - {selectedConv.persona?.name}</h3>
                <div className="flex items-center gap-4 mt-1 text-sm text-parchment-300">
                  <span>Turns: {selectedConv.num_turns}</span>
                  <span>Duration: {formatDuration(selectedConv.total_duration_ms)}</span>
                  <span className={selectedConv.success ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>
                    {selectedConv.success ? '✓ Success' : '✗ Failed'}
                  </span>
                </div>
              </div>
              <button onClick={() => setSelectedConv(null)} className="text-parchment-300 hover:text-parchment-100 text-2xl">×</button>
            </div>

            {/* Error details for failed conversations */}
            {!selectedConv.success && (selectedConv.stop_reason || selectedConv.error_message) && (
              <div className="mb-4 p-4 bg-red-900/30 border border-red-700 rounded">
                <div className="font-medium text-red-300 mb-1">Failure Details</div>
                {selectedConv.stop_reason && (
                  <div className="text-sm text-red-200">
                    <span className="font-medium">Stop Reason:</span> {selectedConv.stop_reason}
                  </div>
                )}
                {selectedConv.error_message && (
                  <div className="text-sm text-red-200 mt-1">
                    <span className="font-medium">Error:</span> {selectedConv.error_message}
                  </div>
                )}
              </div>
            )}

            <div className="space-y-4 max-h-96 overflow-y-auto">
              {selectedConv.messages.map((msg, i) => (
                <div key={i} className={`p-4 rounded-lg ${msg.role === 'user' ? 'bg-strategic-900/40 border border-strategic-700' : 'bg-slate-800 border border-slate-700'}`}>
                  <div className="text-xs font-medium text-parchment-300 mb-1">{msg.role === 'user' ? '👤 User' : '🤖 Assistant'}</div>
                  <div className="text-sm text-parchment-200">{msg.content}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
