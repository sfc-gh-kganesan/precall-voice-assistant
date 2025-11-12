'use client'

import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ProductMetrics } from '@/types'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AIInsightsPanel } from './AIInsightsPanel'
import { ProductKPICards } from './ProductKPICards'
import { RecentCasesSidebar } from './RecentCasesSidebar'
import { BenchmarkContext } from './BenchmarkContext'

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

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
  }

  const product = products?.find((p: ProductMetrics) => p.productId === productId)

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
      <div className="grid grid-cols-3 gap-6">
        {/* Main Content Column (2/3) */}
        <div className="col-span-2 space-y-6">
          {/* KPI Summary Cards */}
          <ProductKPICards
            totalCases={product.metrics.totalCases}
            avgCaseLife={product.metrics.avgCaseLife}
            resolutionRate={product.metrics.resolutionRate}
          />

          {/* Top Issues */}
          {product.topIssues.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">🔥 Top Issues</h3>
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

          {/* Trend Chart */}
          {product.trend && product.trend.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-foreground mb-3">📈 Case Volume Trend</h3>
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
