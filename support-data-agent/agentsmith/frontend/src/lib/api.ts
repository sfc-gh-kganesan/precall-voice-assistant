import axios from 'axios'
import type {
  Project,
  ProjectCreate,
  Simulation,
  SimulationCreate,
  SimulationResults,
  ConversationSummary,
  Conversation,
  PersonaTemplate,
  PersonaTemplateCreate,
  ImprovementSuggestion,
} from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'  // Changed from 8000 to 8080

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Projects API
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects/'),
  get: (id: number) => api.get<Project>(`/api/projects/${id}`),
  create: (data: ProjectCreate) => api.post<Project>('/api/projects/', data),
  update: (id: number, data: ProjectCreate) => api.put<Project>(`/api/projects/${id}`, data),
  delete: (id: number) => api.delete(`/api/projects/${id}`),
  getSimulations: (id: number) => api.get<Simulation[]>(`/api/projects/${id}/simulations`),

  // Persona templates
  getPersonas: (id: number) => api.get<PersonaTemplate[]>(`/api/projects/${id}/personas`),
  createPersona: (projectId: number, data: PersonaTemplateCreate) =>
    api.post<PersonaTemplate>(`/api/projects/${projectId}/personas`, data),
  deletePersona: (projectId: number, personaId: number) =>
    api.delete(`/api/projects/${projectId}/personas/${personaId}`),

  // Live data from Snowflake
  getMetrics: (id: number) => api.get(`/api/projects/${id}/metrics`),
  getConversations: (id: number, params?: { limit?: number; offset?: number; triggered_by?: string; errors_only?: boolean }) =>
    api.get(`/api/projects/${id}/conversations`, { params }),
  generateInsights: (id: number, data?: { date_from?: string; date_to?: string }) =>
    api.post(`/api/projects/${id}/insights`, data || {}),
}

// Simulations API
export const simulationsApi = {
  create: (data: SimulationCreate) => api.post<Simulation>('/api/simulations/', data),
  get: (id: number) => api.get<Simulation>(`/api/simulations/${id}`),
  getResults: (id: number) => api.get<SimulationResults>(`/api/simulations/${id}/results`),
  getConversations: (id: number) => api.get<ConversationSummary[]>(`/api/simulations/${id}/conversations`),
  delete: (id: number) => api.delete(`/api/simulations/${id}`),
  stop: (id: number) => api.post(`/api/simulations/${id}/stop`),

  // AI Insights
  getAIInsights: (id: number) => api.get<ImprovementSuggestion[]>(`/api/simulations/${id}/ai-insights`),
  regenerateAIInsights: (id: number) => api.post<ImprovementSuggestion[]>(`/api/simulations/${id}/ai-insights/regenerate`),
  createGithubIssue: (simulationId: number, insightId: number, customContent?: { title?: string; body?: string }) =>
    api.post<{ success: boolean; issue_url: string; insight_id: number }>(
      `/api/simulations/${simulationId}/insights/${insightId}/create-github-issue`,
      customContent || {}
    ),
}

// Conversations API
export const conversationsApi = {
  get: (id: number) => api.get<Conversation>(`/api/conversations/${id}`),
}

export default api
