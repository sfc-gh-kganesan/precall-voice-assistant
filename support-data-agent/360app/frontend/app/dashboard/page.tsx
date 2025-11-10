'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { KPICard } from '@/components/dashboard/KPICard'
import { FilterBar } from '@/components/common/FilterBar'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ProductPerformanceSection } from '@/components/dashboard/ProductPerformanceSection'
import { TopicPerformanceSection } from '@/components/dashboard/TopicPerformanceSection'
import { SnowflakeLogo } from '@/components/ui/SnowflakeLogo'
import { NoConfigurationAlert } from '@/components/common/NoConfigurationAlert'

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
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <SnowflakeLogo size={36} />
              <div>
                <h1 className="text-xl font-bold text-foreground">
                  Support Intelligence
                </h1>
                <p className="text-xs text-muted-foreground">Powered by Snowflake</p>
              </div>
            </div>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
                Dashboard
              </Link>
              <Link href="/products" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Products
              </Link>
              <Link href="/topics" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Topics
              </Link>
              <Link href="/tickets" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Cases
              </Link>
              <Link href="/admin" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Admin
              </Link>
            </nav>
          </div>
        </div>
      </header>

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

            {/* KPI Cards */}
            <div className="mb-6">
              {kpisLoading ? (
                <LoadingSpinner size="lg" className="h-32" />
              ) : kpis ? (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <KPICard metric={kpis.avgCases} />
                  <KPICard metric={kpis.avgCaseLife} />
                  <KPICard metric={kpis.resolutionRate} />
                  <KPICard metric={kpis.firstResponseTime} />
                </div>
              ) : null}
            </div>

            {/* Product & Topic Metrics */}
            <div className="space-y-6">
              <ProductPerformanceSection />
              <TopicPerformanceSection />
            </div>
          </>
        )}
      </main>
    </div>
  )
}
