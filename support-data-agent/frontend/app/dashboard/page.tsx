'use client'

import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { KPICard } from '@/components/dashboard/KPICard'
import { FilterBar } from '@/components/common/FilterBar'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ProductPerformanceSection } from '@/components/dashboard/ProductPerformanceSection'
import { TopicPerformanceSection } from '@/components/dashboard/TopicPerformanceSection'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { SnowflakeLogo } from '@/components/ui/SnowflakeLogo'
import { NoConfigurationAlert } from '@/components/common/NoConfigurationAlert'

export default function DashboardPage() {
  const { filters, chatOpen, activeConfigId, isInitializing } = useAppStore()

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
              <a href="/dashboard" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
                Dashboard
              </a>
              <a href="/products" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Products
              </a>
              <a href="/topics" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Topics
              </a>
              <a href="/tickets" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Cases
              </a>
              <a href="/admin" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Admin
              </a>
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

      {/* Chat Window */}
      {chatOpen && <ChatWindow />}

      {/* Chat Toggle Button */}
      <button
        onClick={() => useAppStore.getState().toggleChat()}
        className="fixed bottom-4 right-4 w-14 h-14 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 hover:scale-110 transition-all flex items-center justify-center ring-2 ring-primary/20"
        aria-label="Toggle chat"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </button>
    </div>
  )
}
