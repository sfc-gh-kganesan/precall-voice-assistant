'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { simulationsApi } from '@/lib/api'
import type { SimulationResults, ConversationSummary, ImprovementSuggestion } from '@/lib/types'

export default function InsightsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const simulationId = parseInt(id)
  const [results, setResults] = useState<SimulationResults | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [aiInsights, setAiInsights] = useState<ImprovementSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [aiInsightsLoading, setAiInsightsLoading] = useState(false)
  const [aiInsightsError, setAiInsightsError] = useState<string | null>(null)

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

      // Load AI insights separately (may take a while if generating)
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

  if (loading) return <div className="p-8 text-center text-parchment-200">Loading...</div>
  if (!results) return <div className="p-8 text-center text-parchment-200">No results available</div>

  // Analysis
  const failedConvs = conversations.filter(c => !c.success)
  const avgTurns = conversations.reduce((sum, c) => sum + c.num_turns, 0) / conversations.length
  const avgDuration = conversations.reduce((sum, c) => sum + c.total_duration_ms, 0) / conversations.length
  const timeoutFailures = failedConvs.filter(c => c.stop_reason === 'timeout').length
  const maxTurnsFailures = failedConvs.filter(c => c.stop_reason === 'max_turns').length
  const errorFailures = failedConvs.filter(c => c.stop_reason === 'error').length
  const multiTurnSuccess = conversations.filter(c => c.num_turns > 1 && c.success).length
  const multiTurnRate = multiTurnSuccess / conversations.filter(c => c.num_turns > 1).length * 100 || 0

  // Generate recommendations
  const recommendations = []
  if (results.successful / results.num_simulations < 0.7) {
    recommendations.push({
      type: 'critical',
      title: 'Low Success Rate',
      description: `Only ${(results.successful / results.num_simulations * 100).toFixed(1)}% of conversations succeeded. This indicates significant issues with your agent.`,
      actions: ['Review failed conversation logs', 'Check agent error handling', 'Verify business logic']
    })
  }

  if (timeoutFailures > 0) {
    recommendations.push({
      type: 'warning',
      title: 'Timeout Issues',
      description: `${timeoutFailures} conversations timed out. Your agent may be taking too long to respond.`,
      actions: ['Increase timeout settings', 'Optimize agent response time', 'Check for blocking operations']
    })
  }

  if (maxTurnsFailures > results.num_simulations * 0.3) {
    recommendations.push({
      type: 'warning',
      title: 'Excessive Turn Count',
      description: `${maxTurnsFailures} conversations hit max turns without completing. Your agent may be going in circles.`,
      actions: ['Review conversation flow', 'Improve task completion logic', 'Add clearer completion signals']
    })
  }

  if (errorFailures > 0) {
    recommendations.push({
      type: 'critical',
      title: 'Agent Errors',
      description: `${errorFailures} conversations failed with errors. Check your agent logs for exceptions.`,
      actions: ['Review error logs', 'Add error handling', 'Test edge cases']
    })
  }

  if (multiTurnRate < 50 && conversations.some(c => c.num_turns > 1)) {
    recommendations.push({
      type: 'info',
      title: 'Multi-Turn Challenges',
      description: `Only ${multiTurnRate.toFixed(1)}% of multi-turn conversations succeeded. Your agent struggles with follow-up questions.`,
      actions: ['Improve context retention', 'Test conversation continuity', 'Add conversation state management']
    })
  }

  if (avgDuration > 30000) {
    recommendations.push({
      type: 'info',
      title: 'Slow Response Times',
      description: `Average conversation duration is ${(avgDuration / 1000).toFixed(1)}s. Consider optimization.`,
      actions: ['Profile agent performance', 'Cache common queries', 'Optimize database queries']
    })
  }

  if (recommendations.length === 0) {
    recommendations.push({
      type: 'success',
      title: 'Great Performance!',
      description: 'Your agent is performing well across all metrics.',
      actions: ['Continue monitoring', 'Test with more edge cases', 'Expand test scenarios']
    })
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-serif font-semibold text-parchment-100">Insights & Recommendations</h1>
            <p className="text-sm text-parchment-300 mt-2">Analysis for Simulation {results.id}</p>
          </div>
          <Link href={`/simulations/${simulationId}/results`} className="px-4 py-2 border-2 border-strategic-600 text-strategic-500 rounded hover:bg-strategic-600/10 transition-colors text-sm">
            Back to Results
          </Link>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 mb-8">
        <h2 className="text-lg font-serif font-semibold text-parchment-100 mb-4">Key Metrics</h2>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="text-sm text-parchment-300">Average Turns</div>
            <div className="text-2xl font-serif font-semibold text-parchment-100 mt-1">{avgTurns.toFixed(1)}</div>
          </div>
          <div>
            <div className="text-sm text-parchment-300">Average Duration</div>
            <div className="text-2xl font-serif font-semibold text-parchment-100 mt-1">{(avgDuration / 1000).toFixed(1)}s</div>
          </div>
          <div>
            <div className="text-sm text-parchment-300">Multi-Turn Success</div>
            <div className="text-2xl font-serif font-semibold text-parchment-100 mt-1">{isNaN(multiTurnRate) ? 'N/A' : `${multiTurnRate.toFixed(1)}%`}</div>
          </div>
        </div>
      </div>

      {/* Failure Analysis */}
      {failedConvs.length > 0 && (
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 mb-8">
          <h2 className="text-lg font-serif font-semibold text-parchment-100 mb-4">Failure Analysis</h2>
          <div className="space-y-3">
            {timeoutFailures > 0 && (
              <div className="flex justify-between items-center p-3 bg-red-900/30 border border-red-700 rounded">
                <span className="text-sm font-medium text-parchment-200">Timeout Failures</span>
                <span className="text-sm text-red-400">{timeoutFailures} ({(timeoutFailures / failedConvs.length * 100).toFixed(0)}%)</span>
              </div>
            )}
            {maxTurnsFailures > 0 && (
              <div className="flex justify-between items-center p-3 bg-amber-900/30 border border-amber-700 rounded">
                <span className="text-sm font-medium text-parchment-200">Max Turns Reached</span>
                <span className="text-sm text-amber-400">{maxTurnsFailures} ({(maxTurnsFailures / failedConvs.length * 100).toFixed(0)}%)</span>
              </div>
            )}
            {errorFailures > 0 && (
              <div className="flex justify-between items-center p-3 bg-red-900/30 border border-red-700 rounded">
                <span className="text-sm font-medium text-parchment-200">Agent Errors</span>
                <span className="text-sm text-red-400">{errorFailures} ({(errorFailures / failedConvs.length * 100).toFixed(0)}%)</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="space-y-4">
        <h2 className="text-lg font-serif font-semibold text-parchment-100">Rule-Based Recommendations</h2>
        {recommendations.map((rec, i) => {
          const typeStyles = {
            critical: 'border-red-600 bg-red-900/30',
            warning: 'border-amber-600 bg-amber-900/30',
            info: 'border-strategic-600 bg-strategic-900/30',
            success: 'border-green-600 bg-green-900/30'
          }
          const textColors = {
            critical: 'text-red-300',
            warning: 'text-amber-300',
            info: 'text-strategic-400',
            success: 'text-green-300'
          }
          return (
            <div key={i} className={`border-l-4 p-6 rounded ${typeStyles[rec.type as keyof typeof typeStyles]}`}>
              <h3 className={`font-serif font-semibold text-lg mb-2 ${textColors[rec.type as keyof typeof textColors]}`}>{rec.title}</h3>
              <p className="text-sm text-parchment-200 mb-4">{rec.description}</p>
              <div>
                <div className="text-sm font-medium text-parchment-300 mb-2">Recommended Actions:</div>
                <ul className="list-disc list-inside space-y-1">
                  {rec.actions.map((action, j) => (
                    <li key={j} className="text-sm text-parchment-200">{action}</li>
                  ))}
                </ul>
              </div>
            </div>
          )
        })}
      </div>

      {/* AI-Powered Insights */}
      <div className="mt-8 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-serif font-semibold text-parchment-100">AI-Powered Analysis</h2>
          <button
            onClick={regenerateInsights}
            disabled={aiInsightsLoading}
            className="px-3 py-1 text-sm border border-strategic-600 text-strategic-500 rounded hover:bg-strategic-600/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {aiInsightsLoading ? 'Generating...' : 'Regenerate'}
          </button>
        </div>

        {aiInsightsLoading && (
          <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 text-center">
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
          <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 text-center text-parchment-300">
            No AI insights available yet. They will be generated automatically after simulation completes.
          </div>
        )}

        {!aiInsightsLoading && aiInsights.length > 0 && aiInsights.map((insight) => {
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
            <div key={insight.id} className={`border-l-4 p-6 rounded ${priorityStyles[insight.priority]}`}>
              <div className="flex items-start justify-between gap-4 mb-2">
                <h3 className={`font-serif font-semibold text-lg ${priorityColors[insight.priority]}`}>
                  <span className="mr-2">{categoryIcons[insight.category] || '📌'}</span>
                  {insight.title}
                </h3>
                <div className="flex gap-2">
                  <span className="px-2 py-1 text-xs rounded bg-slate-800 text-parchment-300 border border-slate-600">
                    {insight.category}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded font-medium ${priorityColors[insight.priority]}`}>
                    {insight.priority.toUpperCase()}
                  </span>
                </div>
              </div>
              <p className="text-sm text-parchment-200 mb-4">{insight.description}</p>

              {/* Evidence */}
              {insight.evidence && (
                <div className="mt-4 p-3 bg-slate-800/50 rounded border border-slate-700">
                  <div className="text-xs font-medium text-parchment-300 mb-2">Evidence:</div>
                  <div className="text-xs text-parchment-400 space-y-1">
                    {insight.evidence.pattern && (
                      <div><span className="text-parchment-300">Pattern:</span> {insight.evidence.pattern}</div>
                    )}
                    {insight.evidence.conversation_ids && insight.evidence.conversation_ids.length > 0 && (
                      <div><span className="text-parchment-300">Affected Conversations:</span> {insight.evidence.conversation_ids.length}</div>
                    )}
                    {insight.evidence.affected_personas && insight.evidence.affected_personas.length > 0 && (
                      <div><span className="text-parchment-300">Affected Personas:</span> {insight.evidence.affected_personas.join(', ')}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
