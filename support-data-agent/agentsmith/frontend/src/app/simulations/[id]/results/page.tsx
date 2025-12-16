'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { simulationsApi, conversationsApi, projectsApi } from '@/lib/api'
import type { SimulationResults, ConversationSummary, Conversation, ImprovementSuggestion } from '@/lib/types'
import CodeRecommendationModal from '@/components/CodeRecommendationModal'
import KnowledgeRecommendationModal from '@/components/KnowledgeRecommendationModal'
import { QualityScoreBadge, EndingAssessmentBadge, KnowledgeGapBadge, CapabilityGapBadge, GapCard } from '@/components/GapIndicators'

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
  const [selectedPriorities, setSelectedPriorities] = useState<Set<string>>(new Set(['high', 'medium', 'low']))
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set())
  const [selectedInsightForModal, setSelectedInsightForModal] = useState<ImprovementSuggestion | null>(null)
  const [selectedKnowledgeForModal, setSelectedKnowledgeForModal] = useState<ImprovementSuggestion | null>(null)
  const [conversationsExpanded, setConversationsExpanded] = useState(false)
  const [selectedSnowflakeConvId, setSelectedSnowflakeConvId] = useState<string | null>(null)
  const [snowflakeConvDetails, setSnowflakeConvDetails] = useState<any>(null)
  const [snowflakeConvLoading, setSnowflakeConvLoading] = useState(false)

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

  const loadSnowflakeConversation = async (conversationId: string) => {
    if (!results?.project_id) {
      alert('Project ID not available')
      return
    }
    try {
      setSnowflakeConvLoading(true)
      setSelectedSnowflakeConvId(conversationId)
      const response = await projectsApi.getConversationDetails(results.project_id, conversationId)
      setSnowflakeConvDetails(response.data)
    } catch (err) {
      console.error('Failed to load conversation details:', err)
      alert('Failed to load conversation')
      setSelectedSnowflakeConvId(null)
    } finally {
      setSnowflakeConvLoading(false)
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

  if (loading) return <div className="p-8 text-center text-text-secondary">Loading...</div>
  if (!results) return <div className="p-8 text-center text-text-secondary">No results available</div>

  const successRate = (results.successful / results.num_simulations) * 100

  // Calculate insights metrics
  const insightsByPriority = {
    high: aiInsights.filter(i => i.priority === 'high'),
    medium: aiInsights.filter(i => i.priority === 'medium'),
    low: aiInsights.filter(i => i.priority === 'low')
  }

  // Get all unique categories
  const allCategories = Array.from(new Set(aiInsights.map(i => i.category)))

  // Filter insights based on selected priorities and categories
  const filteredInsights = aiInsights.filter(insight => {
    const matchesPriority = selectedPriorities.has(insight.priority)
    const matchesCategory = selectedCategories.size === 0 || selectedCategories.has(insight.category)
    return matchesPriority && matchesCategory
  }).sort((a, b) => {
    // Sort by priority: high (0) -> medium (1) -> low (2)
    const priorityOrder: Record<string, number> = { high: 0, medium: 1, low: 2 }
    return priorityOrder[a.priority] - priorityOrder[b.priority]
  })

  // Toggle functions for filters
  const togglePriority = (priority: string) => {
    const newSelected = new Set(selectedPriorities)
    if (newSelected.has(priority)) {
      newSelected.delete(priority)
    } else {
      newSelected.add(priority)
    }
    setSelectedPriorities(newSelected)
  }

  const toggleCategory = (category: string) => {
    const newSelected = new Set(selectedCategories)
    if (newSelected.has(category)) {
      newSelected.delete(category)
    } else {
      newSelected.add(category)
    }
    setSelectedCategories(newSelected)
  }

  const categoryIcons: Record<string, string> = {
    tool: '🔧',
    knowledge: '📚',
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
        <nav className="flex items-center gap-2 text-sm text-text-muted">
          <Link href="/projects" className="hover:text-text-secondary transition-colors">
            Deployments
          </Link>
          <span>›</span>
          <Link href={`/projects/${results.project_id}`} className="hover:text-text-secondary transition-colors">
            Deployment
          </Link>
          <span>›</span>
          <span className="text-text-secondary">Analysis Results</span>
        </nav>
      </div>

      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-text-primary">Analysis Results</h1>
          <p className="text-sm text-text-tertiary mt-2">ID: {results.id}</p>
        </div>
        <button onClick={() => {
          const data = JSON.stringify({ results, conversations, insights: aiInsights }, null, 2)
          const blob = new Blob([data], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `simulation-${simulationId}.json`
          a.click()
        }} className="px-4 py-2 bg-cyan-500 text-white rounded hover:bg-cyan-400 transition-colors">
          Export
        </button>
      </div>

      <div className="bg-navy-950 rounded-lg border border-navy-800 p-4 mb-4">
        <h2 className="text-base font-semibold text-text-primary mb-3">Performance Overview</h2>

        <div className="grid grid-cols-4 gap-3">
          {/* Total */}
          <div className="bg-navy-900 rounded-lg border border-navy-800 p-4">
            <div className="text-xs font-medium text-text-tertiary">Total</div>
            <div className="text-2xl font-semibold text-text-primary mt-1">{conversations.length}</div>
          </div>

          {/* Success Rate */}
          <div className="bg-navy-900 rounded-lg border border-navy-800 p-4">
            <div className="text-xs font-medium text-text-tertiary">Success Rate</div>
            <div className="text-2xl font-semibold text-green-400 mt-1">{successRate.toFixed(1)}%</div>
          </div>

          {/* Successful */}
          <div className="bg-navy-900 rounded-lg border border-navy-800 p-4">
            <div className="text-xs font-medium text-text-tertiary">Successful</div>
            <div className="text-2xl font-semibold text-green-400 mt-1">{results.successful}</div>
          </div>

          {/* Failed */}
          <div className="bg-navy-900 rounded-lg border border-navy-800 p-4">
            <div className="text-xs font-medium text-text-tertiary">Failed</div>
            <div className="text-2xl font-semibold text-red-400 mt-1">{results.failed}</div>
          </div>
        </div>
      </div>

      {/* Gap Analysis Summary */}
      {(() => {
        // Calculate gap statistics
        const appropriateCount = conversations.filter(c => c.scenario?.evaluation?.ending_assessment === 'appropriate').length
        const prematureCount = conversations.filter(c => c.scenario?.evaluation?.ending_assessment === 'premature').length
        const excessiveCount = conversations.filter(c => c.scenario?.evaluation?.ending_assessment === 'excessive').length
        const knowledgeGapCount = conversations.filter(c => c.scenario?.evaluation?.knowledge_gap).length
        const capabilityGapCount = conversations.filter(c => c.scenario?.evaluation?.capability_gap).length
        const avgQuality = conversations
          .filter(c => c.scenario?.evaluation?.quality_score !== undefined)
          .reduce((sum, c) => sum + (c.scenario?.evaluation?.quality_score || 0), 0) /
          Math.max(conversations.filter(c => c.scenario?.evaluation?.quality_score !== undefined).length, 1)

        // Only show dashboard if we have evaluation data
        const hasEvaluationData = appropriateCount + prematureCount + excessiveCount + knowledgeGapCount + capabilityGapCount > 0

        if (!hasEvaluationData) return null

        return (
          <div className="bg-navy-950 rounded-lg border border-navy-800 p-4 mb-4">
            <h2 className="text-base font-semibold text-text-primary mb-3">Gap Analysis Summary</h2>

            <div className="grid grid-cols-4 gap-3">
              {/* Average Quality */}
              <div className="border-l-4 border-strategic-600 pl-4">
                <div className="text-xs font-medium text-text-tertiary uppercase">Avg Quality</div>
                <div className="text-2xl font-semibold text-text-primary mt-2">{(avgQuality * 100).toFixed(0)}%</div>
                <div className="text-xs text-text-muted mt-1">across evaluated conversations</div>
              </div>

              {/* Ending Quality */}
              <div className="border-l-4 border-green-600 pl-4">
                <div className="text-xs font-medium text-text-tertiary uppercase">Ending Quality</div>
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-green-400">✓ Appropriate</span>
                    <span className="font-semibold text-text-primary">{appropriateCount}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-yellow-400">⚠ Premature</span>
                    <span className="font-semibold text-text-primary">{prematureCount}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-orange-400">⏳ Excessive</span>
                    <span className="font-semibold text-text-primary">{excessiveCount}</span>
                  </div>
                </div>
              </div>

              {/* Knowledge Gaps */}
              <div className="border-l-4 border-blue-600 pl-4">
                <div className="text-xs font-medium text-text-tertiary uppercase">Knowledge Gaps</div>
                <div className="text-2xl font-semibold text-blue-300 mt-2">{knowledgeGapCount}</div>
                <div className="text-xs text-text-muted mt-1">
                  {knowledgeGapCount > 0 ?
                    `${(knowledgeGapCount / conversations.length * 100).toFixed(0)}% of conversations` :
                    'No gaps detected'
                  }
                </div>
              </div>

              {/* Capability Gaps */}
              <div className="border-l-4 border-purple-600 pl-4">
                <div className="text-xs font-medium text-text-tertiary uppercase">Capability Gaps</div>
                <div className="text-2xl font-semibold text-purple-300 mt-2">{capabilityGapCount}</div>
                <div className="text-xs text-text-muted mt-1">
                  {capabilityGapCount > 0 ?
                    `${(capabilityGapCount / conversations.length * 100).toFixed(0)}% of conversations` :
                    'No gaps detected'
                  }
                </div>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Quality Insights Section */}
      <div className="bg-navy-950 rounded-lg border border-navy-800 overflow-hidden mb-4">
        <div
          className="px-6 py-4 border-b border-navy-800 bg-navy-900/50 flex justify-between items-center cursor-pointer hover:bg-navy-900/70 transition-colors"
          onClick={() => setInsightsExpanded(!insightsExpanded)}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎯</span>
            <h2 className="text-lg font-semibold text-text-primary">Quality Insights</h2>
            {aiInsights.length > 0 && (
              <span className="px-2 py-1 text-xs rounded bg-navy-800 text-text-tertiary">
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
                className="px-3 py-1 text-sm border border-strategic-600 text-cyan-400 rounded hover:bg-cyan-500/10 transition-colors"
              >
                Regenerate
              </button>
            )}
            <span className="text-2xl text-text-muted">{insightsExpanded ? '▼' : '►'}</span>
          </div>
        </div>

        {insightsExpanded && (
          <div className="p-6">
            {aiInsightsLoading && (
              <div className="text-center py-8">
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
              <div className="text-center py-8 text-text-tertiary">
                <div className="text-4xl mb-2">✨</div>
                <div>No issues detected. Great job!</div>
              </div>
            )}

            {!aiInsightsLoading && aiInsights.length > 0 && (
              <>
                {/* Executive Summary - Full Width */}
                <div className="mb-6">
                  {/* Executive Summary */}
                  <div className="bg-gradient-to-r from-strategic-900/40 to-slate-900/40 rounded-lg p-5 border-2 border-strategic-600">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="text-2xl">🎯</span>
                      <h3 className="text-lg font-semibold text-cyan-300">Executive Summary</h3>
                      <span className="px-2 py-1 text-xs rounded bg-strategic-900/50 border border-strategic-600 text-strategic-300">
                        {aiInsights.length} issue{aiInsights.length !== 1 ? 's' : ''} found
                      </span>
                    </div>

                    <div className="space-y-4 text-text-secondary">
                      {/* Overall Assessment */}
                      <div>
                        <div className="font-semibold text-text-primary mb-2">Overall Performance</div>
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
                          <ul className="text-sm space-y-1 list-disc list-inside text-text-tertiary">
                            {insightsByPriority.high.slice(0, 3).map(insight => (
                              <li key={insight.id}>{insight.title}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Recommended Actions */}
                      <div>
                        <div className="font-semibold text-strategic-300 mb-2">Recommended Actions</div>
                        <ol className="text-sm space-y-2 list-decimal list-inside text-text-tertiary">
                          {(() => {
                            const actions = []

                            // Prioritize high priority issues
                            if (insightsByPriority.high.length > 0) {
                              const topHigh = insightsByPriority.high[0]
                              actions.push(`Address "${topHigh.title}" - affecting ${topHigh.evidence?.conversation_ids?.length || 0} conversations`)
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
                </div>

                {/* Compact Filter Bar */}
                <div className="bg-navy-900/30 border-b border-navy-800 py-2 px-4 -mx-6 mb-0 flex items-center gap-4 text-sm">
                  {/* Priority Filters */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-text-muted uppercase">Priority:</span>
                    <div className="flex gap-1">
                      <button
                        onClick={() => togglePriority('high')}
                        className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                          selectedPriorities.has('high')
                            ? 'bg-red-900/50 border-red-600 text-red-300'
                            : 'bg-navy-900 border-navy-700 text-text-muted hover:border-red-600/50'
                        }`}
                      >
                        {selectedPriorities.has('high') ? '✓ ' : ''}High ({insightsByPriority.high.length})
                      </button>
                      <button
                        onClick={() => togglePriority('medium')}
                        className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                          selectedPriorities.has('medium')
                            ? 'bg-amber-900/50 border-amber-600 text-amber-300'
                            : 'bg-navy-900 border-navy-700 text-text-muted hover:border-amber-600/50'
                        }`}
                      >
                        {selectedPriorities.has('medium') ? '✓ ' : ''}Medium ({insightsByPriority.medium.length})
                      </button>
                      <button
                        onClick={() => togglePriority('low')}
                        className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                          selectedPriorities.has('low')
                            ? 'bg-blue-900/50 border-blue-600 text-blue-300'
                            : 'bg-navy-900 border-navy-700 text-text-muted hover:border-blue-600/50'
                        }`}
                      >
                        {selectedPriorities.has('low') ? '✓ ' : ''}Low ({insightsByPriority.low.length})
                      </button>
                    </div>
                  </div>

                  {/* Separator */}
                  {allCategories.length > 0 && (
                    <div className="h-4 w-px bg-slate-600"></div>
                  )}

                  {/* Category Filters */}
                  {allCategories.length > 0 && (
                    <div className="flex items-center gap-2 flex-1">
                      <span className="text-xs font-medium text-text-muted uppercase">Category:</span>
                      <div className="flex flex-wrap gap-1">
                        {allCategories.map(category => {
                          const count = aiInsights.filter(i => i.category === category).length
                          return (
                            <button
                              key={category}
                              onClick={() => toggleCategory(category)}
                              className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                                selectedCategories.has(category)
                                  ? 'bg-strategic-900/50 border-strategic-600 text-strategic-300'
                                  : 'bg-navy-900 border-navy-700 text-text-muted hover:border-strategic-600/50'
                              }`}
                            >
                              {categoryIcons[category] || '📌'} {selectedCategories.has(category) ? '✓ ' : ''}{category} ({count})
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Result Count */}
                  <div className="text-xs text-text-muted whitespace-nowrap">
                    {filteredInsights.length} results
                  </div>
                </div>

                {/* Insights Cards */}
                <div className="space-y-2 mt-4">
                  {filteredInsights.length === 0 ? (
                    <div className="text-center py-8 text-text-tertiary">
                      No insights match the selected filters.
                    </div>
                  ) : (
                    filteredInsights.map(insight => {
                      const isExpanded = expandedInsightIds.has(insight.id)
                      const conversationCount = insight.evidence?.conversation_ids?.length || 0

                      // Determine card styling based on priority
                      const priorityStyles = {
                        high: {
                          border: 'border-red-600',
                          bg: 'bg-red-900/30',
                          text: 'text-red-300'
                        },
                        medium: {
                          border: 'border-amber-600',
                          bg: 'bg-amber-900/30',
                          text: 'text-amber-300'
                        },
                        low: {
                          border: 'border-blue-600',
                          bg: 'bg-blue-900/30',
                          text: 'text-blue-300'
                        }
                      }

                      const style = priorityStyles[insight.priority as keyof typeof priorityStyles]

                      return (
                        <div key={insight.id} className={`border-l-4 ${style.border} p-4 rounded ${style.bg}`}>
                          <div className="flex items-start justify-between gap-4 mb-2">
                            <h4 className={`font-semibold ${style.text} flex items-center gap-2`}>
                              <span>{categoryIcons[insight.category] || '📌'}</span>
                              {insight.title}
                            </h4>
                            <div className="flex gap-2 shrink-0">
                              <span className="px-2 py-1 text-xs rounded bg-navy-900 text-text-tertiary border border-navy-700">
                                {insight.category}
                              </span>
                              <span className={`px-2 py-1 text-xs rounded border ${
                                insight.priority === 'high' ? 'bg-red-900/50 border-red-700 text-red-300' :
                                insight.priority === 'medium' ? 'bg-amber-900/50 border-amber-700 text-amber-300' :
                                'bg-blue-900/50 border-blue-700 text-blue-300'
                              }`}>
                                {insight.priority}
                              </span>
                            </div>
                          </div>
                          <p className="text-sm text-text-secondary mb-3">{insight.description}</p>

                          {/* Recommendation Buttons */}
                          <div className="flex gap-2 mb-3">
                            {/* Code Recommendation Button */}
                            {insight.code_recommendation && (
                              <button
                                onClick={() => setSelectedInsightForModal(insight)}
                                className="px-3 py-1.5 text-xs bg-cyan-500/20 text-cyan-300 border border-strategic-600 rounded hover:bg-cyan-500/30 transition-colors flex items-center gap-2"
                              >
                                <span>💡</span>
                                View Code Recommendation
                                {insight.code_recommendation.github_issue_url && (
                                  <span className="text-green-400">✓</span>
                                )}
                              </button>
                            )}

                            {/* Knowledge Recommendation Button */}
                            {insight.knowledge_recommendation && (
                              <button
                                onClick={() => setSelectedKnowledgeForModal(insight)}
                                className="px-3 py-1.5 text-xs bg-blue-600/20 text-blue-400 border border-blue-600 rounded hover:bg-blue-600/30 transition-colors flex items-center gap-2"
                              >
                                <span>📚</span>
                                View Documentation Recommendation
                              </button>
                            )}
                          </div>

                          <div className="flex items-center justify-between p-2 bg-navy-900/50 rounded border border-navy-800">
                            <div className="flex gap-4 text-xs text-text-muted">
                              {conversationCount > 0 && (
                                <div><span className="text-text-tertiary font-medium">{conversationCount}</span> conversations</div>
                              )}
                            </div>
                            <button
                              onClick={() => toggleInsightDetail(insight.id)}
                              className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                            >
                              {isExpanded ? 'Hide' : 'Show'} Details
                            </button>
                          </div>

                          {isExpanded && insight.evidence && (
                            <div className="mt-2 p-2 bg-navy-900/50 rounded border border-navy-800">
                              <div className="text-xs text-text-muted space-y-1">
                                {insight.evidence.pattern && (
                                  <div><span className="text-text-tertiary">Pattern:</span> {insight.evidence.pattern}</div>
                                )}
                                {insight.evidence.conversation_ids && insight.evidence.conversation_ids.length > 0 && (
                                  <div>
                                    <span className="text-text-tertiary">Conversation IDs:</span>{' '}
                                    {insight.evidence.conversation_ids.slice(0, 10).map((convId, idx) => (
                                      <span key={convId}>
                                        {idx > 0 && ', '}
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            loadSnowflakeConversation(String(convId))
                                          }}
                                          className="text-cyan-400 hover:text-cyan-300 hover:underline transition-colors"
                                        >
                                          {convId}
                                        </button>
                                      </span>
                                    ))}
                                    {insight.evidence.conversation_ids.length > 10 && <span>...</span>}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* All Conversations Table */}
      <div className="bg-navy-950 rounded-lg border border-navy-800 overflow-hidden mb-8">
        <div
          className="px-6 py-4 border-b border-navy-800 bg-navy-900/50 cursor-pointer hover:bg-navy-900/70 transition-colors"
          onClick={() => setConversationsExpanded(!conversationsExpanded)}
        >
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{conversationsExpanded ? '▼' : '►'}</span>
              <div>
                <h2 className="text-lg font-semibold text-text-primary">All Conversations</h2>
                <p className="text-sm text-text-secondary mt-1">{conversations.length} total conversation(s)</p>
              </div>
            </div>
          </div>
        </div>

        {conversationsExpanded && (
          <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-navy-800">
            <thead className="bg-navy-900/30">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Persona</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Quality</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Ending</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Gaps</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Turns</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Duration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-navy-950 divide-y divide-navy-900">
              {conversations.map(conv => (
                <tr key={conv.id} className="hover:bg-navy-900/50 transition-colors">
                  <td className="px-6 py-4 text-sm text-text-secondary">{conv.id}</td>
                  <td className="px-6 py-4 text-sm text-text-secondary">{conv.persona?.name || 'Unknown'}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border ${conv.success ? 'bg-green-900/40 text-green-400 border-green-700' : 'bg-red-900/40 text-red-400 border-red-700'}`}>
                      {conv.success ? 'Success' : 'Failed'}
                    </span>
                  </td>

                  {/* Quality Score */}
                  <td className="px-6 py-4">
                    {conv.scenario?.evaluation?.quality_score !== undefined ? (
                      <QualityScoreBadge score={conv.scenario.evaluation.quality_score} compact />
                    ) : (
                      <span className="text-xs text-text-muted">—</span>
                    )}
                  </td>

                  {/* Ending Assessment */}
                  <td className="px-6 py-4">
                    {conv.scenario?.evaluation?.ending_assessment ? (
                      <EndingAssessmentBadge assessment={conv.scenario.evaluation.ending_assessment} compact />
                    ) : (
                      <span className="text-xs text-text-muted">—</span>
                    )}
                  </td>

                  {/* Gaps */}
                  <td className="px-6 py-4">
                    <div className="flex gap-1">
                      {conv.scenario?.evaluation?.knowledge_gap && (
                        <KnowledgeGapBadge gap={conv.scenario.evaluation.knowledge_gap} compact />
                      )}
                      {conv.scenario?.evaluation?.capability_gap && (
                        <CapabilityGapBadge gap={conv.scenario.evaluation.capability_gap} compact />
                      )}
                      {!conv.scenario?.evaluation?.knowledge_gap && !conv.scenario?.evaluation?.capability_gap && (
                        <span className="text-xs text-text-muted">—</span>
                      )}
                    </div>
                  </td>

                  <td className="px-6 py-4 text-sm text-text-secondary">{conv.num_turns}</td>
                  <td className="px-6 py-4 text-sm text-text-secondary">{formatDuration(conv.total_duration_ms)}</td>
                  <td className="px-6 py-4">
                    <button onClick={() => loadConversation(conv.id)} className="text-cyan-400 hover:text-cyan-300 text-sm font-medium">
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {selectedConv && (
        <div className="fixed inset-0 bg-navy-900/80 backdrop-blur-sm overflow-y-auto z-50" onClick={() => setSelectedConv(null)}>
          <div className="relative top-20 mx-auto p-5 border-2 border-navy-800 w-11/12 max-w-4xl shadow-2xl rounded-lg bg-navy-950" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-text-primary">Conversation - {selectedConv.persona?.name}</h3>
                <div className="flex items-center gap-4 mt-1 text-sm text-text-tertiary">
                  <span>Turns: {selectedConv.num_turns}</span>
                  <span>Duration: {formatDuration(selectedConv.total_duration_ms)}</span>
                  <span className={selectedConv.success ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>
                    {selectedConv.success ? '✓ Success' : '✗ Failed'}
                  </span>
                </div>
              </div>
              <button onClick={() => setSelectedConv(null)} className="text-text-tertiary hover:text-text-primary text-2xl">×</button>
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
                <div key={i} className={`p-4 rounded-lg ${msg.role === 'user' ? 'bg-strategic-900/40 border border-strategic-700' : 'bg-navy-900 border border-navy-800'}`}>
                  <div className="text-xs font-medium text-text-tertiary mb-1">{msg.role === 'user' ? '👤 User' : '🤖 Assistant'}</div>
                  <div className="text-sm text-text-secondary">{msg.content}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Snowflake Conversation Details Modal */}
      {selectedSnowflakeConvId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedSnowflakeConvId(null)}>
          <div className="bg-navy-950 rounded-lg border border-navy-800 max-w-4xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center p-6 border-b border-navy-800">
              <div>
                <h2 className="text-xl font-semibold text-text-primary">Conversation Details</h2>
                <p className="text-sm text-text-muted mt-1 font-mono">{selectedSnowflakeConvId}</p>
              </div>
              <button onClick={() => setSelectedSnowflakeConvId(null)} className="text-text-tertiary hover:text-text-primary text-2xl">×</button>
            </div>

            {snowflakeConvLoading ? (
              <div className="p-8 text-center text-text-secondary">Loading conversation...</div>
            ) : snowflakeConvDetails ? (
              <>
                {/* Conversation Metadata */}
                <div className="px-6 py-4 bg-navy-900/50 border-b border-navy-800 flex gap-6 text-sm">
                  <div>
                    <span className="text-text-muted">Turns:</span>
                    <span className="text-text-primary ml-2 font-semibold">{snowflakeConvDetails.turn_count}</span>
                  </div>
                  <div>
                    <span className="text-text-muted">Duration:</span>
                    <span className="text-text-primary ml-2 font-semibold">
                      {snowflakeConvDetails.duration_ms ? formatDuration(snowflakeConvDetails.duration_ms) : '-'}
                    </span>
                  </div>
                  {snowflakeConvDetails.triggered_by && (
                    <div>
                      <span className="text-text-muted">Channel:</span>
                      <span className="text-text-primary ml-2 font-semibold">{snowflakeConvDetails.triggered_by}</span>
                    </div>
                  )}
                </div>

                {/* Messages */}
                <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                  {snowflakeConvDetails.messages && snowflakeConvDetails.messages.length > 0 ? (
                    snowflakeConvDetails.messages.map((msg: any, i: number) => (
                      <div
                        key={i}
                        className={`p-4 rounded-lg ${
                          msg.role === 'user'
                            ? 'bg-strategic-900/40 border border-strategic-700'
                            : 'bg-navy-900 border border-navy-800'
                        }`}
                      >
                        <div className="text-xs font-medium text-text-tertiary mb-1">
                          {msg.role === 'user' ? '👤 User' : '🤖 Assistant'}
                        </div>
                        <div className="text-sm text-text-secondary whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-text-muted py-8">No messages found</div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-text-muted">Failed to load conversation</div>
            )}
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

      {/* Knowledge Recommendation Modal */}
      {selectedKnowledgeForModal && (
        <KnowledgeRecommendationModal
          insight={selectedKnowledgeForModal}
          isOpen={true}
          onClose={() => setSelectedKnowledgeForModal(null)}
        />
      )}
    </div>
  )
}
