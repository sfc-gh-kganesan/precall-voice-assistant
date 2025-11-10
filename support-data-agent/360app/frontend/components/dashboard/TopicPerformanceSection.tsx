'use client'

import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { PerformanceSection } from './PerformanceSection'
import { TrendingUp, Clock, CheckCircle } from 'lucide-react'

export function TopicPerformanceSection() {
  const { filters, activeConfigId } = useAppStore()

  const { data, isLoading } = useQuery({
    queryKey: ['topic-performance', filters],
    queryFn: () => dashboardApi.getTopicPerformance(filters),
    enabled: !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Topic Performance</h2>
        <LoadingSpinner size="lg" className="h-64" />
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className="mt-12">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground mb-2">Support Trends</h2>
        <p className="text-sm text-muted-foreground">
          Week-over-week support topic trends
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Case Volume Trends */}
        <PerformanceSection
          title="Case Volume Trends"
          topLabel="Rising Topics"
          bottomLabel="Declining Topics"
          topItems={data.caseVolume.topPerformers}
          bottomItems={data.caseVolume.bottomPerformers}
          metricType="caseVolume"
          icon={<TrendingUp className="w-5 h-5" />}
        />

        {/* Resolution Time Changes */}
        <PerformanceSection
          title="Resolution Time Changes"
          topLabel="Deteriorating"
          bottomLabel="Improving"
          topItems={data.resolutionTime.topPerformers}
          bottomItems={data.resolutionTime.bottomPerformers}
          metricType="resolutionTime"
          icon={<Clock className="w-5 h-5" />}
        />

        {/* Resolution Rate Performance */}
        <PerformanceSection
          title="Resolution Rate Performance"
          topLabel="Improving Success"
          bottomLabel="Declining Success"
          topItems={data.resolutionRate.topPerformers}
          bottomItems={data.resolutionRate.bottomPerformers}
          metricType="resolutionRate"
          icon={<CheckCircle className="w-5 h-5" />}
        />
      </div>
    </div>
  )
}
