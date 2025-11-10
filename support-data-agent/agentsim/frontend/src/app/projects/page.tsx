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
      setError('Failed to load projects')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this project?')) return
    
    try {
      await projectsApi.delete(id)
      await loadProjects()
    } catch (err) {
      alert('Failed to delete project')
      console.error(err)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-parchment-200">Loading projects...</div>
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-serif font-semibold text-parchment-100">Projects</h1>
          <p className="mt-2 text-sm text-parchment-200">
            Configure your AI agents for testing
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <Link
            href="/projects/new"
            className="block rounded bg-strategic-600 px-4 py-2 text-center text-sm font-medium text-parchment-50 shadow hover:bg-strategic-500 transition-colors"
          >
            New Project
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
            <p className="text-parchment-200">No projects yet. Create your first project to get started!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {projects.map((project) => (
              <div key={project.id} className="bg-slate-900 shadow-sm rounded border border-slate-700 p-6">
                <div className="flex justify-between items-start">
                  <Link href={`/projects/${project.id}`} className="flex-1 cursor-pointer group">
                    <h3 className="text-lg font-serif font-semibold text-parchment-100 group-hover:text-strategic-500 transition-colors">{project.name}</h3>
                    <p className="mt-1 text-sm text-parchment-200">{project.description}</p>
                    <div className="mt-2 text-sm text-parchment-200">
                      <span className="font-medium">Endpoint:</span> {project.agent_endpoint}
                    </div>
                  </Link>
                  <div className="ml-4 flex gap-2">
                    <Link
                      href={`/projects/${project.id}`}
                      className="inline-flex items-center rounded bg-strategic-600 px-3 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-strategic-500 transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View History
                    </Link>
                    <Link
                      href={`/projects/${project.id}/simulate`}
                      className="inline-flex items-center rounded bg-green-700 px-3 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-green-600 transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Run Simulation
                    </Link>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(project.id)
                      }}
                      className="inline-flex items-center rounded bg-red-700 px-3 py-2 text-sm font-medium text-parchment-50 shadow hover:bg-red-600 transition-colors"
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
