'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ConfigurationHeader } from '@/components/admin/ConfigurationHeader'
import { ConfigurationDetailsCard } from '@/components/admin/ConfigurationDetailsCard'
import { SchemaVisualization } from '@/components/admin/SchemaVisualization'
import { EnhancedPreviewTable } from '@/components/admin/EnhancedPreviewTable'

export default function ConfigurationDashboardPage() {
  const params = useParams()
  const configId = params.id as string

  const [activeTab, setActiveTab] = useState<'enriched' | 'topics' | 'products'>('enriched')

  // Fetch configuration details
  const { data: configuration, isLoading } = useQuery({
    queryKey: ['configuration', configId],
    queryFn: () => adminApi.getConfiguration(configId),
  })

  // Fetch preview data based on active tab
  const { data: previewData } = useQuery({
    queryKey: ['preview', configuration?.config.database, configuration?.config.schema, activeTab, configId],
    queryFn: () => {
      if (!configuration) return null

      const { database, schema, outputTable } = configuration.config
      let tableName = outputTable

      if (activeTab === 'topics') tableName = `${outputTable}_TOPICS`
      if (activeTab === 'products') tableName = `${outputTable}_PRODUCTS`

      return adminApi.getTablePreview(database, schema, tableName)
    },
    enabled: !!configuration,
  })

  if (isLoading || !configuration) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  const { config, status } = configuration

  const getTableDisplayName = () => {
    if (activeTab === 'enriched') return config.outputTable
    if (activeTab === 'topics') return 'Topic Metrics'
    return 'Product Metrics'
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <ConfigurationHeader configName={config.name} />

      <main className="container mx-auto px-4 py-4 space-y-4">
        {/* Configuration Details */}
        <ConfigurationDetailsCard
          configName={config.name}
          database={config.database}
          schema={config.schema}
          sourceTables={config.tables}
          outputTable={config.outputTable}
          baseTableStatus={status.baseTable}
          topicMetricsStatus={status.topicMetrics}
          productMetricsStatus={status.productMetrics}
          createdAt={config.createdAt}
          isActive={true}
        />

        {/* Schema Visualization */}
        <SchemaVisualization
          sourceName={`${config.database}.${config.schema}`}
          sourceTables={config.tables}
          outputTable={config.outputTable}
          baseTableStatus={status.baseTable}
          topicMetricsStatus={status.topicMetrics}
          productMetricsStatus={status.productMetrics}
          activeTable={activeTab}
          onTableClick={setActiveTab}
        />

        {/* Data Preview */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="mb-6">
            <h2 className="text-lg font-semibold">Data Preview: {getTableDisplayName()}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Explore and search through your data
            </p>
          </div>

          <EnhancedPreviewTable
            columns={previewData?.columns || []}
            rows={previewData?.rows || []}
            isLoading={!previewData}
            tableName={getTableDisplayName()}
          />
        </div>
      </main>
    </div>
  )
}
