// Type definitions matching backend schemas

export interface Project {
  id: number
  name: string
  description?: string
  business_context: string
  agent_endpoint?: string
  auth_type: string
  source_database?: string
  source_schema?: string
  source_table?: string
  github_owner?: string
  github_repo?: string
  target_path?: string
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  business_context: string
  agent_endpoint?: string
  auth_type: string
  auth_credentials: Record<string, string>
  custom_headers?: Record<string, string>
  conversation_examples?: any[]
  source_database?: string
  source_schema?: string
  source_table?: string
  github_owner?: string
  github_repo?: string
  target_path?: string
}

export interface Simulation {
  id: number
  project_id: number
  num_simulations: number
  conversation_count: number
  conversation_timeout_seconds: number
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
  conversation_timeout_seconds?: number
  stop_conditions?: string[]
  metrics_config?: string[]

  // Analysis-specific filters (for analyzing existing conversations from Snowflake)
  date_from?: Date | null
  date_to?: Date | null
  conversation_ids?: string[] | null
  triggered_by?: string | null
  include_errors_only?: boolean

  // Legacy fields (for simulation mode with personas)
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

  // Evaluation data from ConversationAnalyzer
  scenario?: {
    evaluation?: {
      quality_score?: number           // 0-1
      confidence?: number              // 0-1
      ending_assessment?: string       // appropriate/premature/excessive
      reasoning?: string
      knowledge_gap?: {
        type: string                   // missing_documentation | incomplete_knowledge_base
        description: string
        evidence: string
      }
      capability_gap?: {
        type: string                   // missing_tool | missing_integration | unsupported_action
        description: string
        evidence: string
      }
    }
  }
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
  error_message?: string
  started_at: string
  completed_at?: string
  messages: Message[]
}

// AI Insights types
export interface ImprovementSuggestion {
  id: number
  simulation_id: number
  category: string
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  evidence: {
    conversation_ids?: number[]
    affected_personas?: string[]
    metrics?: Record<string, any>
    pattern?: string
  }
  code_recommendation?: {
    title: string
    description: string
    file_changes: Array<{
      file: string
      old_content: string
      new_content: string
      diff: string
    }>
    priority: string
    status?: string
    github_issue_url?: string
    generated_at?: string
  }
  knowledge_recommendation?: {
    title: string
    doc_type: 'new_page' | 'update_existing' | 'add_example'
    target_doc: string
    existing_doc_coverage: string
    glean_sources: string[]
    recommended_content: string
    rationale: string
    priority: 'high' | 'medium' | 'low'
    generated_at?: string
    status?: string
  }
  created_at: string
}
