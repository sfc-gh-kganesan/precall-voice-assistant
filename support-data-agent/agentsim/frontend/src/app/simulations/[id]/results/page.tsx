'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { simulationsApi, conversationsApi } from '@/lib/api'
import type { SimulationResults, ConversationSummary, Conversation, ImprovementSuggestion } from '@/lib/types'
import CodeRecommendationModal from '@/components/CodeRecommendationModal'

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
  const [aiInsights, setAiInsights] = useState<ImprovementSuggestion[]>([])
  const [aiInsightsLoading, setAiInsightsLoading] = useState(false)
  const [aiInsightsError, setAiInsightsError] = useState<string | null>(null)
  const [insightsExpanded, setInsightsExpanded] = useState(true)
  const [expandedInsightIds, setExpandedInsightIds] = useState<Set<number>>(new Set())
  const [activeInsightsTab, setActiveInsightsTab] = useState<'high' | 'medium' | 'low'>('high')
  const [selectedInsightForModal, setSelectedInsightForModal] = useState<ImprovementSuggestion | null>(null)

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

      // Load AI insights separately
      loadAIInsights()
    } catch (err) {
      console.error(err)
      setLoading(false)
    }
  }

  const loadAIInsights = async () => {
    setAiInsightsLoading(true)
    setAiInsightsError(null)
    try {
      const response = await simulationsApi.getAIInsights(simulationId)
      setAiInsights(response.data)
    } catch (err: any) {
      console.error('Failed to load AI insights:', err)
      setAiInsightsError(err.response?.data?.detail || 'Failed to load AI insights')
    } finally {
      setAiInsightsLoading(false)
    }
  }

  const regenerateInsights = async () => {
    setAiInsightsLoading(true)
    setAiInsightsError(null)
    try {
      const response = await simulationsApi.regenerateAIInsights(simulationId)
      setAiInsights(response.data)
    } catch (err: any) {
      console.error('Failed to regenerate AI insights:', err)
      setAiInsightsError(err.response?.data?.detail || 'Failed to regenerate AI insights')
    } finally {
      setAiInsightsLoading(false)
    }
  }

  const toggleInsightDetail = (id: number) => {
    const newExpanded = new Set(expandedInsightIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedInsightIds(newExpanded)
  }

  const loadConversation = async (id: number) => {
    try {
      const res = await conversationsApi.get(id)
      setSelectedConv(res.data)
    } catch (err) {
      alert('Failed to load conversation')
    }
  }

  const handleIssueCreated = (insightId: number, issueUrl: string) => {
    // Update the insight in the state with the new issue URL
    setAiInsights(prevInsights =>
      prevInsights.map(insight =>
        insight.id === insightId
          ? {
              ...insight,
              code_recommendation: {
                ...insight.code_recommendation!,
                github_issue_url: issueUrl,
                status: 'issue_created',
              },
            }
          : insight
      )
    )
  }

  if (loading) return <div className="p-8 text-center text-parchment-200">Loading...</div>
  if (!results) return <div className="p-8 text-center text-parchment-200">No results available</div>

  const successRate = (results.successful / results.num_simulations) * 100

  // Calculate insights metrics
  const insightsByPriority = {
    high: aiInsights.filter(i => i.priority === 'high'),
    medium: aiInsights.filter(i => i.priority === 'medium'),
    low: aiInsights.filter(i => i.priority === 'low')
  }

  const categoryIcons: Record<string, string> = {
    tool: '🔧',
    prompt: '💬',
    logic: '🧠',
    error_handling: '⚠️',
    ux: '✨',
    performance: '⚡',
    general: '📌'
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Breadcrumb Navigation */}
      <div className="mb-4">
        <nav className="flex items-center gap-2 text-sm text-parchment-400">
          <Link href="/projects" className="hover:text-parchment-200 transition-colors">
            Projects
          </Link>
          <span>›</span>
          <Link href={`/projects/${results.project_id}`} className="hover:text-parchment-200 transition-colors">
            Project
          </Link>
          <span>›</span>
          <span className="text-parchment-200">Simulation Results</span>
        </nav>
      </div>

      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-serif font-semibold text-parchment-100">Simulation Results</h1>
          <p className="text-sm text-parchment-300 mt-2">ID: {results.id}</p>
        </div>
        <button onClick={() => {
          const data = JSON.stringify({ results, conversations, insights: aiInsights }, null, 2)
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

      {/* All Conversations Table */}
      <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden mb-8">
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

      {/* Quality Insights Section */}
      <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden mb-8">
        <div
          className="px-6 py-4 border-b border-slate-700 bg-slate-800/50 flex justify-between items-center cursor-pointer hover:bg-slate-800/70 transition-colors"
          onClick={() => setInsightsExpanded(!insightsExpanded)}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎯</span>
            <h2 className="text-lg font-serif font-semibold text-parchment-100">Quality Insights</h2>
            {aiInsights.length > 0 && (
              <span className="px-2 py-1 text-xs rounded bg-slate-700 text-parchment-300">
                {aiInsights.length} issue{aiInsights.length !== 1 ? 's' : ''} found
              </span>
            )}
            {insightsByPriority.high.length > 0 && (
              <span className="px-2 py-1 text-xs rounded bg-red-900/50 text-red-300 border border-red-700 font-medium">
                {insightsByPriority.high.length} high priority
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {!aiInsightsLoading && aiInsights.length > 0 && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  regenerateInsights()
                }}
                className="px-3 py-1 text-sm border border-strategic-600 text-strategic-500 rounded hover:bg-strategic-600/10 transition-colors"
              >
                Regenerate
              </button>
            )}
            <span className="text-2xl text-parchment-400">{insightsExpanded ? '▼' : '►'}</span>
          </div>
        </div>

        {insightsExpanded && (
          <div className="p-6">
            {aiInsightsLoading && (
              <div className="text-center py-8">
                <div className="text-parchment-300">Analyzing conversations with AI...</div>
                <div className="text-sm text-parchment-400 mt-2">This may take a moment</div>
              </div>
            )}

            {aiInsightsError && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-6">
                <div className="text-red-300 font-medium">Failed to load AI insights</div>
                <div className="text-sm text-red-400 mt-1">{aiInsightsError}</div>
                <button
                  onClick={loadAIInsights}
                  className="mt-3 px-3 py-1 text-sm border border-red-600 text-red-400 rounded hover:bg-red-600/10 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {!aiInsightsLoading && !aiInsightsError && aiInsights.length === 0 && (
              <div className="text-center py-8 text-parchment-300">
                <div className="text-4xl mb-2">✨</div>
                <div>No issues detected. Great job!</div>
              </div>
            )}

            {!aiInsightsLoading && aiInsights.length > 0 && (
              <>
                {/* Executive Summary & Insights Summary - Side by Side */}
                <div className="grid grid-cols-[1.5fr,1fr] gap-6 mb-6">
                  {/* Executive Summary */}
                  <div className="bg-gradient-to-r from-strategic-900/40 to-slate-900/40 rounded-lg p-5 border-2 border-strategic-600">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="text-2xl">🎯</span>
                      <h3 className="text-lg font-serif font-semibold text-strategic-400">Executive Summary</h3>
                    </div>

                    <div className="space-y-4 text-parchment-200">
                      {/* Overall Assessment */}
                      <div>
                        <div className="font-semibold text-parchment-100 mb-2">Overall Performance</div>
                        <p className="text-sm leading-relaxed">
                          {(() => {
                            const successRate = (results.successful / results.num_simulations) * 100
                            const hasHighPriority = insightsByPriority.high.length > 0

                            if (successRate >= 80 && !hasHighPriority) {
                              return `Strong performance with ${successRate.toFixed(0)}% success rate across ${results.num_simulations} simulations. ${insightsByPriority.medium.length + insightsByPriority.low.length} areas identified for optimization.`
                            } else if (successRate >= 60) {
                              return `Moderate performance with ${successRate.toFixed(0)}% success rate. ${insightsByPriority.high.length} high-priority issues require immediate attention to improve reliability.`
                            } else {
                              return `Performance needs improvement with ${successRate.toFixed(0)}% success rate. ${insightsByPriority.high.length} critical issues identified that significantly impact user experience.`
                            }
                          })()}
                        </p>
                      </div>

                      {/* Key Concerns */}
                      {insightsByPriority.high.length > 0 && (
                        <div>
                          <div className="font-semibold text-red-300 mb-2 flex items-center gap-2">
                            <span>⚠️</span>
                            Top Concerns
                          </div>
                          <ul className="text-sm space-y-1 list-disc list-inside text-parchment-300">
                            {insightsByPriority.high.slice(0, 3).map(insight => (
                              <li key={insight.id}>{insight.title}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Recommended Actions */}
                      <div>
                        <div className="font-semibold text-strategic-300 mb-2">Recommended Actions</div>
                        <ol className="text-sm space-y-2 list-decimal list-inside text-parchment-300">
                          {(() => {
                            const actions = []

                            // Prioritize high priority issues
                            if (insightsByPriority.high.length > 0) {
                              const topHigh = insightsByPriority.high[0]
                              actions.push(`Address "${topHigh.title}" - affecting ${topHigh.evidence?.conversation_ids?.length || topHigh.evidence?.conversation_count || 0} conversations`)
                            }

                            // Add category-specific recommendations
                            const categoryCount: Record<string, number> = {}
                            aiInsights.forEach(i => {
                              categoryCount[i.category] = (categoryCount[i.category] || 0) + 1
                            })
                            const topCategory = Object.entries(categoryCount).sort((a, b) => b[1] - a[1])[0]
                            if (topCategory && topCategory[1] > 2) {
                              actions.push(`Review ${topCategory[0]} issues (${topCategory[1]} instances found) for systemic improvements`)
                            }

                            // Add persona-specific recommendation
                            const personaCounts: Record<string, number> = {}
                            aiInsights.forEach(insight => {
                              const personas = insight.evidence?.affected_personas || []
                              personas.forEach(p => {
                                personaCounts[p] = (personaCounts[p] || 0) + 1
                              })
                            })
                            const topPersona = Object.entries(personaCounts).sort((a, b) => b[1] - a[1])[0]
                            if (topPersona && topPersona[1] > 1) {
                              actions.push(`Focus testing on "${topPersona[0]}" persona (${topPersona[1]} issues detected)`)
                            }

                            // Add general recommendation based on success rate
                            const successRate = (results.successful / results.num_simulations) * 100
                            if (successRate < 90) {
                              actions.push('Run additional simulations after fixes to verify improvements')
                            }

                            return actions.slice(0, 4).map((action, idx) => (
                              <li key={idx} className="pl-1">{action}</li>
                            ))
                          })()}
                        </ol>
                      </div>
                    </div>
                  </div>

                  {/* Insights Summary */}
                  <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-lg">📊</span>
                      <h3 className="text-sm font-semibold text-parchment-200 uppercase tracking-wide">Summary</h3>
                    </div>

                    <div className="space-y-6">
                      {/* Total & Priority Breakdown */}
                      <div>
                        <div className="text-xs text-parchment-400 mb-2">Issues Found</div>
                        <div className="text-2xl font-semibold text-parchment-100 mb-3">{aiInsights.length}</div>
                        <div className="space-y-1 text-sm">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-red-500"></span>
                            <span className="text-parchment-300">{insightsByPriority.high.length} High Priority</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                            <span className="text-parchment-300">{insightsByPriority.medium.length} Medium</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                            <span className="text-parchment-300">{insightsByPriority.low.length} Low</span>
                          </div>
                        </div>
                      </div>

                      {/* Top Categories */}
                      <div>
                        <div className="text-xs text-parchment-400 mb-2">Top Categories</div>
                        <div className="space-y-1 text-sm">
                          {(() => {
                            const categoryCounts: Record<string, number> = {}
                            aiInsights.forEach(insight => {
                              categoryCounts[insight.category] = (categoryCounts[insight.category] || 0) + 1
                            })
                            return Object.entries(categoryCounts)
                              .sort((a, b) => b[1] - a[1])
                              .slice(0, 4)
                              .map(([category, count]) => (
                                <div key={category} className="flex items-center gap-2">
                                  <span>{categoryIcons[category] || '📌'}</span>
                                  <span className="text-parchment-300">{category} ({count})</span>
                                </div>
                              ))
                          })()}
                        </div>
                      </div>

                      {/* Most Affected Personas */}
                      <div>
                        <div className="text-xs text-parchment-400 mb-2">Most Affected</div>
                        <div className="space-y-1 text-sm">
                          {(() => {
                            const personaCounts: Record<string, number> = {}
                            aiInsights.forEach(insight => {
                              const personas = insight.evidence?.affected_personas || []
                              personas.forEach(p => {
                                personaCounts[p] = (personaCounts[p] || 0) + 1
                              })
                            })
                            const topPersonas = Object.entries(personaCounts)
                              .sort((a, b) => b[1] - a[1])
                              .slice(0, 3)

                            return topPersonas.length > 0 ? (
                              topPersonas.map(([persona, count]) => (
                                <div key={persona} className="flex items-center gap-2">
                                  <span className="text-parchment-300">{persona}</span>
                                  <span className="text-xs text-parchment-500">({count} issues)</span>
                                </div>
                              ))
                            ) : (
                              <div className="text-parchment-500 text-xs">No persona data</div>
                            )
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Priority Tabs */}
                <div className="flex gap-2 border-b border-slate-700 -mx-6 px-6 mb-4">
                  <button
                    onClick={() => setActiveInsightsTab('high')}
                    className={`px-4 py-2 font-medium transition-colors ${
                      activeInsightsTab === 'high'
                        ? 'text-red-300 border-b-2 border-red-600'
                        : 'text-parchment-400 hover:text-parchment-200'
                    }`}
                  >
                    High Priority ({insightsByPriority.high.length})
                  </button>
                  <button
                    onClick={() => setActiveInsightsTab('medium')}
                    className={`px-4 py-2 font-medium transition-colors ${
                      activeInsightsTab === 'medium'
                        ? 'text-amber-300 border-b-2 border-amber-600'
                        : 'text-parchment-400 hover:text-parchment-200'
                    }`}
                  >
                    Medium ({insightsByPriority.medium.length})
                  </button>
                  <button
                    onClick={() => setActiveInsightsTab('low')}
                    className={`px-4 py-2 font-medium transition-colors ${
                      activeInsightsTab === 'low'
                        ? 'text-blue-300 border-b-2 border-blue-600'
                        : 'text-parchment-400 hover:text-parchment-200'
                    }`}
                  >
                    Low ({insightsByPriority.low.length})
                  </button>
                </div>

                {/* Tab Content */}
                <div className="space-y-3">
                  {/* High Priority Tab */}
                  {activeInsightsTab === 'high' && (
                    <>
                      {insightsByPriority.high.length === 0 ? (
                        <div className="text-center py-8 text-parchment-300">
                          No high priority issues found.
                        </div>
                      ) : (
                        insightsByPriority.high.map(insight => {
                          const isExpanded = expandedInsightIds.has(insight.id)
                          const conversationCount = insight.evidence?.conversation_ids?.length || insight.evidence?.conversation_count || 0
                          const personaCount = insight.evidence?.affected_personas?.length || insight.evidence?.persona_count || 0

                          return (
                            <div key={insight.id} className="border-l-4 border-red-600 p-4 rounded bg-red-900/30">
                              <div className="flex items-start justify-between gap-4 mb-2">
                                <h4 className="font-semibold text-red-300 flex items-center gap-2">
                                  <span>{categoryIcons[insight.category] || '📌'}</span>
                                  {insight.title}
                                </h4>
                                <span className="px-2 py-1 text-xs rounded bg-slate-800 text-parchment-300 border border-slate-600 shrink-0">
                                  {insight.category}
                                </span>
                              </div>
                              <p className="text-sm text-parchment-200 mb-3">{insight.description}</p>

                              {/* Code Recommendation Button */}
                              {insight.code_recommendation && (
                                <div className="mb-3">
                                  <button
                                    onClick={() => setSelectedInsightForModal(insight)}
                                    className="px-3 py-1.5 text-xs bg-strategic-600/20 text-strategic-400 border border-strategic-600 rounded hover:bg-strategic-600/30 transition-colors flex items-center gap-2"
                                  >
                                    <span>💡</span>
                                    View Code Recommendation
                                    {insight.code_recommendation.github_issue_url && (
                                      <span className="text-green-400">✓</span>
                                    )}
                                  </button>
                                </div>
                              )}

                              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded border border-slate-700">
                                <div className="flex gap-4 text-xs text-parchment-400">
                                  {conversationCount > 0 && (
                                    <div><span className="text-parchment-300 font-medium">{conversationCount}</span> conversations</div>
                                  )}
                                  {personaCount > 0 && (
                                    <div><span className="text-parchment-300 font-medium">{personaCount}</span> personas</div>
                                  )}
                                </div>
                                <button
                                  onClick={() => toggleInsightDetail(insight.id)}
                                  className="text-xs text-strategic-500 hover:text-strategic-400 transition-colors"
                                >
                                  {isExpanded ? 'Hide' : 'Show'} Details
                                </button>
                              </div>

                              {isExpanded && insight.evidence && (
                                <div className="mt-2 p-2 bg-slate-800/50 rounded border border-slate-700">
                                  <div className="text-xs text-parchment-400 space-y-1">
                                    {insight.evidence.pattern && (
                                      <div><span className="text-parchment-300">Pattern:</span> {insight.evidence.pattern}</div>
                                    )}
                                    {insight.evidence.affected_personas && insight.evidence.affected_personas.length > 0 && (
                                      <div><span className="text-parchment-300">Affected Personas:</span> {insight.evidence.affected_personas.join(', ')}</div>
                                    )}
                                    {insight.evidence.conversation_ids && insight.evidence.conversation_ids.length > 0 && (
                                      <div><span className="text-parchment-300">Conversation IDs:</span> {insight.evidence.conversation_ids.slice(0, 10).join(', ')}{insight.evidence.conversation_ids.length > 10 ? '...' : ''}</div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })
                      )}
                    </>
                  )}

                  {/* Medium Priority Tab */}
                  {activeInsightsTab === 'medium' && (
                    <>
                      {insightsByPriority.medium.length === 0 ? (
                        <div className="text-center py-8 text-parchment-300">
                          No medium priority issues found.
                        </div>
                      ) : (
                        insightsByPriority.medium.map(insight => {
                          const isExpanded = expandedInsightIds.has(insight.id)
                          const conversationCount = insight.evidence?.conversation_ids?.length || insight.evidence?.conversation_count || 0
                          const personaCount = insight.evidence?.affected_personas?.length || insight.evidence?.persona_count || 0

                          return (
                            <div key={insight.id} className="border-l-4 border-amber-600 p-4 rounded bg-amber-900/30">
                              <div className="flex items-start justify-between gap-4 mb-2">
                                <h4 className="font-semibold text-amber-300 flex items-center gap-2">
                                  <span>{categoryIcons[insight.category] || '📌'}</span>
                                  {insight.title}
                                </h4>
                                <span className="px-2 py-1 text-xs rounded bg-slate-800 text-parchment-300 border border-slate-600 shrink-0">
                                  {insight.category}
                                </span>
                              </div>
                              <p className="text-sm text-parchment-200 mb-3">{insight.description}</p>

                              {/* Code Recommendation Button */}
                              {insight.code_recommendation && (
                                <div className="mb-3">
                                  <button
                                    onClick={() => setSelectedInsightForModal(insight)}
                                    className="px-3 py-1.5 text-xs bg-strategic-600/20 text-strategic-400 border border-strategic-600 rounded hover:bg-strategic-600/30 transition-colors flex items-center gap-2"
                                  >
                                    <span>💡</span>
                                    View Code Recommendation
                                    {insight.code_recommendation.github_issue_url && (
                                      <span className="text-green-400">✓</span>
                                    )}
                                  </button>
                                </div>
                              )}

                              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded border border-slate-700">
                                <div className="flex gap-4 text-xs text-parchment-400">
                                  {conversationCount > 0 && (
                                    <div><span className="text-parchment-300 font-medium">{conversationCount}</span> conversations</div>
                                  )}
                                  {personaCount > 0 && (
                                    <div><span className="text-parchment-300 font-medium">{personaCount}</span> personas</div>
                                  )}
                                </div>
                                <button
                                  onClick={() => toggleInsightDetail(insight.id)}
                                  className="text-xs text-strategic-500 hover:text-strategic-400 transition-colors"
                                >
                                  {isExpanded ? 'Hide' : 'Show'} Details
                                </button>
                              </div>

                              {isExpanded && insight.evidence && (
                                <div className="mt-2 p-2 bg-slate-800/50 rounded border border-slate-700">
                                  <div className="text-xs text-parchment-400 space-y-1">
                                    {insight.evidence.pattern && (
                                      <div><span className="text-parchment-300">Pattern:</span> {insight.evidence.pattern}</div>
                                    )}
                                    {insight.evidence.affected_personas && insight.evidence.affected_personas.length > 0 && (
                                      <div><span className="text-parchment-300">Affected Personas:</span> {insight.evidence.affected_personas.join(', ')}</div>
                                    )}
                                    {insight.evidence.conversation_ids && insight.evidence.conversation_ids.length > 0 && (
                                      <div><span className="text-parchment-300">Conversation IDs:</span> {insight.evidence.conversation_ids.slice(0, 10).join(', ')}{insight.evidence.conversation_ids.length > 10 ? '...' : ''}</div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })
                      )}
                    </>
                  )}

                  {/* Low Priority Tab */}
                  {activeInsightsTab === 'low' && (
                    <>
                      {insightsByPriority.low.length === 0 ? (
                        <div className="text-center py-8 text-parchment-300">
                          No low priority issues found.
                        </div>
                      ) : (
                        insightsByPriority.low.map(insight => {
                          const isExpanded = expandedInsightIds.has(insight.id)
                          const conversationCount = insight.evidence?.conversation_ids?.length || insight.evidence?.conversation_count || 0
                          const personaCount = insight.evidence?.affected_personas?.length || insight.evidence?.persona_count || 0

                          return (
                            <div key={insight.id} className="border-l-4 border-blue-600 p-4 rounded bg-blue-900/30">
                              <div className="flex items-start justify-between gap-4 mb-2">
                                <h4 className="font-semibold text-blue-300 flex items-center gap-2">
                                  <span>{categoryIcons[insight.category] || '📌'}</span>
                                  {insight.title}
                                </h4>
                                <span className="px-2 py-1 text-xs rounded bg-slate-800 text-parchment-300 border border-slate-600 shrink-0">
                                  {insight.category}
                                </span>
                              </div>
                              <p className="text-sm text-parchment-200 mb-3">{insight.description}</p>

                              {/* Code Recommendation Button */}
                              {insight.code_recommendation && (
                                <div className="mb-3">
                                  <button
                                    onClick={() => setSelectedInsightForModal(insight)}
                                    className="px-3 py-1.5 text-xs bg-strategic-600/20 text-strategic-400 border border-strategic-600 rounded hover:bg-strategic-600/30 transition-colors flex items-center gap-2"
                                  >
                                    <span>💡</span>
                                    View Code Recommendation
                                    {insight.code_recommendation.github_issue_url && (
                                      <span className="text-green-400">✓</span>
                                    )}
                                  </button>
                                </div>
                              )}

                              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded border border-slate-700">
                                <div className="flex gap-4 text-xs text-parchment-400">
                                  {conversationCount > 0 && (
                                    <div><span className="text-parchment-300 font-medium">{conversationCount}</span> conversations</div>
                                  )}
                                  {personaCount > 0 && (
                                    <div><span className="text-parchment-300 font-medium">{personaCount}</span> personas</div>
                                  )}
                                </div>
                                <button
                                  onClick={() => toggleInsightDetail(insight.id)}
                                  className="text-xs text-strategic-500 hover:text-strategic-400 transition-colors"
                                >
                                  {isExpanded ? 'Hide' : 'Show'} Details
                                </button>
                              </div>

                              {isExpanded && insight.evidence && (
                                <div className="mt-2 p-2 bg-slate-800/50 rounded border border-slate-700">
                                  <div className="text-xs text-parchment-400 space-y-1">
                                    {insight.evidence.pattern && (
                                      <div><span className="text-parchment-300">Pattern:</span> {insight.evidence.pattern}</div>
                                    )}
                                    {insight.evidence.affected_personas && insight.evidence.affected_personas.length > 0 && (
                                      <div><span className="text-parchment-300">Affected Personas:</span> {insight.evidence.affected_personas.join(', ')}</div>
                                    )}
                                    {insight.evidence.conversation_ids && insight.evidence.conversation_ids.length > 0 && (
                                      <div><span className="text-parchment-300">Conversation IDs:</span> {insight.evidence.conversation_ids.slice(0, 10).join(', ')}{insight.evidence.conversation_ids.length > 10 ? '...' : ''}</div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })
                      )}
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        )}
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

      {/* Code Recommendation Modal */}
      {selectedInsightForModal && (
        <CodeRecommendationModal
          insight={selectedInsightForModal}
          simulationId={simulationId}
          isOpen={true}
          onClose={() => setSelectedInsightForModal(null)}
          onIssueCreated={(issueUrl) => {
            handleIssueCreated(selectedInsightForModal.id, issueUrl)
          }}
        />
      )}
    </div>
  )
}
