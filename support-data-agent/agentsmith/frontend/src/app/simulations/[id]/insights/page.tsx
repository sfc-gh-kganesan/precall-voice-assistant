'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { simulationsApi } from '@/lib/api'
import type { SimulationResults, ConversationSummary, ImprovementSuggestion } from '@/lib/types'

type TabType = 'high' | 'medium' | 'low' | 'all'

export default function InsightsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const simulationId = parseInt(id)
  const [results, setResults] = useState<SimulationResults | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [aiInsights, setAiInsights] = useState<ImprovementSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [aiInsightsLoading, setAiInsightsLoading] = useState(false)
  const [aiInsightsError, setAiInsightsError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('high')
  const [expandedInsights, setExpandedInsights] = useState<Set<number>>(new Set())

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

  const toggleInsight = (id: number) => {
    const newExpanded = new Set(expandedInsights)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedInsights(newExpanded)
  }

  if (loading) return <div className="p-8 text-center text-text-secondary">Loading...</div>
  if (!results) return <div className="p-8 text-center text-text-secondary">No results available</div>

  // Calculate insights by priority and category
  const insightsByPriority = {
    high: aiInsights.filter(i => i.priority === 'high'),
    medium: aiInsights.filter(i => i.priority === 'medium'),
    low: aiInsights.filter(i => i.priority === 'low')
  }

  const insightsByCategory: Record<string, ImprovementSuggestion[]> = {}
  aiInsights.forEach(insight => {
    const cat = insight.category
    if (!insightsByCategory[cat]) insightsByCategory[cat] = []
    insightsByCategory[cat].push(insight)
  })

  const categoryIcons: Record<string, string> = {
    tool: '🔧',
    prompt: '💬',
    logic: '🧠',
    error_handling: '⚠️',
    ux: '✨',
    performance: '⚡',
    general: '📌'
  }

  const categoryLabels: Record<string, string> = {
    tool: 'Tool Issues',
    prompt: 'Prompt Issues',
    logic: 'Logic Issues',
    error_handling: 'Error Handling',
    ux: 'UX Issues',
    performance: 'Performance',
    general: 'General'
  }

  // Get most affected personas
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

  // Render insight card
  const renderInsightCard = (insight: ImprovementSuggestion) => {
    const priorityStyles = {
      high: 'border-red-600 bg-red-900/30',
      medium: 'border-amber-600 bg-amber-900/30',
      low: 'border-blue-600 bg-blue-900/30'
    }
    const priorityColors = {
      high: 'text-red-300',
      medium: 'text-amber-300',
      low: 'text-blue-300'
    }

    const isExpanded = expandedInsights.has(insight.id)
    const conversationCount = insight.evidence?.conversation_ids?.length || 0
    const personaCount = insight.evidence?.affected_personas?.length || 0

    return (
      <div key={insight.id} className={`border-l-4 p-6 rounded ${priorityStyles[insight.priority]}`}>
        <div className="flex items-start justify-between gap-4 mb-2">
          <h3 className={`font-semibold text-lg ${priorityColors[insight.priority]}`}>
            <span className="mr-2">{categoryIcons[insight.category] || '📌'}</span>
            {insight.title}
          </h3>
          <div className="flex gap-2">
            <span className="px-2 py-1 text-xs rounded bg-navy-900 text-text-tertiary border border-navy-700">
              {insight.category}
            </span>
            <span className={`px-2 py-1 text-xs rounded font-medium ${priorityColors[insight.priority]}`}>
              {insight.priority.toUpperCase()}
            </span>
          </div>
        </div>
        <p className="text-sm text-text-secondary mb-4">{insight.description}</p>

        {/* Compact evidence summary */}
        <div className="mt-3 flex items-center justify-between p-3 bg-navy-900/50 rounded border border-navy-800">
          <div className="flex gap-6 text-xs text-text-muted">
            {conversationCount > 0 && (
              <div><span className="text-text-tertiary font-medium">{conversationCount}</span> conversations affected</div>
            )}
            {personaCount > 0 && (
              <div><span className="text-text-tertiary font-medium">{personaCount}</span> personas affected</div>
            )}
          </div>
          <button
            onClick={() => toggleInsight(insight.id)}
            className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1"
          >
            {isExpanded ? 'Hide' : 'Show'} Details
            <span className="text-lg">{isExpanded ? '▲' : '▼'}</span>
          </button>
        </div>

        {/* Expanded evidence details */}
        {isExpanded && insight.evidence && (
          <div className="mt-2 p-3 bg-navy-900/50 rounded border border-navy-800">
            <div className="text-xs font-medium text-text-tertiary mb-2">Detailed Evidence:</div>
            <div className="text-xs text-text-muted space-y-1">
              {insight.evidence.pattern && (
                <div><span className="text-text-tertiary">Pattern:</span> {insight.evidence.pattern}</div>
              )}
              {insight.evidence.affected_personas && insight.evidence.affected_personas.length > 0 && (
                <div><span className="text-text-tertiary">Affected Personas:</span> {insight.evidence.affected_personas.join(', ')}</div>
              )}
              {insight.evidence.conversation_ids && insight.evidence.conversation_ids.length > 0 && (
                <div><span className="text-text-tertiary">Conversation IDs:</span> {insight.evidence.conversation_ids.slice(0, 10).join(', ')}{insight.evidence.conversation_ids.length > 10 ? '...' : ''}</div>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-semibold text-text-primary">Insights & Recommendations</h1>
            <p className="text-sm text-text-tertiary mt-2">Analysis for Simulation {results.id}</p>
          </div>
          <Link href={`/simulations/${simulationId}/results`} className="px-4 py-2 border-2 border-strategic-600 text-cyan-400 rounded hover:bg-cyan-500/10 transition-colors text-sm">
            Back to Results
          </Link>
        </div>
      </div>

      {/* Summary Banner */}
      {aiInsights.length > 0 && !aiInsightsLoading && (
        <div className="bg-gradient-to-r from-red-900/40 to-amber-900/40 border-2 border-red-600 rounded-lg p-6 mb-8">
          <div className="flex items-start gap-4">
            <div className="text-4xl">⚠️</div>
            <div className="flex-1">
              <h2 className="text-2xl font-semibold text-red-200 mb-3">
                {insightsByPriority.high.length} High Priority Issue{insightsByPriority.high.length !== 1 ? 's' : ''} Detected
              </h2>
              <div className="grid grid-cols-3 gap-4 mb-4">
                {Object.entries(insightsByCategory).map(([cat, insights]) => (
                  <div key={cat} className="flex items-center gap-2 text-sm">
                    <span className="text-lg">{categoryIcons[cat]}</span>
                    <span className="text-text-secondary">{insights.length} {categoryLabels[cat]}</span>
                  </div>
                ))}
              </div>
              {topPersonas.length > 0 && (
                <div className="text-sm text-text-tertiary">
                  Most Affected: {topPersonas.map(([p, count]) => `${p} (${count} issues)`).join(', ')}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI-Powered Insights with Tabs */}
      <div className="mt-8 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-text-primary">AI-Powered Analysis</h2>
          <button
            onClick={regenerateInsights}
            disabled={aiInsightsLoading}
            className="px-3 py-1 text-sm border border-strategic-600 text-cyan-400 rounded hover:bg-cyan-500/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {aiInsightsLoading ? 'Generating...' : 'Regenerate'}
          </button>
        </div>

        {aiInsightsLoading && (
          <div className="bg-navy-950 rounded-lg border border-navy-800 p-6 text-center">
            <div className="text-text-tertiary">Analyzing conversations with AI...</div>
            <div className="text-sm text-text-muted mt-2">This may take a moment</div>
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
          <div className="bg-navy-950 rounded-lg border border-navy-800 p-6 text-center text-text-tertiary">
            No AI insights available yet. They will be generated automatically after simulation completes.
          </div>
        )}

        {!aiInsightsLoading && aiInsights.length > 0 && (
          <>
            {/* Priority Tabs */}
            <div className="flex gap-2 border-b border-navy-800">
              <button
                onClick={() => setActiveTab('high')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'high'
                    ? 'text-red-300 border-b-2 border-red-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                High Priority ({insightsByPriority.high.length})
              </button>
              <button
                onClick={() => setActiveTab('medium')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'medium'
                    ? 'text-amber-300 border-b-2 border-amber-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                Medium ({insightsByPriority.medium.length})
              </button>
              <button
                onClick={() => setActiveTab('low')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'low'
                    ? 'text-blue-300 border-b-2 border-blue-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                Low ({insightsByPriority.low.length})
              </button>
              <button
                onClick={() => setActiveTab('all')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'all'
                    ? 'text-cyan-300 border-b-2 border-strategic-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                All by Category
              </button>
            </div>

            {/* Tab Content */}
            <div className="space-y-4 mt-4">
              {/* Priority-based tabs */}
              {activeTab !== 'all' && (
                <>
                  {insightsByPriority[activeTab].length === 0 ? (
                    <div className="bg-navy-950 rounded-lg border border-navy-800 p-6 text-center text-text-tertiary">
                      No {activeTab} priority insights found.
                    </div>
                  ) : (
                    insightsByPriority[activeTab].map(renderInsightCard)
                  )}
                </>
              )}

              {/* Category-based tab */}
              {activeTab === 'all' && (
                <div className="space-y-6">
                  {Object.entries(insightsByCategory).map(([category, insights]) => (
                    <div key={category}>
                      <h3 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
                        <span className="text-2xl">{categoryIcons[category]}</span>
                        {categoryLabels[category]} ({insights.length})
                      </h3>
                      <div className="space-y-3">
                        {insights.map(renderInsightCard)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* AI-Powered Insights */}
      <div className="mt-8 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-text-primary">AI-Powered Analysis</h2>
          <button
            onClick={regenerateInsights}
            disabled={aiInsightsLoading}
            className="px-3 py-1 text-sm border border-strategic-600 text-cyan-400 rounded hover:bg-cyan-500/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {aiInsightsLoading ? 'Generating...' : 'Regenerate'}
          </button>
        </div>

        {aiInsightsLoading && (
          <div className="bg-navy-950 rounded-lg border border-navy-800 p-6 text-center">
            <div className="text-text-tertiary">Analyzing conversations with AI...</div>
            <div className="text-sm text-text-muted mt-2">This may take a moment</div>
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
          <div className="bg-navy-950 rounded-lg border border-navy-800 p-6 text-center text-text-tertiary">
            No AI insights available yet. They will be generated automatically after simulation completes.
          </div>
        )}

        {!aiInsightsLoading && aiInsights.length > 0 && (
          <>
            {/* Priority Tabs */}
            <div className="flex gap-2 border-b border-navy-800">
              <button
                onClick={() => setActiveTab('high')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'high'
                    ? 'text-red-300 border-b-2 border-red-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                High Priority ({insightsByPriority.high.length})
              </button>
              <button
                onClick={() => setActiveTab('medium')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'medium'
                    ? 'text-amber-300 border-b-2 border-amber-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                Medium ({insightsByPriority.medium.length})
              </button>
              <button
                onClick={() => setActiveTab('low')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'low'
                    ? 'text-blue-300 border-b-2 border-blue-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                Low ({insightsByPriority.low.length})
              </button>
              <button
                onClick={() => setActiveTab('all')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'all'
                    ? 'text-cyan-300 border-b-2 border-strategic-600'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                All by Category
              </button>
            </div>

            {/* Tab Content */}
            <div className="space-y-4 mt-4">
              {/* Priority-based tabs */}
              {activeTab !== 'all' && (
                <>
                  {insightsByPriority[activeTab].length === 0 ? (
                    <div className="bg-navy-950 rounded-lg border border-navy-800 p-6 text-center text-text-tertiary">
                      No {activeTab} priority insights found.
                    </div>
                  ) : (
                    insightsByPriority[activeTab].map(renderInsightCard)
                  )}
                </>
              )}

              {/* Category-based tab */}
              {activeTab === 'all' && (
                <div className="space-y-6">
                  {Object.entries(insightsByCategory).map(([category, insights]) => (
                    <div key={category}>
                      <h3 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
                        <span className="text-2xl">{categoryIcons[category]}</span>
                        {categoryLabels[category]} ({insights.length})
                      </h3>
                      <div className="space-y-3">
                        {insights.map(renderInsightCard)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
