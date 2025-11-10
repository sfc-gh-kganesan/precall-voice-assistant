'use client'

import { use, useState, useEffect } from 'react'
import Link from 'next/link'
import { projectsApi } from '@/lib/api'
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
          <Link
            href={`/projects/${projectId}/simulate`}
            className="inline-flex items-center rounded bg-green-700 px-4 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-green-600 transition-colors"
          >
            Run New Simulation
          </Link>
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
                      {sim.status === 'completed' && (
                        <Link
                          href={`/simulations/${sim.id}/results`}
                          className="text-strategic-500 hover:text-strategic-400 font-medium"
                        >
                          View Results
                        </Link>
                      )}
                      {sim.status === 'running' && (
                        <Link
                          href={`/simulations/${sim.id}`}
                          className="text-strategic-500 hover:text-strategic-400 font-medium"
                        >
                          Monitor
                        </Link>
                      )}
                      {(sim.status === 'pending' || sim.status === 'failed') && (
                        <span className="text-parchment-300">-</span>
                      )}
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
