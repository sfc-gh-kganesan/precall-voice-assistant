'use client'

import { use, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { projectsApi, simulationsApi } from '@/lib/api'
import type { Project, SimulationCreate } from '@/lib/types'

export default function AnalyzePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const projectId = parseInt(id)
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastAnalysisDate, setLastAnalysisDate] = useState<Date | null>(null)

  const [formData, setFormData] = useState<SimulationCreate>({
    project_id: projectId,
    num_simulations: 100, // Max conversations to analyze
    concurrency: 2,
    max_turns: 20,
    timeout_seconds: 120,
    conversation_timeout_seconds: 600,
    stop_conditions: ['llm_judge', 'max_turns'],
    metrics_config: ['efficiency', 'quality', 'tool_usage'],
    // Analysis-specific filters
    date_from: null,
    date_to: null,
    conversation_ids: null,
    triggered_by: null,
    include_errors_only: false,
  })

  const [useSinceLastAnalysis, setUseSinceLastAnalysis] = useState(false)
  const [useCustomDateRange, setUseCustomDateRange] = useState(false)

  useEffect(() => {
    loadProject()
    loadLastAnalysisDate()
  }, [])

  const loadProject = async () => {
    try {
      const response = await projectsApi.get(projectId)
      setProject(response.data)
    } catch (error) {
      console.error('Failed to load project:', error)
    }
  }

  const loadLastAnalysisDate = async () => {
    try {
      // Get the most recent completed simulation for this project
      const response = await projectsApi.getSimulations(projectId)
      const completedSimulations = response.data.filter(
        (sim: any) => sim.status === 'completed'
      )
      if (completedSimulations.length > 0) {
        // Sort by created_at descending and take the first
        completedSimulations.sort((a: any, b: any) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        setLastAnalysisDate(new Date(completedSimulations[0].created_at))
      }
    } catch (error) {
      console.error('Failed to load last analysis date:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      // Prepare date range
      let dateFrom = formData.date_from
      let dateTo = formData.date_to

      if (useSinceLastAnalysis && lastAnalysisDate) {
        dateFrom = lastAnalysisDate
        dateTo = new Date()
      } else if (!useCustomDateRange) {
        // Default: last 7 days
        dateTo = new Date()
        dateFrom = new Date()
        dateFrom.setDate(dateFrom.getDate() - 7)
      }

      const simulationData = {
        ...formData,
        date_from: dateFrom,
        date_to: dateTo,
        // Remove persona-related fields (not used in analysis mode)
        edge_case_ratio: undefined,
        custom_scenarios: undefined,
      }

      const response = await simulationsApi.create(simulationData)
      router.push(`/simulations/${response.data.id}`)
    } catch (error) {
      alert('Failed to create analysis')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (date: Date | null | undefined) => {
    if (!date) return ''
    return date.toISOString().split('T')[0] // YYYY-MM-DD
  }

  if (!project) {
    return <div className="p-8 text-center text-text-secondary">Loading...</div>
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-sans font-bold text-text-primary">Configure AI Analysis</h1>
        <p className="mt-2 text-sm text-text-secondary">
          Analyzing: {project.name}
        </p>
        <p className="mt-1 text-xs text-text-tertiary">
          Analyze existing conversations from Snowflake to identify patterns, errors, and improvement opportunities
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Conversation Selection */}
        <div className="bg-navy-950 shadow-sm rounded-lg border border-navy-800 p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Conversation Selection</h2>
          <p className="text-sm text-text-tertiary mb-4">Choose which conversations to analyze from your Snowflake data</p>

          <div className="space-y-4">
            {/* Date Range Options */}
            <div className="space-y-3">
              {/* Default: Last 7 days */}
              <label className="flex items-center space-x-3 p-3 rounded-md cursor-pointer transition-colors bg-navy-900 border border-navy-800 hover:border-navy-700">
                <input
                  type="radio"
                  name="dateRange"
                  checked={!useSinceLastAnalysis && !useCustomDateRange}
                  onChange={() => {
                    setUseSinceLastAnalysis(false)
                    setUseCustomDateRange(false)
                  }}
                  className="text-strategic-600"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-text-primary">Last 7 days</div>
                  <div className="text-xs text-text-tertiary">Analyze conversations from the past week</div>
                </div>
              </label>

              {/* Since Last Analysis */}
              {lastAnalysisDate && (
                <label className="flex items-center space-x-3 p-3 rounded-md cursor-pointer transition-colors bg-navy-900 border border-navy-800 hover:border-navy-700">
                  <input
                    type="radio"
                    name="dateRange"
                    checked={useSinceLastAnalysis}
                    onChange={() => {
                      setUseSinceLastAnalysis(true)
                      setUseCustomDateRange(false)
                    }}
                    className="text-strategic-600"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-text-primary">New since last analysis</div>
                    <div className="text-xs text-text-tertiary">
                      Since {lastAnalysisDate.toLocaleDateString()} at {lastAnalysisDate.toLocaleTimeString()}
                    </div>
                  </div>
                </label>
              )}

              {/* Custom Date Range */}
              <label className="flex items-center space-x-3 p-3 rounded-md cursor-pointer transition-colors bg-navy-900 border border-navy-800 hover:border-navy-700">
                <input
                  type="radio"
                  name="dateRange"
                  checked={useCustomDateRange}
                  onChange={() => {
                    setUseSinceLastAnalysis(false)
                    setUseCustomDateRange(true)
                  }}
                  className="text-strategic-600"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-text-primary">Custom date range</div>
                  <div className="text-xs text-text-tertiary">Specify exact start and end dates</div>
                </div>
              </label>

              {/* Custom Date Inputs */}
              {useCustomDateRange && (
                <div className="ml-8 grid grid-cols-2 gap-4 p-4 bg-navy-900/50 rounded-md">
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-1">
                      From Date
                    </label>
                    <input
                      type="date"
                      value={formatDate(formData.date_from)}
                      onChange={(e) => setFormData({...formData, date_from: e.target.value ? new Date(e.target.value) : null})}
                      className="w-full rounded-md border border-navy-800 bg-navy-950 text-text-primary px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-1">
                      To Date
                    </label>
                    <input
                      type="date"
                      value={formatDate(formData.date_to)}
                      onChange={(e) => setFormData({...formData, date_to: e.target.value ? new Date(e.target.value) : null})}
                      className="w-full rounded-md border border-navy-800 bg-navy-950 text-text-primary px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Filters */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-navy-800">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Channel Filter
                </label>
                <select
                  value={formData.triggered_by || ''}
                  onChange={(e) => setFormData({...formData, triggered_by: e.target.value || null})}
                  className="w-full rounded-md border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                >
                  <option value="">All Channels</option>
                  <option value="voice">Voice Only</option>
                  <option value="text">Text Only</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Max Conversations
                </label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={formData.num_simulations}
                  onChange={(e) => setFormData({...formData, num_simulations: parseInt(e.target.value) || 1})}
                  className="w-full rounded-md border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                />
                <p className="mt-1 text-xs text-text-tertiary">Maximum number of conversations to analyze</p>
              </div>
            </div>

            {/* Errors Only Toggle */}
            <label className="flex items-center space-x-2 p-3 rounded-md cursor-pointer transition-colors bg-navy-900 border border-navy-800 hover:border-navy-700">
              <input
                type="checkbox"
                checked={formData.include_errors_only}
                onChange={(e) => setFormData({...formData, include_errors_only: e.target.checked})}
                className="rounded text-strategic-600"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-text-primary">Analyze errors only</div>
                <div className="text-xs text-text-tertiary">Focus analysis on conversations that had errors</div>
              </div>
            </label>
          </div>
        </div>

        {/* Analysis Configuration */}
        <div className="bg-navy-950 shadow-sm rounded-lg border border-navy-800 p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Analysis Configuration</h2>
          <p className="text-sm text-text-tertiary mb-4">Configure how conversations are analyzed and evaluated</p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary">
                Concurrency
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.concurrency}
                onChange={(e) => setFormData({...formData, concurrency: parseInt(e.target.value) || 1})}
                className="mt-1 block w-full rounded-md border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              />
              <p className="mt-1 text-xs text-text-tertiary">Number of conversations to analyze in parallel</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary">
                Timeout (seconds)
              </label>
              <input
                type="number"
                min="30"
                max="600"
                value={formData.timeout_seconds}
                onChange={(e) => setFormData({...formData, timeout_seconds: parseInt(e.target.value) || 30})}
                className="mt-1 block w-full rounded-md border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              />
              <p className="mt-1 text-xs text-text-tertiary">Timeout for stop conditions evaluation</p>
            </div>
          </div>

          {/* Stop Conditions */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Evaluation Criteria
            </label>
            <div className="space-y-2">
              <label className="flex items-center space-x-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={formData.stop_conditions?.includes('llm_judge') ?? false}
                  onChange={(e) => {
                    const updated = e.target.checked
                      ? [...(formData.stop_conditions || []), 'llm_judge']
                      : (formData.stop_conditions || []).filter(c => c !== 'llm_judge')
                    setFormData({...formData, stop_conditions: updated})
                  }}
                  className="rounded"
                />
                <span>LLM Judge - AI evaluates conversation success</span>
              </label>
              <label className="flex items-center space-x-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={formData.stop_conditions?.includes('max_turns') ?? false}
                  onChange={(e) => {
                    const updated = e.target.checked
                      ? [...(formData.stop_conditions || []), 'max_turns']
                      : (formData.stop_conditions || []).filter(c => c !== 'max_turns')
                    setFormData({...formData, stop_conditions: updated})
                  }}
                  className="rounded"
                />
                <span>Max Turns - Flag conversations exceeding turn limit</span>
              </label>
            </div>
          </div>

          {/* Metrics */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Metrics to Calculate
            </label>
            <div className="space-y-2">
              <label className="flex items-center space-x-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={formData.metrics_config?.includes('efficiency') ?? false}
                  onChange={(e) => {
                    const updated = e.target.checked
                      ? [...(formData.metrics_config || []), 'efficiency']
                      : (formData.metrics_config || []).filter(m => m !== 'efficiency')
                    setFormData({...formData, metrics_config: updated})
                  }}
                  className="rounded"
                />
                <span>Efficiency - Duration, turns, latency</span>
              </label>
              <label className="flex items-center space-x-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={formData.metrics_config?.includes('quality') ?? false}
                  onChange={(e) => {
                    const updated = e.target.checked
                      ? [...(formData.metrics_config || []), 'quality']
                      : (formData.metrics_config || []).filter(m => m !== 'quality')
                    setFormData({...formData, metrics_config: updated})
                  }}
                  className="rounded"
                />
                <span>Quality - Success rate, error patterns</span>
              </label>
              <label className="flex items-center space-x-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={formData.metrics_config?.includes('tool_usage') ?? false}
                  onChange={(e) => {
                    const updated = e.target.checked
                      ? [...(formData.metrics_config || []), 'tool_usage']
                      : (formData.metrics_config || []).filter(m => m !== 'tool_usage')
                    setFormData({...formData, metrics_config: updated})
                  }}
                  className="rounded"
                />
                <span>Tool Usage - Tool call frequency and patterns</span>
              </label>
            </div>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => router.push(`/projects/${projectId}`)}
            className="px-4 py-2 text-sm font-medium text-text-secondary bg-navy-900 border border-navy-800 rounded-md hover:bg-navy-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 text-sm font-medium text-white bg-green-700 rounded-md hover:bg-green-600 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Starting Analysis...' : 'Start Analysis'}
          </button>
        </div>
      </form>
    </div>
  )
}
