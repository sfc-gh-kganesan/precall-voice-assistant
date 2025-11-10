'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { simulationsApi } from '@/lib/api'
import type { SimulationResults, ConversationSummary } from '@/lib/types'

export default function InsightsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const simulationId = parseInt(id)
  const [results, setResults] = useState<SimulationResults | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
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
        <h2 className="text-lg font-serif font-semibold text-parchment-100">Recommendations</h2>
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
    </div>
  )
}
