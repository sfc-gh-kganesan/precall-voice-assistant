'use client'

import { use, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { projectsApi } from '@/lib/api'
import type { ProjectCreate, Project } from '@/lib/types'

export default function EditProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const projectId = parseInt(id)
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [formData, setFormData] = useState<ProjectCreate>({
    name: '',
    description: '',
    business_context: '',
    agent_endpoint: '',
    auth_type: 'none',
    auth_credentials: {},
    custom_headers: {},
    source_database: '',
    source_schema: '',
    source_table: '',
    github_owner: '',
    github_repo: '',
    target_path: '',
  })

  useEffect(() => {
    loadProject()
  }, [])

  const loadProject = async () => {
    try {
      const response = await projectsApi.get(projectId)
      const project: Project = response.data
      setFormData({
        name: project.name,
        description: project.description || '',
        business_context: project.business_context,
        agent_endpoint: project.agent_endpoint,
        auth_type: project.auth_type,
        auth_credentials: {},  // Don't pre-fill credentials for security
        custom_headers: {},
        source_database: project.source_database || '',
        source_schema: project.source_schema || '',
        source_table: project.source_table || '',
        github_owner: project.github_owner || '',
        github_repo: project.github_repo || '',
        target_path: project.target_path || '',
      })
    } catch (error) {
      alert('Failed to load project')
      console.error(error)
      router.push('/projects')
    } finally {
      setInitialLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await projectsApi.update(projectId, formData)
      router.push(`/projects/${projectId}`)
    } catch (error) {
      alert('Failed to update project')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  if (initialLoading) {
    return <div className="p-8 text-center text-text-secondary">Loading...</div>
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-text-primary">Edit Project</h1>
        <p className="mt-2 text-sm text-text-secondary">
          Update your AI agent configuration
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-navy-950 shadow-sm rounded border border-navy-800 p-6">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-text-secondary">
            Project Name *
          </label>
          <input
            type="text"
            id="name"
            required
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
            placeholder="My AI Agent Project"
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-text-secondary">
            Description
          </label>
          <input
            type="text"
            id="description"
            value={formData.description || ''}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
            placeholder="Brief description of your agent"
          />
        </div>

        <div>
          <label htmlFor="business_context" className="block text-sm font-medium text-text-secondary">
            Business Context *
          </label>
          <textarea
            id="business_context"
            required
            value={formData.business_context}
            onChange={(e) => setFormData({...formData, business_context: e.target.value})}
            rows={4}
            className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
            placeholder="Describe what your agent does, what questions it can answer, what data it has access to..."
          />
          <p className="mt-1 text-xs text-text-tertiary">
            This context helps generate realistic test scenarios
          </p>
        </div>

        <div>
          <label htmlFor="agent_endpoint" className="block text-sm font-medium text-text-secondary">
            Agent Endpoint URL *
          </label>
          <input
            type="url"
            id="agent_endpoint"
            required
            value={formData.agent_endpoint}
            onChange={(e) => setFormData({...formData, agent_endpoint: e.target.value})}
            className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
            placeholder="https://your-agent.com/api/chat"
          />
        </div>

        {/* Data Source Section */}
        <div className="pt-6 border-t border-navy-800">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Data Source</h3>
          <p className="text-sm text-text-tertiary mb-4">
            Snowflake table containing conversation traces for analysis
          </p>

          <div className="space-y-4">
            <div>
              <label htmlFor="source_database" className="block text-sm font-medium text-text-secondary">
                Database Name
              </label>
              <input
                type="text"
                id="source_database"
                value={formData.source_database || ''}
                onChange={(e) => setFormData({...formData, source_database: e.target.value})}
                className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
                placeholder="AI_FDE"
              />
            </div>

            <div>
              <label htmlFor="source_schema" className="block text-sm font-medium text-text-secondary">
                Schema Name
              </label>
              <input
                type="text"
                id="source_schema"
                value={formData.source_schema || ''}
                onChange={(e) => setFormData({...formData, source_schema: e.target.value})}
                className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
                placeholder="CX360_DEMO"
              />
            </div>

            <div>
              <label htmlFor="source_table" className="block text-sm font-medium text-text-secondary">
                Table Name
              </label>
              <input
                type="text"
                id="source_table"
                value={formData.source_table || ''}
                onChange={(e) => setFormData({...formData, source_table: e.target.value})}
                className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
                placeholder="AGENT_TRACES"
              />
              <p className="mt-1 text-xs text-text-tertiary">
                Leave blank to use environment defaults (AI_FDE.CX360_DEMO.AGENT_TRACES)
              </p>
            </div>
          </div>
        </div>

        {/* GitHub Configuration Section */}
        <div className="pt-6 border-t border-navy-800">
          <h3 className="text-lg font-semibold text-text-primary mb-4">GitHub Configuration</h3>
          <p className="text-sm text-text-tertiary mb-4">
            Configure GitHub repository for code recommendations and issue creation
          </p>

          <div className="space-y-4">
            <div>
              <label htmlFor="github_owner" className="block text-sm font-medium text-text-secondary">
                GitHub Owner/Organization
              </label>
              <input
                type="text"
                id="github_owner"
                value={formData.github_owner || ''}
                onChange={(e) => setFormData({...formData, github_owner: e.target.value})}
                className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
                placeholder="snowflakedb"
              />
            </div>

            <div>
              <label htmlFor="github_repo" className="block text-sm font-medium text-text-secondary">
                GitHub Repository Name
              </label>
              <input
                type="text"
                id="github_repo"
                value={formData.github_repo || ''}
                onChange={(e) => setFormData({...formData, github_repo: e.target.value})}
                className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
                placeholder="aura"
              />
            </div>

            <div>
              <label htmlFor="target_path" className="block text-sm font-medium text-text-secondary">
                Target Code Path (Optional)
              </label>
              <input
                type="text"
                id="target_path"
                value={formData.target_path || ''}
                onChange={(e) => setFormData({...formData, target_path: e.target.value})}
                className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
                placeholder="src/agent"
              />
              <p className="mt-1 text-xs text-text-tertiary">
                Specific path in repository where agent code lives (optional)
              </p>
            </div>
          </div>
        </div>

        <div>
          <label htmlFor="auth_type" className="block text-sm font-medium text-text-secondary">
            Authentication Type
          </label>
          <select
            id="auth_type"
            value={formData.auth_type}
            onChange={(e) => setFormData({...formData, auth_type: e.target.value})}
            className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
          >
            <option value="none">None</option>
            <option value="bearer">Bearer Token</option>
            <option value="api_key">API Key</option>
            <option value="basic">Basic Auth</option>
          </select>
        </div>

        {formData.auth_type !== 'none' && (
          <div>
            <label htmlFor="auth_token" className="block text-sm font-medium text-text-secondary">
              {formData.auth_type === 'bearer' ? 'Bearer Token' :
               formData.auth_type === 'api_key' ? 'API Key' :
               'Username:Password'}
            </label>
            <input
              type="text"
              id="auth_token"
              value={formData.auth_credentials?.token || ''}
              onChange={(e) => setFormData({
                ...formData,
                auth_credentials: {token: e.target.value}
              })}
              className="mt-1 block w-full rounded border border-navy-800 bg-navy-900 text-text-primary px-3 py-2 shadow-sm focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-colors"
              placeholder={formData.auth_type === 'basic' ? 'username:password' : 'Your token/key (leave blank to keep existing)'}
            />
            <p className="mt-1 text-xs text-text-tertiary">
              Leave blank to keep existing credentials
            </p>
          </div>
        )}

        <div className="flex justify-end gap-4 pt-4">
          <button
            type="button"
            onClick={() => router.push(`/projects/${projectId}`)}
            className="px-4 py-2 text-sm font-medium text-text-secondary bg-navy-900 border border-navy-800 rounded shadow-sm hover:bg-navy-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-cyan-500 rounded shadow-sm hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Updating...' : 'Update Project'}
          </button>
        </div>
      </form>
    </div>
  )
}
