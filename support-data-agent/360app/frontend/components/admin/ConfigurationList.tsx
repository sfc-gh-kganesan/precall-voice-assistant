'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAdminStore } from '@/stores/adminStore'
import { adminApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber } from '@/lib/utils'

export function ConfigurationList() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { setCurrentStep, reset } = useAdminStore()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Fetch all configurations
  const { data: configurations, isLoading } = useQuery({
    queryKey: ['configurations'],
    queryFn: () => adminApi.getAllConfigurations(),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (configId: string) => adminApi.deleteConfiguration(configId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configurations'] })
      setDeletingId(null)
    },
  })

  const handleNewConfiguration = () => {
    reset()
    setCurrentStep(1)
  }

  const handleViewConfiguration = (configId: string) => {
    router.push(`/admin/configuration/${configId}`)
  }

  const handleDeleteConfiguration = (configId: string) => {
    if (confirm('Are you sure you want to delete this configuration?')) {
      setDeletingId(configId)
      deleteMutation.mutate(configId)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold">Configurations</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your knowledge base configurations
          </p>
        </div>
        <button
          onClick={handleNewConfiguration}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Configuration
        </button>
      </div>

      {/* Configurations List */}
      {!configurations || configurations.length === 0 ? (
        <div className="text-center py-12">
          <svg className="w-16 h-16 mx-auto text-muted-foreground/50 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="text-lg font-medium mb-2">No configurations yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create your first configuration to start analyzing support data
          </p>
          <button
            onClick={handleNewConfiguration}
            className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
          >
            Create Configuration
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {configurations.map((config) => {
            const isComplete = config.status.baseTable.created &&
                              config.status.topicMetrics.created &&
                              config.status.productMetrics.created &&
                              config.status.kpiSummary.created

            return (
              <div
                key={config.configId}
                className="border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-medium">{config.name}</h3>
                      <span
                        className={`
                          px-2 py-0.5 rounded text-xs font-medium
                          ${isComplete
                            ? 'bg-success/20 text-success'
                            : 'bg-warning/20 text-warning'
                          }
                        `}
                      >
                        {isComplete ? 'Complete' : 'Incomplete'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                      <div>
                        <span className="text-muted-foreground">Database: </span>
                        <span className="font-medium">{config.database}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Schema: </span>
                        <span className="font-medium">{config.schema}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Tables: </span>
                        <span className="font-medium">{config.tables.join(', ')}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Created: </span>
                        <span className="font-medium">
                          {new Date(config.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {/* Status Indicators */}
                    <div className="flex items-center gap-4 text-xs">
                      <div className={`flex items-center gap-1 ${config.status.baseTable.created ? 'text-success' : 'text-muted-foreground'}`}>
                        {config.status.baseTable.created ? '✓' : '○'} Base Table
                        {config.status.baseTable.created && ` (${formatNumber(config.status.baseTable.rowCount)} rows)`}
                      </div>
                      <div className={`flex items-center gap-1 ${config.status.topicMetrics.created ? 'text-success' : 'text-muted-foreground'}`}>
                        {config.status.topicMetrics.created ? '✓' : '○'} Topic Metrics
                      </div>
                      <div className={`flex items-center gap-1 ${config.status.productMetrics.created ? 'text-success' : 'text-muted-foreground'}`}>
                        {config.status.productMetrics.created ? '✓' : '○'} Product Metrics
                      </div>
                      <div className={`flex items-center gap-1 ${config.status.kpiSummary.created ? 'text-success' : 'text-muted-foreground'}`}>
                        {config.status.kpiSummary.created ? '✓' : '○'} KPIs
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => handleViewConfiguration(config.configId)}
                      className="px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted transition-colors"
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => handleDeleteConfiguration(config.configId)}
                      disabled={deletingId === config.configId}
                      className="px-3 py-1.5 text-sm text-error border border-error/30 rounded-md hover:bg-error/10 transition-colors disabled:opacity-50"
                    >
                      {deletingId === config.configId ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
