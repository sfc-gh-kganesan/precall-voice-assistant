'use client'

import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { PerformanceSection } from './PerformanceSection'
import { TrendingUp, Clock, CheckCircle } from 'lucide-react'

export function ProductPerformanceSection() {
  const { filters, activeConfigId } = useAppStore()

  const { data, isLoading } = useQuery({
    queryKey: ['product-performance', filters],
    queryFn: () => dashboardApi.getProductPerformance(filters),
    enabled: !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Product Performance</h2>
        <LoadingSpinner size="lg" className="h-64" />
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div>
      <div className="mb-3">
        <h2 className="text-lg font-bold text-foreground mb-1">Product Trends</h2>
        <p className="text-xs text-muted-foreground">
          Week-over-week product trends
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Case Volume Trends */}
        <PerformanceSection
          title="Case Volume Trends"
          topLabel="Rising Products"
          bottomLabel="Declining Products"
          topItems={data.caseVolume.topPerformers.slice(0, 3)}
          bottomItems={data.caseVolume.bottomPerformers.slice(0, 3)}
          metricType="caseVolume"
          icon={<TrendingUp className="w-4 h-4" />}
        />

        {/* Resolution Time Changes */}
        <PerformanceSection
          title="Resolution Time Changes"
          topLabel="Deteriorating"
          bottomLabel="Improving"
          topItems={data.resolutionTime.topPerformers.slice(0, 3)}
          bottomItems={data.resolutionTime.bottomPerformers.slice(0, 3)}
          metricType="resolutionTime"
          icon={<Clock className="w-4 h-4" />}
        />

        {/* Resolution Rate Performance */}
        <PerformanceSection
          title="Resolution Rate Performance"
          topLabel="Declining Success"
          bottomLabel="Improving Success"
          topItems={data.resolutionRate.bottomPerformers.slice(0, 3)}
          bottomItems={data.resolutionRate.topPerformers.slice(0, 3)}
          metricType="resolutionRate"
          icon={<CheckCircle className="w-4 h-4" />}
        />
      </div>
    </div>
  )
}
