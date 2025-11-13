'use client'

import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { KPICard } from '@/components/dashboard/KPICard'
import { FilterBar } from '@/components/common/FilterBar'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { CategorySummary } from '@/components/dashboard/CategorySummary'
import { TopicPerformanceSection } from '@/components/dashboard/TopicPerformanceSection'
import { NoConfigurationAlert } from '@/components/common/NoConfigurationAlert'
import { AppHeader } from '@/components/common/AppHeader'

export default function DashboardPage() {
  const { filters, activeConfigId, isInitializing } = useAppStore()

  // Fetch KPIs
  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ['kpis', filters],
    queryFn: () => dashboardApi.getKPIs(filters),
    enabled: !!activeConfigId,
  })

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <AppHeader />

      {/* Main Content */}
      <main className="container mx-auto px-3 py-6">
        {isInitializing ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : !activeConfigId ? (
          <NoConfigurationAlert />
        ) : (
          <>
            {/* Filter Bar */}
            <FilterBar className="mb-6" />

            {/* KPI Cards & Category Summary */}
            <div className="mb-6 space-y-6">
              {kpisLoading ? (
                <LoadingSpinner size="lg" className="h-32" />
              ) : kpis ? (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <KPICard metric={kpis.avgCases} />
                    <KPICard metric={kpis.avgCaseLife} />
                    <KPICard metric={kpis.resolutionRate} />
                    <KPICard metric={kpis.firstResponseTime} />
                  </div>
                  <CategorySummary />
                </>
              ) : null}
            </div>

            {/* Topic Metrics */}
            <div className="space-y-6">
              <TopicPerformanceSection />
            </div>
          </>
        )}
      </main>
    </div>
  )
}
