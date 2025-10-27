'use client'

import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber, formatPercentage } from '@/lib/utils'
import { ProductMetrics } from '@/types'

export function ProductMetricsSection() {
  const { filters, activeConfigId } = useAppStore()

  const { data: products, isLoading } = useQuery({
    queryKey: ['product-metrics', filters],
    queryFn: () => dashboardApi.getProductMetrics(filters),
    enabled: !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Product Metrics</h2>
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">Product Metrics</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {products?.map((product: ProductMetrics) => (
          <div
            key={product.productId}
            className="bg-background border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
          >
            {/* Header */}
            <div className="mb-3 pb-3 border-b border-border">
              <h3 className="font-semibold text-foreground">{product.productName}</h3>
              <span className="text-xs text-muted-foreground">{product.productCategory}</span>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="text-center">
                <div className="text-xl font-bold text-primary">
                  {formatNumber(product.metrics.totalCases.value)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Cases</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-foreground">
                  {product.metrics.avgCaseLife.value.toFixed(1)}h
                </div>
                <div className="text-xs text-muted-foreground mt-1">Avg Life</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-success">
                  {formatPercentage(product.metrics.resolutionRate.value)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Resolved</div>
              </div>
            </div>

            {/* Top Issues */}
            {product.topIssues.length > 0 && (
              <div className="pt-3 border-t border-border">
                <div className="text-xs font-medium text-muted-foreground mb-2">Top Issues</div>
                <div className="space-y-1">
                  {product.topIssues.slice(0, 2).map((issue, idx) => (
                    <div key={idx} className="flex justify-between items-center text-xs">
                      <span className="text-foreground truncate flex-1">{issue.issue}</span>
                      <span className="text-muted-foreground ml-2">{issue.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
