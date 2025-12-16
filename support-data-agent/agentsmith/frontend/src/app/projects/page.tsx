'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { projectsApi } from '@/lib/api'
import type { Project } from '@/lib/types'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const response = await projectsApi.list()
      setProjects(response.data)
    } catch (err) {
      setError('Failed to load deployments')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this deployment?')) return

    try {
      await projectsApi.delete(id)
      await loadProjects()
    } catch (err) {
      alert('Failed to delete deployment')
      console.error(err)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-text-secondary">Loading deployments...</div>
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-text-primary">Deployments</h1>
          <p className="mt-2 text-sm text-text-secondary">
            Configure chatbot deployments for analysis
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <Link
            href="/projects/new"
            className="block rounded bg-cyan-500 px-4 py-2 text-center text-sm font-medium text-white shadow hover:bg-cyan-400 transition-colors"
          >
            New Deployment
          </Link>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-900/30 border border-red-700 text-red-200 rounded">
          {error}
        </div>
      )}

      <div className="mt-8 flow-root">
        {projects.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-text-secondary">No deployments yet. Create your first deployment to get started!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {projects.map((project) => (
              <div key={project.id} className="bg-navy-950 shadow-sm rounded border border-navy-800 p-6 hover:border-cyan-400/50 transition-colors">
                <div className="flex justify-between items-start">
                  <Link href={`/projects/${project.id}`} className="flex-1 cursor-pointer group">
                    <h3 className="text-lg font-semibold text-text-primary group-hover:text-cyan-400 transition-colors">{project.name}</h3>
                    <p className="mt-1 text-sm text-text-secondary">{project.description}</p>
                    <div className="mt-2 text-sm text-text-secondary">
                      <span className="font-medium">Endpoint:</span> {project.agent_endpoint}
                    </div>
                  </Link>
                  <div className="ml-4 flex gap-2">
                    <Link
                      href={`/projects/${project.id}`}
                      className="inline-flex items-center rounded bg-cyan-500 px-3 py-2 text-sm font-medium text-white shadow hover:bg-cyan-400 transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View History
                    </Link>
                    <Link
                      href={`/projects/${project.id}/simulate`}
                      className="inline-flex items-center rounded bg-green-600 px-3 py-2 text-sm font-medium text-white shadow hover:bg-green-500 transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Analyze
                    </Link>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(project.id)
                      }}
                      className="inline-flex items-center rounded bg-red-600 px-3 py-2 text-sm font-medium text-white shadow hover:bg-red-500 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
