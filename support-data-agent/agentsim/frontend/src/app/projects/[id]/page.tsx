'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { projectsApi, simulationsApi } from '@/lib/api'
import type { Project, Simulation } from '@/lib/types'

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const projectId = parseInt(id)
  const [project, setProject] = useState<Project | null>(null)
  const [simulations, setSimulations] = useState<Simulation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

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
    } catch (err) {
      setError('Failed to load project data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteSimulation = async (simulationId: number) => {
    if (!confirm('Are you sure you want to delete this simulation? This cannot be undone.')) {
      return
    }

    try {
      await simulationsApi.delete(simulationId)
      // Reload simulations list
      await loadData()
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to delete simulation'
      alert(errorMsg)
      console.error(err)
    }
  }

  const handleStopSimulation = async (simulationId: number) => {
    if (!confirm('Are you sure you want to stop this simulation?')) {
      return
    }

    try {
      await simulationsApi.stop(simulationId)
      // Reload simulations list
      await loadData()
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to stop simulation'
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
          {error || 'Project not found'}
        </div>
        <Link href="/projects" className="mt-4 inline-block text-strategic-500 hover:text-strategic-400">
          ← Back to Projects
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
          ← Back to Projects
        </Link>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-serif font-semibold text-parchment-100">{project.name}</h1>
            <p className="mt-2 text-sm text-parchment-200">{project.description}</p>
            <div className="mt-2 text-sm text-parchment-300">
              <span className="font-medium">Endpoint:</span> {project.agent_endpoint}
            </div>
          </div>
          <div className="flex gap-2">
            <Link
              href={`/projects/${projectId}/edit`}
              className="inline-flex items-center rounded bg-slate-700 px-4 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-slate-600 transition-colors"
            >
              Edit Project
            </Link>
            <Link
              href={`/projects/${projectId}/simulate`}
              className="inline-flex items-center rounded bg-green-700 px-4 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-green-600 transition-colors"
            >
              Run New Simulation
            </Link>
          </div>
        </div>
      </div>

      {/* Simulations History */}
      <div className="bg-slate-900 rounded border border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700 bg-slate-800/50">
          <h2 className="text-lg font-serif font-semibold text-parchment-100">Simulation History</h2>
          <p className="text-sm text-parchment-200 mt-1">{simulations.length} total simulation(s)</p>
        </div>

        {simulations.length === 0 ? (
          <div className="text-center py-12 px-4">
            <p className="text-parchment-200 mb-4">No simulations yet for this project.</p>
            <Link
              href={`/projects/${projectId}/simulate`}
              className="inline-flex items-center rounded bg-strategic-600 px-4 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-strategic-500 transition-colors"
            >
              Run First Simulation
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-700">
              <thead className="bg-slate-800/30">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase tracking-wider">
                    Tests
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase tracking-wider">
                    Completed
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-parchment-200 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-slate-900 divide-y divide-slate-800">
                {simulations.map((sim) => (
                  <tr key={sim.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-parchment-100">
                      {sim.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(sim.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-parchment-200">
                      {sim.num_simulations}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-parchment-200">
                      {formatDate(sim.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-parchment-200">
                      {sim.completed_at ? formatDate(sim.completed_at) : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        {/* View Results icon button */}
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

                        {/* Monitor icon button */}
                        {sim.status === 'running' && (
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
                        )}

                        {/* Stop icon button */}
                        {sim.status === 'running' && (
                          <button
                            onClick={() => handleStopSimulation(sim.id)}
                            className="p-2 text-yellow-500 hover:text-yellow-400 hover:bg-yellow-900/20 rounded transition-colors"
                            title="Stop Simulation"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                            </svg>
                          </button>
                        )}

                        {/* Delete icon button */}
                        {sim.status !== 'running' && (
                          <button
                            onClick={() => handleDeleteSimulation(sim.id)}
                            className="p-2 text-red-500 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors"
                            title="Delete Simulation"
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
      </div>
    </div>
  )
}
