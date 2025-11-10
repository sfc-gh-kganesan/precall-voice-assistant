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
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await projectsApi.create(formData)
      router.push('/projects')
    } catch (error) {
      alert('Failed to create project')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-serif font-semibold text-parchment-100">Create New Project</h1>
        <p className="mt-2 text-sm text-parchment-200">
          Configure your AI agent for testing
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-slate-900 shadow-sm rounded border border-slate-700 p-6">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-parchment-200">
            Project Name *
          </label>
          <input
            type="text"
            id="name"
            required
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
            placeholder="My AI Agent Project"
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
            placeholder="Brief description of your agent"
          />
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
            placeholder="Describe what your agent does, what questions it can answer, what data it has access to..."
          />
          <p className="mt-1 text-xs text-parchment-300">
            This context helps generate realistic test scenarios
          </p>
        </div>

        <div>
          <label htmlFor="agent_endpoint" className="block text-sm font-medium text-parchment-200">
            Agent Endpoint URL *
          </label>
          <input
            type="url"
            id="agent_endpoint"
            required
            value={formData.agent_endpoint}
            onChange={(e) => setFormData({...formData, agent_endpoint: e.target.value})}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 shadow-sm focus:border-strategic-600 focus:outline-none focus:ring-1 focus:ring-strategic-600"
            placeholder="https://your-agent.com/api/chat"
          />
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
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  )
}
