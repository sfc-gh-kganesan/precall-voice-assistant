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
  delete: (id: number) => api.delete(`/api/projects/${id}`),
  getSimulations: (id: number) => api.get<Simulation[]>(`/api/projects/${id}/simulations`),

  // Persona templates
  getPersonas: (id: number) => api.get<PersonaTemplate[]>(`/api/projects/${id}/personas`),
  createPersona: (projectId: number, data: PersonaTemplateCreate) =>
    api.post<PersonaTemplate>(`/api/projects/${projectId}/personas`, data),
  deletePersona: (projectId: number, personaId: number) =>
    api.delete(`/api/projects/${projectId}/personas/${personaId}`),
}

// Simulations API
export const simulationsApi = {
  create: (data: SimulationCreate) => api.post<Simulation>('/api/simulations/', data),
  get: (id: number) => api.get<Simulation>(`/api/simulations/${id}`),
  getResults: (id: number) => api.get<SimulationResults>(`/api/simulations/${id}/results`),
  getConversations: (id: number) => api.get<ConversationSummary[]>(`/api/simulations/${id}/conversations`),
  delete: (id: number) => api.delete(`/api/simulations/${id}`),
  stop: (id: number) => api.post(`/api/simulations/${id}/stop`),
}

// Conversations API
export const conversationsApi = {
  get: (id: number) => api.get<Conversation>(`/api/conversations/${id}`),
}

export default api
