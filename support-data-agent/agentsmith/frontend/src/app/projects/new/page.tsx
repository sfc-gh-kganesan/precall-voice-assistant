'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { projectsApi } from '@/lib/api'
import type { ProjectCreate } from '@/lib/types'

export default function NewProjectPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
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
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await projectsApi.create(formData)
      router.push('/projects')
    } catch (error) {
      alert('Failed to create deployment')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-serif font-semibold text-parchment-100">Create New Deployment</h1>
        <p className="mt-2 text-sm text-parchment-200">
          Connect chatbot data source
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-slate-900 shadow-sm rounded border border-slate-700 p-6">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-parchment-200">
            Deployment Name *
          </label>
          <input
            type="text"
            id="name"
            required
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
            placeholder="Snowflake Website Agent"
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-parchment-200">
            Description
          </label>
          <input
            type="text"
            id="description"
            value={formData.description || ''}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
            placeholder="Brief description of your chatbot"
          />
        </div>

        {/* Data Source Section */}
        <div className="pt-6 border-t border-slate-700">
          <h3 className="text-lg font-semibold text-parchment-100 mb-4">Data Source</h3>
          <p className="text-sm text-parchment-300 mb-4">
            Snowflake table containing conversation traces for analysis
          </p>

          <div className="space-y-4">
            <div>
              <label htmlFor="source_database" className="block text-sm font-medium text-parchment-200">
                Database Name
              </label>
              <input
                type="text"
                id="source_database"
                value={formData.source_database || ''}
                onChange={(e) => setFormData({...formData, source_database: e.target.value})}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
                placeholder="AI_FDE"
              />
            </div>

            <div>
              <label htmlFor="source_schema" className="block text-sm font-medium text-parchment-200">
                Schema Name
              </label>
              <input
                type="text"
                id="source_schema"
                value={formData.source_schema || ''}
                onChange={(e) => setFormData({...formData, source_schema: e.target.value})}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
                placeholder="CX360_DEMO"
              />
            </div>

            <div>
              <label htmlFor="source_table" className="block text-sm font-medium text-parchment-200">
                Table Name
              </label>
              <input
                type="text"
                id="source_table"
                value={formData.source_table || ''}
                onChange={(e) => setFormData({...formData, source_table: e.target.value})}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
                placeholder="AGENT_TRACES"
              />
              <p className="mt-1 text-xs text-parchment-300">
                Leave blank to use environment defaults (AI_FDE.CX360_DEMO.AGENT_TRACES)
              </p>
            </div>
          </div>
        </div>

        <div>
          <label htmlFor="business_context" className="block text-sm font-medium text-parchment-200">
            Business Context *
          </label>
          <textarea
            id="business_context"
            required
            value={formData.business_context}
            onChange={(e) => setFormData({...formData, business_context: e.target.value})}
            rows={4}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
            placeholder="Describe what your chatbot does, what questions it answers, what data it has access to..."
          />
          <p className="mt-1 text-xs text-parchment-300">
            This context helps AI generate actionable insights and recommendations
          </p>
        </div>

        <div>
          <label htmlFor="agent_endpoint" className="block text-sm font-medium text-parchment-200">
            Agent Endpoint URL (Optional)
          </label>
          <input
            type="url"
            id="agent_endpoint"
            value={formData.agent_endpoint || ''}
            onChange={(e) => setFormData({...formData, agent_endpoint: e.target.value})}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
            placeholder="https://your-agent.com/api/chat"
          />
          <p className="mt-1 text-xs text-parchment-300">
            Optionally provide agent endpoint for re-running failed conversations
          </p>
        </div>

        <div>
          <label htmlFor="auth_type" className="block text-sm font-medium text-parchment-200">
            Authentication Type
          </label>
          <select
            id="auth_type"
            value={formData.auth_type}
            onChange={(e) => setFormData({...formData, auth_type: e.target.value})}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
          >
            <option value="none">None</option>
            <option value="bearer">Bearer Token</option>
            <option value="api_key">API Key</option>
            <option value="basic">Basic Auth</option>
          </select>
        </div>

        {formData.auth_type !== 'none' && (
          <div>
            <label htmlFor="auth_token" className="block text-sm font-medium text-parchment-200">
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
              className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
              placeholder={formData.auth_type === 'basic' ? 'username:password' : 'Your token/key'}
            />
          </div>
        )}

        {/* GitHub Configuration Section */}
        <div className="pt-6 border-t border-slate-700">
          <h3 className="text-lg font-semibold text-parchment-100 mb-4">GitHub Configuration (Optional)</h3>
          <p className="text-sm text-parchment-300 mb-4">
            Configure GitHub repository for automated code recommendations and issue creation
          </p>

          <div className="space-y-4">
            <div>
              <label htmlFor="github_owner" className="block text-sm font-medium text-parchment-200">
                GitHub Owner/Organization
              </label>
              <input
                type="text"
                id="github_owner"
                value={formData.github_owner || ''}
                onChange={(e) => setFormData({...formData, github_owner: e.target.value})}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
                placeholder="snowflakedb"
              />
            </div>

            <div>
              <label htmlFor="github_repo" className="block text-sm font-medium text-parchment-200">
                Repository Name
              </label>
              <input
                type="text"
                id="github_repo"
                value={formData.github_repo || ''}
                onChange={(e) => setFormData({...formData, github_repo: e.target.value})}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
                placeholder="aura"
              />
            </div>

            <div>
              <label htmlFor="target_path" className="block text-sm font-medium text-parchment-200">
                Target Path (Optional)
              </label>
              <input
                type="text"
                id="target_path"
                value={formData.target_path || ''}
                onChange={(e) => setFormData({...formData, target_path: e.target.value})}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
                placeholder="support-data-agent/troubleshooting"
              />
              <p className="mt-1 text-xs text-parchment-300">
                Path within repository to focus code recommendations (e.g., src/agent)
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-4 pt-4">
          <button
            type="button"
            onClick={() => router.push('/projects')}
            className="px-4 py-2 text-sm font-medium text-parchment-200 bg-slate-800 border border-slate-700 rounded shadow-sm hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-parchment-50 bg-strategic-600 rounded shadow-sm hover:bg-strategic-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Creating...' : 'Create Deployment'}
          </button>
        </div>
      </form>
    </div>
  )
}
