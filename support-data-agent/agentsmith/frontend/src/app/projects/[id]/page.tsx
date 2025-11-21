'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { projectsApi, simulationsApi } from '@/lib/api'
import type { Project, Simulation } from '@/lib/types'

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

interface ProjectMetrics {
  total_conversations: number
  date_range_start?: string
  date_range_end?: string
  avg_duration_ms?: number
  avg_turns?: number
  error_rate?: number
  total_voice_interactions: number
  total_text_interactions: number
}

interface ConversationSummary {
  conversation_id: string
  start_time: string
  end_time?: string
  duration_ms?: number
  turn_count: number
  triggered_by?: string
  has_error: boolean
  status_code?: string
}

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const projectId = parseInt(id)
  const [project, setProject] = useState<Project | null>(null)
  const [simulations, setSimulations] = useState<Simulation[]>([])
  const [metrics, setMetrics] = useState<ProjectMetrics | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [conversationsTotal, setConversationsTotal] = useState(0)
  const [conversationsOffset, setConversationsOffset] = useState(0)
  const [conversationsLimit] = useState(5)
  const [conversationsFilter, setConversationsFilter] = useState<string | null>(null)
  const [errorsOnly, setErrorsOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [metricsLoading, setMetricsLoading] = useState(false)
  const [conversationsLoading, setConversationsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [historyExpanded, setHistoryExpanded] = useState(false)
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [conversationDetails, setConversationDetails] = useState<any>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [latestAnalysis, setLatestAnalysis] = useState<Simulation | null>(null)
  const [latestInsights, setLatestInsights] = useState<any[]>([])
  const [insightsLoading, setInsightsLoading] = useState(false)
  const [conversationsExpanded, setConversationsExpanded] = useState(false)

  useEffect(() => {
    loadData()
    loadMetrics()
    loadConversations()
  }, [])

  useEffect(() => {
    loadConversations()
  }, [conversationsOffset, conversationsFilter, errorsOnly])

  useEffect(() => {
    // Load latest insights when simulations change
    if (simulations.length > 0) {
      loadLatestInsights()
    }
  }, [simulations])

  const loadData = async () => {
    try {
      setLoading(true)
      const [projectRes, simulationsRes] = await Promise.all([
        projectsApi.get(projectId),
        projectsApi.getSimulations(projectId)
      ])
      setProject(projectRes.data)
      setSimulations(simulationsRes.data)
      setError(null)

      // Load latest insights after simulations are loaded
      // We'll call it separately since it depends on simulations state
    } catch (err) {
      setError('Failed to load deployment data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadMetrics = async () => {
    try {
      setMetricsLoading(true)
      const response = await projectsApi.getMetrics(projectId)
      setMetrics(response.data)
    } catch (err) {
      console.error('Failed to load metrics:', err)
    } finally {
      setMetricsLoading(false)
    }
  }

  const loadConversations = async () => {
    try {
      setConversationsLoading(true)
      const response = await projectsApi.getConversations(projectId, {
        limit: conversationsLimit,
        offset: conversationsOffset,
        triggered_by: conversationsFilter || undefined,
        errors_only: errorsOnly
      })
      setConversations(response.data.conversations)
      setConversationsTotal(response.data.total)
    } catch (err) {
      console.error('Failed to load conversations:', err)
    } finally {
      setConversationsLoading(false)
    }
  }

  const loadLatestInsights = async () => {
    try {
      setInsightsLoading(true)
      // Find the most recent completed analysis
      const completedAnalyses = simulations.filter(s => s.status === 'completed').sort((a, b) => {
        return new Date(b.completed_at || b.created_at).getTime() - new Date(a.completed_at || a.created_at).getTime()
      })

      if (completedAnalyses.length > 0) {
        const latest = completedAnalyses[0]
        setLatestAnalysis(latest)

        // Load insights for this analysis
        const response = await simulationsApi.getAIInsights(latest.id)
        setLatestInsights(response.data)
      }
    } catch (err) {
      console.error('Failed to load latest insights:', err)
    } finally {
      setInsightsLoading(false)
    }
  }

  const loadConversationDetails = async (conversationId: string) => {
    try {
      setDetailsLoading(true)
      setSelectedConversationId(conversationId)
      const response = await projectsApi.getConversationDetails(projectId, conversationId)
      setConversationDetails(response.data)
    } catch (err) {
      console.error('Failed to load conversation details:', err)
      alert('Failed to load conversation details')
      setSelectedConversationId(null)
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleDeleteSimulation = async (simulationId: number) => {
    if (!confirm('Are you sure you want to delete this analysis? This cannot be undone.')) {
      return
    }

    try {
      await simulationsApi.delete(simulationId)
      await loadData()
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to delete analysis'
      alert(errorMsg)
      console.error(err)
    }
  }

  const handleStopSimulation = async (simulationId: number) => {
    if (!confirm('Are you sure you want to stop this analysis?')) {
      return
    }

    try {
      await simulationsApi.stop(simulationId)
      await loadData()
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to stop analysis'
      alert(errorMsg)
      console.error(err)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-parchment-200">Loading...</div>
  }

  if (error || !project) {
    return (
      <div className="p-8">
        <div className="bg-red-900/30 border border-red-700 text-red-200 rounded p-4">
          {error || 'Deployment not found'}
        </div>
        <Link href="/projects" className="mt-4 inline-block text-strategic-500 hover:text-strategic-400">
          ← Back to Deployments
        </Link>
      </div>
    )
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      pending: 'bg-slate-800 text-parchment-300 border border-slate-700',
      running: 'bg-strategic-900/40 text-strategic-400 border border-strategic-700',
      completed: 'bg-green-900/40 text-green-400 border border-green-700',
      failed: 'bg-red-900/40 text-red-400 border border-red-700'
    }
    return (
      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${colors[status as keyof typeof colors] || colors.pending}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <Link href="/projects" className="text-sm text-strategic-500 hover:text-strategic-400 mb-2 inline-block">
          ← Back to Deployments
        </Link>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-serif font-semibold text-parchment-100">{project.name}</h1>
            <p className="mt-2 text-sm text-parchment-200">{project.description}</p>
            {project.agent_endpoint && (
              <div className="mt-2 text-sm text-parchment-300">
                <span className="font-medium">Endpoint:</span> {project.agent_endpoint}
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <Link
              href={`/projects/${projectId}/edit`}
              className="inline-flex items-center rounded bg-slate-700 px-4 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-slate-600 transition-colors"
            >
              Edit Deployment
            </Link>
            <Link
              href={`/projects/${projectId}/simulate`}
              className="inline-flex items-center rounded bg-green-700 px-4 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-green-600 transition-colors"
            >
              Run Analysis
            </Link>
          </div>
        </div>
      </div>

      {/* Live Metrics */}
      <div className="mb-8">
        <h2 className="text-xl font-serif font-semibold text-parchment-100 mb-4">Live Metrics from Snowflake</h2>
        {metricsLoading ? (
          <div className="text-center py-8 text-parchment-300">Loading metrics...</div>
        ) : metrics && metrics.total_conversations > 0 ? (
          <>
            <div className="grid grid-cols-5 gap-4 mb-4">
              <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
                <div className="text-sm font-medium text-parchment-300">Total Conversations</div>
                <div className="text-3xl font-serif font-semibold text-parchment-100 mt-2">{metrics.total_conversations}</div>
              </div>
              <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
                <div className="text-sm font-medium text-parchment-300">Avg Duration</div>
                <div className="text-3xl font-serif font-semibold text-parchment-100 mt-2">
                  {metrics.avg_duration_ms ? formatDuration(metrics.avg_duration_ms) : '-'}
                </div>
              </div>
              <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
                <div className="text-sm font-medium text-parchment-300">Avg Turns</div>
                <div className="text-3xl font-serif font-semibold text-parchment-100 mt-2">
                  {metrics.avg_turns ? metrics.avg_turns.toFixed(1) : '-'}
                </div>
              </div>
              <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
                <div className="text-sm font-medium text-parchment-300">Error Rate</div>
                <div className={`text-3xl font-serif font-semibold mt-2 ${metrics.error_rate && metrics.error_rate > 0.1 ? 'text-red-400' : 'text-green-400'}`}>
                  {metrics.error_rate ? `${(metrics.error_rate * 100).toFixed(1)}%` : '0%'}
                </div>
              </div>
              <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
                <div className="text-sm font-medium text-parchment-300">Interactions</div>
                <div className="text-2xl font-serif font-semibold text-parchment-100 mt-2">
                  🎤 {metrics.total_voice_interactions} | 💬 {metrics.total_text_interactions}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="bg-slate-900 rounded-lg border border-slate-700 p-12 text-center">
            <div className="text-parchment-300">No conversation data available yet</div>
            <div className="text-sm text-parchment-400 mt-2">Conversations will appear here once they are logged to Snowflake</div>
          </div>
        )}
      </div>

      {/* Latest Insights from Most Recent Analysis */}
      {latestAnalysis && (
        <div className="mb-8">
          <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-700 bg-slate-800/50 flex justify-between items-center">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🎯</span>
                <h2 className="text-xl font-serif font-semibold text-parchment-100">Latest Insights</h2>
                {latestAnalysis && (
                  <span className="px-2 py-1 text-xs rounded bg-slate-700 text-parchment-300">
                    Analysis #{latestAnalysis.id} · {formatDate(latestAnalysis.completed_at || latestAnalysis.created_at)}
                  </span>
                )}
              </div>
              {latestAnalysis && (
                <Link
                  href={`/simulations/${latestAnalysis.id}/results`}
                  className="px-4 py-2 bg-strategic-600 text-parchment-50 rounded hover:bg-strategic-500 transition-colors text-sm font-medium"
                >
                  View Full Analysis
                </Link>
              )}
            </div>

            {insightsLoading ? (
              <div className="p-8 text-center text-parchment-300">Loading insights...</div>
            ) : latestInsights.length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-4xl mb-2">✨</div>
                <div className="text-parchment-300">No issues detected in latest analysis. Great job!</div>
              </div>
            ) : (
              <div className="p-6">
                {/* Insights Summary Grid */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  {/* High Priority Issues */}
                  <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
                    <div className="text-xs font-medium text-red-300 uppercase mb-1">High Priority</div>
                    <div className="text-3xl font-semibold text-red-400">
                      {latestInsights.filter(i => i.priority === 'high').length}
                    </div>
                    <div className="text-xs text-parchment-400 mt-1">issues require attention</div>
                  </div>

                  {/* Medium Priority Issues */}
                  <div className="bg-amber-900/20 border border-amber-700 rounded-lg p-4">
                    <div className="text-xs font-medium text-amber-300 uppercase mb-1">Medium Priority</div>
                    <div className="text-3xl font-semibold text-amber-400">
                      {latestInsights.filter(i => i.priority === 'medium').length}
                    </div>
                    <div className="text-xs text-parchment-400 mt-1">optimization opportunities</div>
                  </div>

                  {/* Low Priority Issues */}
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4">
                    <div className="text-xs font-medium text-blue-300 uppercase mb-1">Low Priority</div>
                    <div className="text-3xl font-semibold text-blue-400">
                      {latestInsights.filter(i => i.priority === 'low').length}
                    </div>
                    <div className="text-xs text-parchment-400 mt-1">minor improvements</div>
                  </div>
                </div>

                {/* Top High Priority Insights */}
                {latestInsights.filter(i => i.priority === 'high').length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-red-300 uppercase tracking-wide">Top Concerns</h3>
                    {latestInsights
                      .filter(i => i.priority === 'high')
                      .slice(0, 3)
                      .map((insight) => (
                        <div key={insight.id} className="border-l-4 border-red-600 bg-red-900/30 p-4 rounded">
                          <h4 className="font-semibold text-red-300 mb-1">{insight.title}</h4>
                          <p className="text-sm text-parchment-200">{insight.description}</p>
                          {insight.evidence && (
                            <div className="mt-2 text-xs text-parchment-400">
                              {insight.evidence.conversation_ids && (
                                <span>Affects {insight.evidence.conversation_ids.length} conversation(s)</span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Conversations Browser */}
      <div className="bg-slate-900 rounded border border-slate-700 overflow-hidden mb-8">
        <div
          className="px-6 py-4 border-b border-slate-700 bg-slate-800/50 cursor-pointer hover:bg-slate-800/70 transition-colors"
          onClick={() => setConversationsExpanded(!conversationsExpanded)}
        >
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{conversationsExpanded ? '▼' : '►'}</span>
              <div>
                <h2 className="text-lg font-serif font-semibold text-parchment-100">Conversation Browser</h2>
                <p className="text-sm text-parchment-200 mt-1">{conversationsTotal} total conversation(s)</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setErrorsOnly(!errorsOnly)
                }}
                className={`px-3 py-1.5 text-sm rounded transition-colors ${errorsOnly ? 'bg-red-600 text-white' : 'bg-slate-700 text-parchment-200 hover:bg-slate-600'}`}
              >
                {errorsOnly ? 'Show All' : 'Errors Only'}
              </button>
              <select
                value={conversationsFilter || ''}
                onChange={(e) => {
                  e.stopPropagation()
                  setConversationsFilter(e.target.value || null)
                }}
                onClick={(e) => e.stopPropagation()}
                className="px-3 py-1.5 text-sm bg-slate-700 text-parchment-200 rounded border-0 focus:ring-2 focus:ring-strategic-500"
              >
                <option value="">All Channels</option>
                <option value="voice">Voice</option>
                <option value="text">Text</option>
              </select>
            </div>
          </div>
        </div>

        {conversationsExpanded && (
          <>
            {conversationsLoading ? (
              <div className="text-center py-12 text-parchment-300">Loading conversations...</div>
            ) : conversations.length === 0 ? (
              <div className="text-center py-12 px-4 text-parchment-300">
                No conversations found
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-700">
                    <thead className="bg-slate-800/30">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Start Time</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Duration</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Turns</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Channel</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody className="bg-slate-900 divide-y divide-slate-800">
                      {conversations.map((conv) => (
                        <tr
                          key={conv.conversation_id}
                          onClick={() => loadConversationDetails(conv.conversation_id)}
                          className="hover:bg-slate-800/50 transition-colors cursor-pointer"
                        >
                          <td className="px-6 py-4 text-sm font-mono text-parchment-200">{conv.conversation_id.substring(0, 8)}...</td>
                          <td className="px-6 py-4 text-sm text-parchment-200">{formatDate(conv.start_time)}</td>
                          <td className="px-6 py-4 text-sm text-parchment-200">
                            {conv.duration_ms ? formatDuration(conv.duration_ms) : '-'}
                          </td>
                          <td className="px-6 py-4 text-sm text-parchment-200">{conv.turn_count}</td>
                          <td className="px-6 py-4 text-sm text-parchment-200">
                            {conv.triggered_by || '-'}
                          </td>
                          <td className="px-6 py-4">
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border ${conv.has_error ? 'bg-red-900/40 text-red-400 border-red-700' : 'bg-green-900/40 text-green-400 border-green-700'}`}>
                              {conv.has_error ? `Error (${conv.status_code})` : 'Success'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Pagination */}
                {conversationsTotal > conversationsLimit && (
                  <div className="px-6 py-4 border-t border-slate-700 flex justify-between items-center">
                    <div className="text-sm text-parchment-300">
                      Showing {conversationsOffset + 1} to {Math.min(conversationsOffset + conversationsLimit, conversationsTotal)} of {conversationsTotal}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setConversationsOffset(Math.max(0, conversationsOffset - conversationsLimit))}
                        disabled={conversationsOffset === 0}
                        className="px-3 py-1 text-sm bg-slate-700 text-parchment-200 rounded hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setConversationsOffset(conversationsOffset + conversationsLimit)}
                        disabled={conversationsOffset + conversationsLimit >= conversationsTotal}
                        className="px-3 py-1 text-sm bg-slate-700 text-parchment-200 rounded hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>

      {/* Analysis History (Collapsible) */}
      <div className="bg-slate-900 rounded border border-slate-700 overflow-hidden">
        <div
          className="px-6 py-4 border-b border-slate-700 bg-slate-800/50 flex justify-between items-center cursor-pointer hover:bg-slate-800/70 transition-colors"
          onClick={() => setHistoryExpanded(!historyExpanded)}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">📊</span>
            <h2 className="text-lg font-serif font-semibold text-parchment-100">Analysis History</h2>
            {simulations.length > 0 && (
              <span className="px-2 py-1 text-xs rounded bg-slate-700 text-parchment-300">
                {simulations.length} run{simulations.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <span className="text-2xl text-parchment-400">{historyExpanded ? '▼' : '►'}</span>
        </div>

        {historyExpanded && (
          <>
            {simulations.length === 0 ? (
              <div className="text-center py-12 px-4">
                <p className="text-parchment-200 mb-4">No analysis runs yet for this deployment.</p>
                <Link
                  href={`/projects/${projectId}/simulate`}
                  className="inline-flex items-center rounded bg-strategic-600 px-4 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-strategic-500 transition-colors"
                >
                  Run First Analysis
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-700">
                  <thead className="bg-slate-800/30">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Conversations</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Created</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Completed</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-slate-900 divide-y divide-slate-800">
                    {simulations.map((sim) => (
                      <tr key={sim.id} className="hover:bg-slate-800/50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-parchment-100">{sim.id}</td>
                        <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(sim.status)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-parchment-200">{sim.conversation_count}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-parchment-200">{formatDate(sim.created_at)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-parchment-200">
                          {sim.completed_at ? formatDate(sim.completed_at) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex items-center gap-2">
                            {sim.status === 'completed' && (
                              <Link
                                href={`/simulations/${sim.id}/results`}
                                className="p-2 text-strategic-500 hover:text-strategic-400 hover:bg-strategic-900/30 rounded transition-colors"
                                title="View Results"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                              </Link>
                            )}
                            {sim.status === 'running' && (
                              <>
                                <Link
                                  href={`/simulations/${sim.id}`}
                                  className="p-2 text-strategic-500 hover:text-strategic-400 hover:bg-strategic-900/30 rounded transition-colors"
                                  title="Monitor"
                                >
                                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                  </svg>
                                </Link>
                                <button
                                  onClick={() => handleStopSimulation(sim.id)}
                                  className="p-2 text-yellow-500 hover:text-yellow-400 hover:bg-yellow-900/20 rounded transition-colors"
                                  title="Stop Analysis"
                                >
                                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                                  </svg>
                                </button>
                              </>
                            )}
                            {sim.status !== 'running' && (
                              <button
                                onClick={() => handleDeleteSimulation(sim.id)}
                                className="p-2 text-red-500 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors"
                                title="Delete Analysis"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {/* Conversation Details Modal */}
      {selectedConversationId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedConversationId(null)}>
          <div className="bg-slate-900 rounded-lg border border-slate-700 max-w-4xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center p-6 border-b border-slate-700">
              <div>
                <h2 className="text-xl font-serif font-semibold text-parchment-100">Conversation Details</h2>
                <p className="text-sm text-parchment-400 mt-1 font-mono">{selectedConversationId}</p>
              </div>
              <button onClick={() => setSelectedConversationId(null)} className="text-parchment-300 hover:text-parchment-100 text-2xl">×</button>
            </div>

            {detailsLoading ? (
              <div className="p-8 text-center text-parchment-200">Loading conversation...</div>
            ) : conversationDetails ? (
              <>
                {/* Conversation Metadata */}
                <div className="px-6 py-4 bg-slate-800/50 border-b border-slate-700 flex gap-6 text-sm">
                  <div>
                    <span className="text-parchment-400">Turns:</span>
                    <span className="text-parchment-100 ml-2 font-semibold">{conversationDetails.turn_count}</span>
                  </div>
                  <div>
                    <span className="text-parchment-400">Duration:</span>
                    <span className="text-parchment-100 ml-2 font-semibold">
                      {conversationDetails.duration_ms ? formatDuration(conversationDetails.duration_ms) : '-'}
                    </span>
                  </div>
                  {conversationDetails.triggered_by && (
                    <div>
                      <span className="text-parchment-400">Channel:</span>
                      <span className="text-parchment-100 ml-2 font-semibold">{conversationDetails.triggered_by}</span>
                    </div>
                  )}
                </div>

                {/* Messages */}
                <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                  {conversationDetails.messages && conversationDetails.messages.length > 0 ? (
                    conversationDetails.messages.map((msg: any, i: number) => (
                      <div
                        key={i}
                        className={`p-4 rounded-lg ${
                          msg.role === 'user'
                            ? 'bg-strategic-900/40 border border-strategic-700'
                            : 'bg-slate-800 border border-slate-700'
                        }`}
                      >
                        <div className="text-xs font-medium text-parchment-300 mb-1">
                          {msg.role === 'user' ? '👤 User' : '🤖 Assistant'}
                        </div>
                        <div className="text-sm text-parchment-200 whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-parchment-400 py-8">No messages found</div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-parchment-400">Failed to load conversation</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
