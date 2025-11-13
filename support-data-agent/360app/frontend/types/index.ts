// Support Ticket Types (Aligned with Snowflake Case Structure)
export interface SupportTicket {
  id: string
  case_number: string

  created_at: string
  updated_at: string
  closed_at: string | null
  last_modified_at: string

  status: 'New' | 'In Progress' | 'Awaiting Customer' | 'Solution Provided' | 'Closed' | 'Escalated'
  severity: 'Severity-1: Critical outage' | 'Severity-2: High impact, but business is operational' | 'Severity-3: Medium to low impact to business/operations' | 'Severity-4: Low impact to business/operations'
  initial_severity: string
  peak_severity: string

  subject: string
  description: string

  account_id: string
  account_name: string
  is_priority_support: boolean

  total_comments: number
  has_jira_issues: boolean
  has_escalations: boolean
  has_collaborations: boolean

  generated_topic?: string
  generated_product_category?: string
  generated_product?: string
  generated_feature?: string
  sentiment?: 'positive' | 'negative' | 'neutral'

  resolution_time_hours: number | null
  sla_violated: boolean
}

// Raw Case Structure (mirrors CSV structure)
export interface RawSupportCase {
  CASE_ID: string
  CASE_NUMBER: string
  PRIME_CASE_STRUCTURED: string
  CHRONICLE_XML: string
  CHRONICLE_TIMING_ISSUES_XML: string
  LAST_MODIFIED_AT: string
  DESCRIPTION: string
  SUBJECT: string
}

// Parsed PRIME_CASE_STRUCTURED structure
export interface PrimeCaseStructured {
  content: {
    initial_post: {
      author_type: 'Customer' | 'Support Engineer' | 'System'
      content: {
        description: string
        subject: string
      }
      timestamp: string
    }
    timeline: TimelineEvent[]
  }
  metadata: CaseMetadata
}

// Timeline Event (comment, update, etc.)
export interface TimelineEvent {
  all_comment_rank: number
  comment_id: string
  content: string
  timestamp: string
  day_of_week: string
  event_id: string
  type: 'customer_comment' | 'sf_response' | 'api_metadata' | 'system_update' | 'status_change'
  visibility: 'Internal' | 'External'
  author_type?: string
}

// Case Metadata (from PRIME_CASE_STRUCTURED)
export interface CaseMetadata {
  case: {
    sfdc_case_id: string
    sfdc_account_id: string
    case_number: string
    account_name: string
    created_at: string
    closed_at: string | null
    current_status: string
    current_severity: string
    initial_severity: string
    peak_severity: string
    total_comments: number
    is_priority_support_entitlement: boolean
    is_ascii: boolean
    has_japanese: boolean
  }
  jira_issues: JiraIssue[]
  collaborations: Collaboration[]
  escalations: Escalation[]
  initial_response_sla: SLAInfo
  quality_signals: QualitySignals
}

// JIRA Issue Link
export interface JiraIssue {
  jira_issue_id: string
  jira_issue_key: string
  jira_issue_summary: string
  linked_at: string
}

// Collaboration Record
export interface Collaboration {
  collaboration_id: string
  collaboration_name: string
  cleaned_content: string
  start_timestamp: string
  end_timestamp: string
}

// Escalation Record
export interface Escalation {
  escalation_id: string
  escalation_type: string
  escalated_at: string
  resolved_at: string | null
  reason: string
}

// SLA Information
export interface SLAInfo {
  sla_start: string
  sla_target: string
  sla_completed: string | null
  target_hours: number
  business_hours: number
  clock_hours: number
  is_violated: boolean
}

// Quality Signals (delays, issues)
export interface QualitySignals {
  delay_periods: DelayPeriod[]
  summary: {
    total_delay_flags: number
  }
}

export interface DelayPeriod {
  type: 'follow_up_delay' | 'response_delay'
  period_start: string
  period_end: string
  last_sf_response: string
  flag_timestamp: string
  severity: string
  threshold_hours: number
  threshold_display: string
  actual_delay_hours: number
}

// KPI Metric Types
export interface KPIMetric {
  id: string
  name: string
  value: number
  previousValue: number
  change: number
  changePercentage: number
  changeType: 'increase' | 'decrease' | 'neutral'
  period: 'week' | 'month' | 'custom'
  comparisonPeriod: string
  unit?: string
  drillDownEnabled: boolean
}

// Product Metrics Types
export interface ProductMetrics {
  productId: string
  productName: string
  productCategory: string
  productSubcategory?: string
  parentProduct?: string
  metrics: {
    totalCases: KPIMetric
    avgCaseLife: KPIMetric
    resolutionRate: KPIMetric
  }
  topIssues: Issue[]
  trend: TrendData[]
  aiSummary?: string      // AI-generated customer sentiment summary (markdown formatted)
  rootCauses?: string     // AI-generated root cause analysis (markdown formatted)
}

export interface Issue {
  issue: string
  count: number
}

export interface TrendData {
  date: string
  value: number
}

// Topic Metrics Types
export interface TopicMetrics {
  topicId: string
  topicName: string
  totalCases: number
  change: number
  changePercentage: number
  changeType: 'increase' | 'decrease' | 'neutral'
  avgResolutionTime: number
  resolutionRate: number
  sentiment: {
    positive: number
    neutral: number
    negative: number
  }
  topProducts: Array<{
    product: string
    count: number
  }>
}

export interface PerformanceItem {
  id: string
  name: string
  category: string
  currentValue: number
  previousValue: number
  changeAbsolute: number
  changePercentage: number
}

export interface PerformanceData {
  caseVolume: {
    topPerformers: PerformanceItem[]
    bottomPerformers: PerformanceItem[]
  }
  resolutionTime: {
    topPerformers: PerformanceItem[]
    bottomPerformers: PerformanceItem[]
  }
  resolutionRate: {
    topPerformers: PerformanceItem[]
    bottomPerformers: PerformanceItem[]
  }
}

// Chat Types
export interface ChatMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: {
    queriedData?: string[]
    suggestedQueries?: string[]
  }
}

export interface ChatSession {
  id: string
  userId: string
  startTime: Date
  lastActivity: Date
  messages: ChatMessage[]
  context: Record<string, unknown>
}

// Configuration Types
export interface DataSourceConfig {
  id: string
  name: string
  database: string
  schema: string
  tables: string[]
  mappings: FieldMapping[]
  createdAt: Date
  updatedAt: Date
  status: 'draft' | 'active' | 'archived'
}

export interface FieldMapping {
  targetField: 'case_id' | 'case_number' | 'subject' | 'description' |
                'status' | 'severity' | 'priority' |
                'created_at' | 'closed_at' | 'last_modified_at' |
                'account_name' | 'account_id' |
                'timeline' | 'total_comments' |
                'jira_issues' | 'collaborations' | 'escalations' |
                'topic' | 'product' | 'feature'
  sourceType: 'column' | 'generated' | 'json_path'
  sourceColumn?: string
  sourceColumns?: string[]  // Multiple columns for AI context
  aiInstruction?: string    // User's one-line instruction for AI
  jsonPath?: string         // For extracting from JSON columns like PRIME_CASE_STRUCTURED
  generationType?: 'llm' | 'regex' | 'lookup'
  generationConfig?: Record<string, unknown>
}

// API Response Types
export interface ApiResponse<T> {
  data: T
  error?: string
  status: 'success' | 'error'
}

// Table Types
export interface TableInfo {
  name: string
  rowCount: number
}

// Job Types
export interface GenerationJob {
  jobId: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  estimatedTime?: number
  progress?: number
  results?: {
    processed: number
    errors: number
  }
}

// Filter Types
export interface Filters {
  period: 'week' | 'month' | 'custom'
  startDate?: Date
  endDate?: Date
  products?: string[]
  topics?: string[]
  categories?: string[]
}

// Category Metrics Types
export interface CategoryMetrics {
  categoryName: string
  totalCases: number
  casesChange: number
  casesChangePercentage: number
  changeType: 'increase' | 'decrease' | 'neutral'
  avgResolution: number
  resolutionRate: number
  productCount: number
}

// Subcategory Metrics Types
export interface SubcategoryMetrics {
  subcategoryName: string
  categoryName: string
  totalCases: number
  casesChange: number
  casesChangePercentage: number
  changeType: 'increase' | 'decrease' | 'neutral'
  avgResolution: number
  resolutionRate: number
}

// Product Benchmarking Types
export interface ProductBenchmark {
  id: string
  name: string
  cases?: number
  time?: number
  rate?: number
}

export interface BenchmarkData {
  scope: string
  average: {
    cases: number
    time: number
    rate: number
  }
  topPerformer: ProductBenchmark
  bottomPerformer: ProductBenchmark
  bestTimePerformer?: ProductBenchmark
  bestRatePerformer?: ProductBenchmark
  yourProduct?: ProductBenchmark
}

// Product Search Types
export interface ProductSearchResult {
  productId: string
  productName: string
  productCategory: string
  productSubcategory: string | null
}

// Product Filter State
export interface ProductFilters {
  categories: string[]
  subcategories: string[]
  searchQuery: string
  selectedProducts: string[]
}

// Usage Metrics Types
export interface UsageTrendPoint {
  ds: string
  credits: number
  rolling_avg_7d: number
}

export interface BiggestMover {
  salesforce_account_name: string
  salesforce_account_id: string
  l7_total_credits: number
  delta: number
  pct_change: number | null
  sales_engineer_email: string | null
  is_cap1: boolean | null
  agreement_type: string | null
}

export interface BiggestMoversResponse {
  gainers: BiggestMover[]
  decliners: BiggestMover[]
}

export interface TopAccount {
  ds: string
  salesforce_account_name: string
  salesforce_account_id: string
  total_indexed_rows: number
  total_active_serving_rows: number
  num_services: number
  snowflake_account_type: string
  acct_first_svc_creation_date: string
  sales_engineer_email: string | null
  accounts: any[]
}

export interface UsageMetrics {
  total_credits: number
  total_credits_change: number
  total_credits_change_pct: number
  active_accounts: number
  active_accounts_change: number
  seven_day_change_pct: number
}

export interface HighValueCustomer {
  salesforce_account_name: string
  salesforce_account_id: string
  total_active_serving_rows: number
  cases_last_30_days: number
}
