import { Filters, KPIMetric, ProductMetrics, SupportTicket, TableInfo, GenerationJob, FieldMapping, TopicMetrics, PerformanceData, CategoryMetrics, SubcategoryMetrics, BenchmarkData, ProductSearchResult } from '@/types'
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

    async getCategoryMetrics(filters: Filters): Promise<CategoryMetrics[]> {
        const queryParams = buildFiltersQueryParams(filters)
        return await apiRequest<CategoryMetrics[]>(`${API_BASE}/api/v1/dashboard/categories?${queryParams}`)
    },

    async getSubcategoryMetrics(category: string, filters: Filters): Promise<SubcategoryMetrics[]> {
        const queryParams = buildFiltersQueryParams(filters)
        return await apiRequest<SubcategoryMetrics[]>(`${API_BASE}/api/v1/dashboard/categories/${encodeURIComponent(category)}/subcategories?${queryParams}`)
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
        outputTable?: string
    }): Promise<{ jobId: string; configId: string }> {
        // First, save the configuration to get a real configId
        const configName = `${config.database}.${config.schema} Auto-Generated Config`
        const outputTable = config.outputTable || `${config.tables[0]}_ENRICHED`

        const saveResult = await apiRequest<{ configId: string }>(`${API_BASE}/api/v1/admin/configurations`, {
            method: 'POST',
            body: JSON.stringify({
                name: configName,
                database: config.database,
                schema: config.schema,
                tables: config.tables,
                mappings: config.mappings,
                outputTable: outputTable
            })
        })

        // Now start the generation job with the real configId
        const generateResult = await apiRequest<{ jobId: string }>(`${API_BASE}/api/v1/admin/generate`, {
            method: 'POST',
            body: JSON.stringify({
                configId: saveResult.configId,
                jobType: 'enrichment'
            })
        })

        return {
            jobId: generateResult.jobId,
            configId: saveResult.configId
        }
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
    /**
     * Stream chat messages from the backend with conversation history support
     * @param message - The user's message
     * @param messageHistory - Previous conversation messages for context (limited to last 5 by backend)
     * @param onChunk - Callback for each streamed message chunk
     * @returns Updated message history after the conversation turn
     */
    async streamMessage(
        message: string,
        messageHistory: Array<{ role: string; content: string; timestamp: string }> | null,
        onChunk: (data: {
            role: 'user' | 'model' | 'tool_status' | 'history_update'
            timestamp: string
            content?: string
            event_type?: string
            tool_name?: string
            status?: 'running' | 'completed'
            messages?: string
        }) => void
    ): Promise<Array<{ role: string; content: string; timestamp: string }>> {
        // Backend expects FormData with 'message' and optional 'message_history' fields
        const formData = new FormData()
        formData.append('message', message)

        // Send message history if available
        if (messageHistory && messageHistory.length > 0) {
            formData.append('message_history', JSON.stringify(messageHistory))
        }

        const response = await fetch(`${API_BASE}/api/v1/chat/messages`, {
            method: 'POST',
            body: formData,
        })

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`)
        }

        // Read the streaming response
        const reader = response.body?.getReader()
        if (!reader) {
            throw new Error('No response body')
        }

        const decoder = new TextDecoder()
        let buffer = ''
        let updatedHistory: Array<{ role: string; content: string; timestamp: string }> = []

        try {
            while (true) {
                const { done, value } = await reader.read()

                if (done) break

                // Decode the chunk and add to buffer
                buffer += decoder.decode(value, { stream: true })

                // Process complete lines (newline-delimited JSON)
                const lines = buffer.split('\n')
                // Keep the last incomplete line in buffer
                buffer = lines.pop() || ''

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const data = JSON.parse(line)

                            // Capture history update event
                            if (data.role === 'history_update' && data.messages) {
                                updatedHistory = JSON.parse(data.messages)
                            }

                            onChunk(data)
                        } catch (e) {
                            console.error('Failed to parse JSON line:', line, e)
                        }
                    }
                }
            }

            // Return the updated message history
            return updatedHistory
        } finally {
            reader.releaseLock()
        }
    },
}

export const ticketsApi = {
    async getTickets(filters: {
        page: number
        pageSize: number
        sortBy?: string
        sortOrder?: 'asc' | 'desc'
        product?: string
        severity?: string
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
        if (filters.severity) {
            params.append('severity', filters.severity)
        }

        return await apiRequest<{
            tickets: SupportTicket[]
            total: number
            page: number
            pageSize: number
        }>(`${API_BASE}/api/v1/tickets?${params.toString()}`)
    },
}

export const productsApi = {
    async getBenchmarks(filters: Filters & {
        category?: string
        subcategory?: string
        productId?: string
    }): Promise<BenchmarkData> {
        const queryParams = buildQueryParams({
            period: filters.period,
            startDate: filters.startDate,
            endDate: filters.endDate,
            category: filters.category,
            subcategory: filters.subcategory,
            productId: filters.productId,
        })
        return await apiRequest<BenchmarkData>(`${API_BASE}/api/v1/products/benchmarks?${queryParams}`)
    },

    async searchProducts(query: string, category?: string, subcategory?: string): Promise<ProductSearchResult[]> {
        const queryParams = buildQueryParams({
            query,
            category,
            subcategory,
        })
        return await apiRequest<ProductSearchResult[]>(`${API_BASE}/api/v1/products/search?${queryParams}`)
    },

    async getBenchmarkContext(productId: string, period: string = 'week'): Promise<any> {
        const queryParams = buildQueryParams({ period })
        return await apiRequest<any>(`${API_BASE}/api/v1/products/${productId}/benchmark-context?${queryParams}`)
    },
}

export const usageApi = {
    async getCreditsTimeline(params?: {
        date_range?: string
        certified_organization_type?: string
        certified_deployment?: string
        certified_salesforce_account_id?: string
        certified_salesforce_account_name?: string
        include_coda?: boolean
    }): Promise<import('@/types').UsageTrendPoint[]> {
        const queryParams = buildQueryParams(params || {})
        return await apiRequest<import('@/types').UsageTrendPoint[]>(`${API_BASE}/api/v1/usage/credits-timeline?${queryParams}`)
    },

    async getTopAccounts(params?: {
        certified_organization_type?: string
        certified_deployment?: string
        certified_salesforce_account_name?: string
    }): Promise<import('@/types').TopAccount[]> {
        const queryParams = buildQueryParams(params || {})
        return await apiRequest<import('@/types').TopAccount[]>(`${API_BASE}/api/v1/usage/top-accounts?${queryParams}`)
    },

    async getBiggestMovers(params?: {
        period?: string
        certified_organization_type?: string
        certified_deployment?: string
        certified_salesforce_account_id?: string
        certified_salesforce_account_name?: string
        include_coda?: boolean
    }): Promise<import('@/types').BiggestMoversResponse> {
        const queryParams = buildQueryParams(params || {})
        return await apiRequest<import('@/types').BiggestMoversResponse>(`${API_BASE}/api/v1/usage/biggest-movers?${queryParams}`)
    },

    async getMetricsSummary(): Promise<import('@/types').UsageMetrics> {
        return await apiRequest<import('@/types').UsageMetrics>(`${API_BASE}/api/v1/usage/metrics-summary`)
    },

    async getCaseCounts(params: {
        product_name: string
        days?: number
    }): Promise<Record<string, number>> {
        const queryParams = buildQueryParams(params)
        return await apiRequest<Record<string, number>>(`${API_BASE}/api/v1/usage/case-counts?${queryParams}`)
    },
}
