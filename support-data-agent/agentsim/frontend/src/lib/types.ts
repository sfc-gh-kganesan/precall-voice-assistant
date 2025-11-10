// Type definitions matching backend schemas

export interface Project {
  id: number
  name: string
  description?: string
  business_context: string
  agent_endpoint: string
  auth_type: string
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  business_context: string
  agent_endpoint: string
  auth_type: string
  auth_credentials: Record<string, string>
  custom_headers?: Record<string, string>
  conversation_examples?: any[]
}

export interface Simulation {
  id: number
  project_id: number
  num_simulations: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  created_at: string
}

export interface SimulationCreate {
  project_id: number
  num_simulations: number
  concurrency?: number
  max_turns?: number
  timeout_seconds?: number
  stop_conditions?: string[]
  metrics_config?: string[]
  edge_case_ratio?: number
  custom_scenarios?: CustomScenario[]
}

export interface CustomScenario {
  persona: Persona
  initial_query: string
  expected_outcome: string
  complexity: string
  category: string
}

export interface Persona {
  name: string
  goal: string
  tone: string
  personality_traits: string[]
  technical_level: string
  edge_case: boolean
}

export interface PersonaTemplate {
  id: number
  project_id: number
  name: string
  goal: string
  tone: string
  personality_traits: string[]
  technical_level: string
  edge_case: boolean
  default_query?: string
  expected_outcome?: string
  complexity: string
  category: string
  knowledge_base?: Record<string, any>
  created_at: string
}

export interface PersonaTemplateCreate {
  name: string
  goal: string
  tone?: string
  personality_traits?: string[]
  technical_level?: string
  edge_case?: boolean
  default_query?: string
  expected_outcome?: string
  complexity?: string
  category?: string
  knowledge_base?: Record<string, any>
}

export interface SimulationResults {
  id: number
  project_id: number
  num_simulations: number
  status: string
  successful: number
  failed: number
  aggregate_metrics: Record<string, any>
}

export interface ConversationSummary {
  id: number
  simulation_id: number
  persona: Record<string, any>
  success: boolean
  num_turns: number
  total_duration_ms: number
  stop_reason?: string
  started_at?: string
  completed_at?: string
  error_message?: string
}

export interface Message {
  id: number
  role: string
  content: string
  timestamp: string
  latency_ms?: number
}

export interface Conversation {
  id: number
  simulation_id: number
  persona: Record<string, any>
  scenario: Record<string, any>
  success: boolean
  num_turns: number
  total_duration_ms: number
  stop_reason?: string
  started_at: string
  completed_at?: string
  messages: Message[]
}
