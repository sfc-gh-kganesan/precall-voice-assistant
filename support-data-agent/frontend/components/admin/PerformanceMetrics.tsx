'use client'

import { useQuery } from '@tanstack/react-query'
import { MetricCard } from './MetricCard'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

export function PerformanceMetrics() {
  const { data: kpis, error, isLoading } = useQuery({
    queryKey: ['performance-kpis'],
    queryFn: () => dashboardApi.getKPIs({ period: 'week' }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 text-sm border border-error/30 bg-error/10 rounded text-error">
        Failed to load performance metrics: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          title="Total Cases"
          value={kpis?.avgCases?.value ?? '—'}
          subtitle={kpis?.avgCases?.comparisonPeriod ?? 'Last period'}
          icon="📊"
        />
        <MetricCard
          title="Resolution Rate"
          value={kpis?.resolutionRate?.value ? `${kpis.resolutionRate.value}%` : '—'}
          subtitle={kpis?.resolutionRate?.comparisonPeriod}
          icon="✅"
          variant="success"
        />
        <MetricCard
          title="Avg Case Life (h)"
          value={kpis?.avgCaseLife?.value ?? '—'}
          subtitle={kpis?.avgCaseLife?.comparisonPeriod}
          icon="⚡"
        />
      </div>
    </div>
  )
}
