'use client'

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useAdminStore } from '@/stores/adminStore'
import { adminApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber } from '@/lib/utils'

export function FieldGeneration() {
  const {
    selectedDatabase,
    selectedSchema,
    selectedTables,
    fieldMappings,
    generationJobId,
    setGenerationJobId,
    setCurrentStep,
  } = useAdminStore()

  const [isGenerating, setIsGenerating] = useState(false)

  // Start generation mutation
  const startGeneration = useMutation({
    mutationFn: () => adminApi.startGeneration({
      database: selectedDatabase!,
      schema: selectedSchema!,
      tables: selectedTables,
      mappings: fieldMappings,
    }),
    onSuccess: (data) => {
      setGenerationJobId(data.jobId)
      setIsGenerating(true)
    },
  })

  // Poll job status with adaptive interval
  const { data: jobStatus } = useQuery({
    queryKey: ['job-status', generationJobId],
    queryFn: () => adminApi.getJobStatus(generationJobId!),
    enabled: !!generationJobId && isGenerating,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed') {
        setIsGenerating(false)
        return false
      }
      return status === 'processing' ? 1000 : 2000
    },
  })

  const fieldsToGenerate = fieldMappings.filter(m => m.sourceType === 'generated')

  const handleStartGeneration = () => {
    startGeneration.mutate()
  }

  const handleNext = () => {
    setCurrentStep(4)
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-6">Field Generation</h2>

      {/* Summary */}
      <div className="mb-6 bg-muted rounded-lg p-4">
        <h3 className="font-medium mb-2">Configuration Summary</h3>
        <div className="space-y-1 text-sm">
          <div>Database: <span className="font-medium">{selectedDatabase}</span></div>
          <div>Schema: <span className="font-medium">{selectedSchema}</span></div>
          <div>Tables: <span className="font-medium">{selectedTables.join(', ')}</span></div>
          <div>Fields to generate: <span className="font-medium">{fieldsToGenerate.length}</span></div>
        </div>
      </div>

      {/* AI Generation Configuration Details */}
      {fieldsToGenerate.length > 0 && (
        <div className="mb-6">
          <h3 className="font-medium mb-3">AI Generation Configuration</h3>
          <div className="space-y-3">
            {fieldsToGenerate.map((mapping, idx) => (
              <div key={idx} className="border border-border rounded-lg p-4 bg-background">
                <div className="flex items-start justify-between mb-2">
                  <div className="font-medium text-sm">{mapping.targetField}</div>
                  <div className="text-xs text-muted-foreground px-2 py-1 bg-primary/10 text-primary rounded">
                    AI Generated
                  </div>
                </div>
                {mapping.sourceColumns && mapping.sourceColumns.length > 0 && (
                  <div className="text-xs text-muted-foreground mb-1">
                    <span className="font-medium">Context columns:</span> {mapping.sourceColumns.join(', ')}
                  </div>
                )}
                {mapping.aiInstruction && (
                  <div className="text-xs text-muted-foreground">
                    <span className="font-medium">Instruction:</span> {mapping.aiInstruction}
                  </div>
                )}
                {mapping.sourceColumns && mapping.sourceColumns.length > 0 && mapping.aiInstruction && (
                  <div className="mt-2 text-xs bg-muted rounded p-2">
                    <span className="font-medium">Full prompt:</span> Use {mapping.sourceColumns.join(', ')} to: {mapping.aiInstruction}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generation Status */}
      {fieldsToGenerate.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-muted-foreground">
            No AI fields configured. You can proceed to save your configuration.
          </p>
        </div>
      ) : !generationJobId ? (
        <div className="text-center py-8">
          <p className="mb-4">Ready to generate {fieldsToGenerate.length} fields using AI.</p>
          <button
            onClick={handleStartGeneration}
            disabled={startGeneration.isPending}
            className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {startGeneration.isPending ? 'Starting...' : 'Start Generation'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Job Status */}
          <div className="border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">Generation Status</span>
              <span className={`
                px-2 py-1 rounded text-xs font-medium
                ${jobStatus?.status === 'completed' ? 'bg-success/20 text-success' : ''}
                ${jobStatus?.status === 'processing' ? 'bg-primary/20 text-primary' : ''}
                ${jobStatus?.status === 'failed' ? 'bg-error/20 text-error' : ''}
              `}>
                {jobStatus?.status || 'Initializing'}
              </span>
            </div>

            {jobStatus?.progress !== undefined && (
              <div className="mb-2">
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${jobStatus.progress}%` }}
                  />
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {jobStatus.progress}% complete
                </div>
              </div>
            )}

            {jobStatus?.results && (
              <div className="text-sm space-y-1">
                <div>Processed: {formatNumber(jobStatus.results.processed)} records</div>
                {jobStatus.results.errors > 0 && (
                  <div className="text-error">Errors: {jobStatus.results.errors}</div>
                )}
              </div>
            )}

            {isGenerating && <LoadingSpinner size="sm" className="mt-4" />}
          </div>

          {/* Estimated Time */}
          {jobStatus?.estimatedTime && jobStatus.estimatedTime > 0 && (
            <div className="text-sm text-muted-foreground">
              Estimated time remaining: {jobStatus.estimatedTime} seconds
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-8">
        <button
          onClick={() => setCurrentStep(2)}
          className="px-6 py-2 border border-border rounded-md hover:bg-muted"
        >
          Back
        </button>
        <button
          onClick={handleNext}
          disabled={fieldsToGenerate.length > 0 && (!jobStatus || jobStatus.status !== 'completed')}
          className="
            bg-primary text-primary-foreground px-6 py-2 rounded-md
            hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          Next: Save Configuration
        </button>
      </div>
    </div>
  )
}
