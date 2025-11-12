'use client'

import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber, formatPercentage } from '@/lib/utils'
import { ProductMetrics } from '@/types'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ProductComparisonProps {
  selectedProductIds: string[]
}

export function ProductComparison({ selectedProductIds }: ProductComparisonProps) {
  const { filters, activeConfigId } = useAppStore()

  const { data: allProducts, isLoading } = useQuery({
    queryKey: ['product-metrics', filters],
    queryFn: () => dashboardApi.getProductMetrics(filters),
    enabled: !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Product Comparison</h2>
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
  }

  if (!selectedProductIds || selectedProductIds.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Product Comparison</h2>
        <div className="text-center py-8 text-muted-foreground">
          Select products to compare their performance
        </div>
      </div>
    )
  }

  const selectedProducts = allProducts?.filter((p: ProductMetrics) =>
    selectedProductIds.includes(p.productId)
  ) || []

  if (selectedProducts.length === 0) {
    return null
  }

  const getTrendIcon = (changeType: string) => {
    switch (changeType) {
      case 'increase':
        return <TrendingUp className="w-4 h-4 text-error" />
      case 'decrease':
        return <TrendingDown className="w-4 h-4 text-success" />
      default:
        return <Minus className="w-4 h-4 text-muted-foreground" />
    }
  }

  const getTrendColor = (changeType: string) => {
    switch (changeType) {
      case 'increase':
        return 'text-error'
      case 'decrease':
        return 'text-success'
      default:
        return 'text-muted-foreground'
    }
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">
        Product Comparison ({selectedProducts.length})
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-border">
            <tr className="text-left">
              <th className="pb-3 pr-4 text-sm font-medium text-muted-foreground sticky left-0 bg-card">
                Product
              </th>
              <th className="pb-3 px-4 text-sm font-medium text-muted-foreground text-right">
                Total Cases
              </th>
              <th className="pb-3 px-4 text-sm font-medium text-muted-foreground text-right">
                Change
              </th>
              <th className="pb-3 px-4 text-sm font-medium text-muted-foreground text-right">
                Avg Case Life
              </th>
              <th className="pb-3 px-4 text-sm font-medium text-muted-foreground text-right">
                Resolution Rate
              </th>
              <th className="pb-3 pl-4 text-sm font-medium text-muted-foreground">
                Top Issues
              </th>
            </tr>
          </thead>
          <tbody>
            {selectedProducts.map((product: ProductMetrics) => (
              <tr
                key={product.productId}
                className="border-b border-border last:border-b-0 hover:bg-accent/50 transition-colors"
              >
                <td className="py-4 pr-4 sticky left-0 bg-card">
                  <div className="font-medium text-foreground">{product.productName}</div>
                  <div className="text-xs text-muted-foreground">{product.productCategory}</div>
                </td>
                <td className="py-4 px-4 text-right font-semibold text-foreground">
                  {formatNumber(product.metrics.totalCases.value)}
                </td>
                <td className="py-4 px-4 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {getTrendIcon(product.metrics.totalCases.changeType)}
                    <span className={cn('text-sm font-medium', getTrendColor(product.metrics.totalCases.changeType))}>
                      {product.metrics.totalCases.changePercentage > 0 ? '+' : ''}
                      {product.metrics.totalCases.changePercentage}%
                    </span>
                  </div>
                </td>
                <td className="py-4 px-4 text-right text-foreground">
                  {product.metrics.avgCaseLife.value.toFixed(1)}h
                </td>
                <td className="py-4 px-4 text-right text-success font-medium">
                  {formatPercentage(product.metrics.resolutionRate.value)}
                </td>
                <td className="py-4 pl-4">
                  <div className="space-y-1 max-w-xs">
                    {product.topIssues.slice(0, 2).map((issue, idx) => (
                      <div key={idx} className="text-xs text-muted-foreground truncate">
                        • {issue.issue} ({issue.count})
                      </div>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
