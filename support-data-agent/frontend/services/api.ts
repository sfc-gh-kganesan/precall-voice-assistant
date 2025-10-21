import { Filters, KPIMetric, ProductMetrics, SupportTicket, TableInfo, GenerationJob, FieldMapping, TopicMetrics, PerformanceData } from '@/types'
import { apiRequest, buildQueryParams } from '@/lib/api-error-handler'
import { API_CONFIG } from '@/lib/constants'

const API_BASE = API_CONFIG.BASE_URL

function buildFiltersQueryParams(filters: Filters): string {
  return buildQueryParams({
    period: filters.period,
    startDate: filters.startDate,
    endDate: filters.endDate,
    products: filters.products,
    topics: filters.topics,
    categories: filters.categories,
  })
}

interface KPIResponse {
  avgCases: KPIMetric
  avgCaseLife: KPIMetric
  resolutionRate: KPIMetric
  firstResponseTime: KPIMetric
}

export const dashboardApi = {
  async getKPIs(filters: Filters): Promise<KPIResponse> {
    const queryParams = buildFiltersQueryParams(filters)
    const data = await apiRequest<KPIResponse>(`${API_BASE}/api/v1/dashboard/kpis?${queryParams}`)

    return {
      avgCases: data.avgCases,
      avgCaseLife: data.avgCaseLife,
      resolutionRate: data.resolutionRate,
      firstResponseTime: data.firstResponseTime,
    }
  },

  async getProductMetrics(filters: Filters): Promise<ProductMetrics[]> {
    const queryParams = buildFiltersQueryParams(filters)
    return await apiRequest<ProductMetrics[]>(`${API_BASE}/api/v1/dashboard/products?${queryParams}`)
  },

  async getTopicMetrics(filters: Filters): Promise<TopicMetrics[]> {
    const queryParams = buildFiltersQueryParams(filters)
    return await apiRequest<TopicMetrics[]>(`${API_BASE}/api/v1/dashboard/topics?${queryParams}`)
  },

  async getProductPerformance(filters: Filters): Promise<PerformanceData> {
    const queryParams = buildFiltersQueryParams(filters)
    return await apiRequest<PerformanceData>(`${API_BASE}/api/v1/dashboard/products/performance?${queryParams}`)
  },

  async getTopicPerformance(filters: Filters): Promise<PerformanceData> {
    const queryParams = buildFiltersQueryParams(filters)
    return await apiRequest<PerformanceData>(`${API_BASE}/api/v1/dashboard/topics/performance?${queryParams}`)
  },
}

export const adminApi = {
  async getDatabases(): Promise<string[]> {
    return await apiRequest<string[]>(`${API_BASE}/api/v1/admin/databases`)
  },

  async getSchemas(database: string): Promise<string[]> {
    return await apiRequest<string[]>(`${API_BASE}/api/v1/admin/schemas?database=${encodeURIComponent(database)}`)
  },

  async getTables(database: string, schema: string): Promise<TableInfo[]> {
    return await apiRequest<TableInfo[]>(`${API_BASE}/api/v1/admin/tables?database=${encodeURIComponent(database)}&schema=${encodeURIComponent(schema)}`)
  },

  async analyzeTable(database: string, schema: string, table: string): Promise<string[]> {
    return await apiRequest<string[]>(`${API_BASE}/api/v1/admin/tables/analyze?database=${encodeURIComponent(database)}&schema=${encodeURIComponent(schema)}&table=${encodeURIComponent(table)}`)
  },

  async getTablePreview(database: string, schema: string, table: string): Promise<{
    columns: string[]
    rows: Record<string, unknown>[]
    sampleCount: number
  }> {
    return await apiRequest<{
      columns: string[]
      rows: Record<string, unknown>[]
      sampleCount: number
    }>(`${API_BASE}/api/v1/admin/tables/preview?database=${encodeURIComponent(database)}&schema=${encodeURIComponent(schema)}&table=${encodeURIComponent(table)}`)
  },

  async startGeneration(config: {
    database: string
    schema: string
    tables: string[]
    mappings: FieldMapping[]
  }): Promise<{ jobId: string }> {
    return await apiRequest<{ jobId: string }>(`${API_BASE}/api/v1/admin/generate`, {
      method: 'POST',
      body: JSON.stringify({
        configId: `${config.database}_${config.schema}_${Date.now()}`,
        jobType: 'enrichment'
      })
    })
  },

  async getJobStatus(jobId: string): Promise<GenerationJob> {
    return await apiRequest<GenerationJob>(`${API_BASE}/api/v1/admin/jobs/${jobId}`)
  },

  async saveConfiguration(config: {
    name: string
    database: string
    schema: string
    tables: string[]
    mappings: FieldMapping[]
    outputTable: string
  }): Promise<{ configId: string }> {
    return await apiRequest<{ configId: string }>(`${API_BASE}/api/v1/admin/configurations`, {
      method: 'POST',
      body: JSON.stringify(config)
    })
  },

  async runAnalytics(configId: string): Promise<{ analyticsJobId: string }> {
    return await apiRequest<{ analyticsJobId: string }>(`${API_BASE}/api/v1/admin/analytics/${configId}`, {
      method: 'POST',
    })
  },

  async getAllConfigurations(): Promise<Array<{
    configId: string
    name: string
    database: string
    schema: string
    tables: string[]
    createdAt: string
    status: {
      baseTable: { created: boolean; rowCount: number }
      topicMetrics: { created: boolean; rowCount: number }
      productMetrics: { created: boolean; rowCount: number }
      kpiSummary: { created: boolean }
    }
  }>> {
    return await apiRequest<Array<{
      configId: string
      name: string
      database: string
      schema: string
      tables: string[]
      createdAt: string
      status: {
        baseTable: { created: boolean; rowCount: number }
        topicMetrics: { created: boolean; rowCount: number }
        productMetrics: { created: boolean; rowCount: number }
        kpiSummary: { created: boolean }
      }
    }>>(`${API_BASE}/api/v1/admin/configurations`)
  },

  async deleteConfiguration(configId: string): Promise<{ success: boolean }> {
    return await apiRequest<{ success: boolean }>(`${API_BASE}/api/v1/admin/configurations/${configId}`, {
      method: 'DELETE',
    })
  },

  async getConfiguration(configId: string): Promise<{
    config: {
      name: string
      database: string
      schema: string
      tables: string[]
      mappings: FieldMapping[]
      outputTable: string
      createdAt: string
    }
    status: {
      baseTable: { created: boolean; rowCount: number }
      topicMetrics: { created: boolean; rowCount: number }
      productMetrics: { created: boolean; rowCount: number }
      kpiSummary: { created: boolean }
    }
  }> {
    return await apiRequest(`${API_BASE}/api/v1/admin/configurations/${configId}`)
  },
}

export const chatApi = {
  async sendMessage(message: string, sessionId: string): Promise<{
    response: string
    suggestedQueries?: string[]
  }> {
    return await apiRequest<{
      response: string
      suggestedQueries?: string[]
    }>(`${API_BASE}/api/v1/chat/messages`, {
      method: 'POST',
      body: JSON.stringify({ message, sessionId }),
    })
  },
}

export const ticketsApi = {
  async getTickets(filters: {
    page: number
    pageSize: number
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
    product?: string
  } & Partial<Filters>): Promise<{
    tickets: SupportTicket[]
    total: number
    page: number
    pageSize: number
  }> {
    const params = new URLSearchParams()
    params.append('page', filters.page.toString())
    params.append('pageSize', filters.pageSize.toString())

    if (filters.sortBy) {
      params.append('sortBy', filters.sortBy)
    }
    if (filters.sortOrder) {
      params.append('sortOrder', filters.sortOrder)
    }
    if (filters.product) {
      params.append('product', filters.product)
    }

    return await apiRequest<{
      tickets: SupportTicket[]
      total: number
      page: number
      pageSize: number
    }>(`${API_BASE}/api/v1/tickets?${params.toString()}`)
  },
}
