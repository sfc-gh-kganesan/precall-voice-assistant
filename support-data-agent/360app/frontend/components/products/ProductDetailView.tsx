'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi, usageApi } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ProductMetrics } from '@/types'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AIInsightsPanel } from './AIInsightsPanel'
import { ProductKPICards } from './ProductKPICards'
import { RecentCasesSidebar } from './RecentCasesSidebar'
import { BenchmarkContext } from './BenchmarkContext'
import { UsageTrendsSection } from './UsageTrendsSection'
import { HighValueCustomers } from './HighValueCustomers'

// Products that have validated usage metrics queries
const PRODUCTS_WITH_USAGE_METRICS = new Set([
  'Cortex Search',
  // Add more products here as usage queries are validated for each product
])

interface ProductDetailViewProps {
  productId: string
  onClose: () => void
}

export function ProductDetailView({ productId, onClose }: ProductDetailViewProps) {
  const { filters, activeConfigId } = useAppStore()

  const { data: products, isLoading } = useQuery({
    queryKey: ['product-metrics', filters],
    queryFn: () => dashboardApi.getProductMetrics(filters),
    enabled: !!activeConfigId,
  })

  const product = products?.find((p: ProductMetrics) => p.productId === productId)
  const hasUsageMetrics = product ? PRODUCTS_WITH_USAGE_METRICS.has(product.productName) : false

  // Fetch usage timeline for Cortex Search only
  const { data: timeline } = useQuery({
    queryKey: ['usage-credits-timeline', product?.productName],
    queryFn: () => usageApi.getCreditsTimeline(),
    enabled: hasUsageMetrics && !!product,
  })

  // Calculate total consumption based on filters.period from app store
  const totalConsumption = useMemo(() => {
    if (!timeline || timeline.length === 0) return 0

    const daysToInclude = filters.period === 'week' ? 7 : 30
    const relevantData = timeline.slice(0, daysToInclude)
    return Math.floor(relevantData.reduce((sum, point) => sum + point.credits, 0))
  }, [timeline, filters.period])

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
  }

  if (!product) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="text-center py-12 text-muted-foreground">
          Product not found
        </div>
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">{product.productName}</h2>
          <p className="text-sm text-muted-foreground">{product.productCategory}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-accent rounded transition-colors"
        >
          <X className="w-5 h-5 text-muted-foreground" />
        </button>
      </div>

      {/* Main Content Grid - 2/3 left, 1/3 right sidebar */}
      <div className="grid grid-cols-3 gap-4">
        {/* Main Content Column (2/3) */}
        <div className="col-span-2 space-y-4">
          {/* KPI Summary Cards */}
          <ProductKPICards
            totalCases={product.metrics.totalCases}
            avgCaseLife={product.metrics.avgCaseLife}
            resolutionRate={product.metrics.resolutionRate}
            totalConsumption={hasUsageMetrics ? totalConsumption : undefined}
            timePeriod={hasUsageMetrics ? filters.period : undefined}
          />

          {/* Usage & Support Trends Section - Only for products with validated metrics */}
          {hasUsageMetrics && (
            <UsageTrendsSection
              productName={product.productName}
              caseVolumeTrend={product.trend}
            />
          )}

          {/* Cortex Search: High-Value Customers & Top Issues Side by Side */}
          {hasUsageMetrics && (
            <div className="grid grid-cols-2 gap-4">
              {/* High-Value Customers Section - Left Column */}
              <div>
                <HighValueCustomers productName={product.productName} />
              </div>

              {/* Top Issues - Right Column */}
              {product.topIssues.length > 0 && (
                <div className="bg-card border border-border rounded-lg p-4">
                  <h3 className="text-lg font-bold text-foreground mb-3">🔥 Top Issues</h3>
                  <div className="space-y-2">
                    {product.topIssues.map((issue, idx) => (
                      <div
                        key={idx}
                        className="bg-background border border-border rounded-lg p-3 flex items-start gap-3"
                      >
                        <div className={cn(
                          'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                          idx === 0 ? 'bg-error/20 text-error' :
                          idx === 1 ? 'bg-warning/20 text-warning' :
                          'bg-muted text-muted-foreground'
                        )}>
                          {idx + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-foreground">{issue.issue}</div>
                          <div className="text-xs text-muted-foreground mt-1">{issue.count} cases</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Non-Cortex Search: Case Volume Trend & Top Issues Side by Side */}
          {!hasUsageMetrics && (product.trend?.length > 0 || product.topIssues.length > 0) && (
            <div className="grid grid-cols-2 gap-4">
              {/* Case Volume Trend - Left Column */}
              {product.trend && product.trend.length > 0 && (
                <div className="bg-card border border-border rounded-lg p-4">
                  <h3 className="text-lg font-bold text-foreground mb-3">📈 Case Volume Trend</h3>
                  <div className="bg-background border border-border rounded-lg p-4">
                    <div className="h-32 flex items-end gap-1">
                      {product.trend.map((point, idx) => {
                        const maxValue = Math.max(...product.trend.map(p => p.value))
                        const height = maxValue > 0 ? (point.value / maxValue) * 100 : 0
                        return (
                          <div
                            key={idx}
                            className="flex-1 bg-primary/70 rounded-t hover:bg-primary transition-colors relative group"
                            style={{ height: `${height}%`, minHeight: '4px' }}
                          >
                            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-popover border border-border px-2 py-1 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                              {point.value} cases<br/>
                              {new Date(point.date).toLocaleDateString()}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                    <div className="flex justify-between mt-3 text-xs text-muted-foreground">
                      <span>{new Date(product.trend[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                      <span>{new Date(product.trend[product.trend.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Top Issues - Right Column */}
              {product.topIssues.length > 0 && (
                <div className="bg-card border border-border rounded-lg p-4">
                  <h3 className="text-lg font-bold text-foreground mb-3">🔥 Top Issues</h3>
                  <div className="space-y-2">
                    {product.topIssues.map((issue, idx) => (
                      <div
                        key={idx}
                        className="bg-background border border-border rounded-lg p-3 flex items-start gap-3"
                      >
                        <div className={cn(
                          'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                          idx === 0 ? 'bg-error/20 text-error' :
                          idx === 1 ? 'bg-warning/20 text-warning' :
                          'bg-muted text-muted-foreground'
                        )}>
                          {idx + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-foreground">{issue.issue}</div>
                          <div className="text-xs text-muted-foreground mt-1">{issue.count} cases</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* AI Insights - Now Collapsible */}
          <AIInsightsPanel aiSummary={product.aiSummary} rootCauses={product.rootCauses} />
        </div>

        {/* Sidebar Column (1/3) - Sticky */}
        <div className="col-span-1">
          <div className="sticky top-4 space-y-4">
            {/* Recent Critical Cases */}
            <RecentCasesSidebar productName={product.productName} />

            {/* Benchmark Context */}
            <BenchmarkContext productId={productId} period={filters.period || 'week'} />
          </div>
        </div>
      </div>
    </div>
  )
}
