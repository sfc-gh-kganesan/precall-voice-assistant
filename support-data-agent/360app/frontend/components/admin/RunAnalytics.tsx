'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useAdminStore } from '@/stores/adminStore'
import { adminApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber } from '@/lib/utils'

export function RunAnalytics() {
  const router = useRouter()
  const {
    configurationId,
    configurationName,
    selectedDatabase,
    selectedSchema,
    outputTableName,
    analyticsJobId,
    setAnalyticsJobId,
  } = useAdminStore()

  const [isRunning, setIsRunning] = useState(false)

  // Fetch configuration data to get actual row count
  const { data: configData } = useQuery({
    queryKey: ['configuration', configurationId],
    queryFn: () => adminApi.getConfiguration(configurationId!),
    enabled: !!configurationId,
  })

  // Start analytics mutation
  const startAnalytics = useMutation({
    mutationFn: () => adminApi.runAnalytics(configurationId!),
    onSuccess: (data) => {
      setAnalyticsJobId(data.analyticsJobId)
      setIsRunning(true)
    },
  })

  // Poll job status
  const { data: jobStatus } = useQuery({
    queryKey: ['analytics-job-status', analyticsJobId],
    queryFn: () => adminApi.getJobStatus(analyticsJobId!),
    enabled: !!analyticsJobId && isRunning,
    refetchInterval: (query) => {
      if (query.state.data?.status === 'completed' || query.state.data?.status === 'failed') {
        setIsRunning(false)
        return false
      }
      return 1000 // Poll every second
    },
  })

  const handleStartAnalytics = () => {
    startAnalytics.mutate()
  }

  const handleViewConfiguration = () => {
    router.push(`/admin/configuration/${configurationId}`)
  }

  const analyticsComplete = jobStatus?.status === 'completed'

  // Calculate analytics step progress
  const getAnalyticsStep = () => {
    const progress = jobStatus?.progress || 0
    if (progress < 33) return { step: 1, label: 'Computing topic metrics...' }
    if (progress < 66) return { step: 2, label: 'Computing product metrics...' }
    if (progress < 100) return { step: 3, label: 'Computing KPIs...' }
    return { step: 4, label: 'Analytics complete!' }
  }

  const currentStep = getAnalyticsStep()

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-2">Run Analytics</h2>
      <div className="text-sm text-muted-foreground mb-6">
        {configurationName || `${selectedDatabase}.${selectedSchema} Configuration`}
      </div>

      {/* Base Table Summary */}
      <div className="mb-6 bg-muted rounded-lg p-4">
        <h3 className="font-medium mb-3">Base Table Created</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Output Table</span>
            <span className="font-medium">{selectedDatabase}.{selectedSchema}.{outputTableName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <span className="text-success font-medium">✓ Created</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Rows</span>
            <span className="font-medium">{formatNumber(configData?.status.baseTable.rowCount || 0)}</span>
          </div>
        </div>
      </div>

      {/* Analytics Processing */}
      {!analyticsJobId ? (
        <div className="text-center py-8">
          <p className="mb-4">Ready to process analytics aggregations and generate insights.</p>
          <button
            onClick={handleStartAnalytics}
            disabled={startAnalytics.isPending}
            className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {startAnalytics.isPending ? 'Starting...' : 'Run Analytics'}
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Progress Steps */}
          <div className="space-y-3">
            <h3 className="font-medium text-sm mb-4">Analytics Processing</h3>

            {/* Step 1: Topic Metrics */}
            <div className={`flex items-start space-x-3 ${currentStep.step > 1 ? 'opacity-50' : ''}`}>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                currentStep.step > 1 ? 'bg-success text-success-foreground' :
                currentStep.step === 1 ? 'bg-primary text-primary-foreground' :
                'bg-muted text-muted-foreground'
              }`}>
                {currentStep.step > 1 ? '✓' : '1'}
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Topic Metrics</div>
                <div className="text-xs text-muted-foreground">Aggregating support metrics by topic</div>
              </div>
              {currentStep.step === 1 && <LoadingSpinner size="sm" />}
            </div>

            {/* Step 2: Product Metrics */}
            <div className={`flex items-start space-x-3 ${currentStep.step > 2 ? 'opacity-50' : ''}`}>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                currentStep.step > 2 ? 'bg-success text-success-foreground' :
                currentStep.step === 2 ? 'bg-primary text-primary-foreground' :
                'bg-muted text-muted-foreground'
              }`}>
                {currentStep.step > 2 ? '✓' : '2'}
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Product Metrics</div>
                <div className="text-xs text-muted-foreground">Aggregating support metrics by product</div>
              </div>
              {currentStep.step === 2 && <LoadingSpinner size="sm" />}
            </div>

            {/* Step 3: KPI Summary */}
            <div className={`flex items-start space-x-3 ${currentStep.step > 3 ? 'opacity-50' : ''}`}>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                currentStep.step > 3 ? 'bg-success text-success-foreground' :
                currentStep.step === 3 ? 'bg-primary text-primary-foreground' :
                'bg-muted text-muted-foreground'
              }`}>
                {currentStep.step > 3 ? '✓' : '3'}
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">KPI Summary</div>
                <div className="text-xs text-muted-foreground">Computing pre-aggregated KPIs</div>
              </div>
              {currentStep.step === 3 && <LoadingSpinner size="sm" />}
            </div>
          </div>

          {/* Progress Bar */}
          {jobStatus && !analyticsComplete && (
            <div className="space-y-2">
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${jobStatus.progress}%` }}
                />
              </div>
              <div className="text-sm text-muted-foreground text-center">
                {jobStatus.progress}% complete
              </div>
              {(jobStatus.estimatedTime ?? 0) > 0 && (
                <div className="text-xs text-muted-foreground text-center">
                  Estimated time remaining: {jobStatus.estimatedTime} seconds
                </div>
              )}
            </div>
          )}

          {/* Success Message */}
          {analyticsComplete && (
            <div className="bg-success/20 border border-success/50 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-success mt-0.5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="font-medium text-success">Analytics Complete!</h4>
                  <p className="text-sm mt-1">All aggregation tables have been created successfully.</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-8">
        <button
          onClick={() => router.push('/admin')}
          disabled={isRunning && !analyticsComplete}
          className="px-6 py-2 border border-border rounded-md hover:bg-muted disabled:opacity-50"
        >
          Back to Admin
        </button>
        <button
          onClick={handleViewConfiguration}
          disabled={!analyticsComplete}
          className="
            bg-primary text-primary-foreground px-6 py-2 rounded-md
            hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          View Configuration
        </button>
      </div>
    </div>
  )
}
