'use client'

import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber } from '@/lib/utils'
import { ProductMetrics } from '@/types'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ProductGridProps {
  selectedCategories: string[]
  selectedSubcategories: string[]
  selectedProducts: string[]
  searchQuery: string
  onProductToggle: (productId: string) => void
  onProductSelect: (productId: string) => void
}

export function ProductGrid({
  selectedCategories,
  selectedSubcategories,
  selectedProducts,
  searchQuery,
  onProductToggle,
  onProductSelect,
}: ProductGridProps) {
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

  // Filter products based on selections
  let filteredProducts = products || []

  if (selectedCategories.length > 0) {
    filteredProducts = filteredProducts.filter((p: ProductMetrics) =>
      selectedCategories.includes(p.productCategory)
    )
  }

  if (selectedSubcategories.length > 0) {
    filteredProducts = filteredProducts.filter((p: ProductMetrics) =>
      p.productSubcategory && selectedSubcategories.includes(p.productSubcategory)
    )
  }

  if (searchQuery.length >= 2) {
    filteredProducts = filteredProducts.filter((p: ProductMetrics) =>
      p.productName.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }

  const getTrendIcon = (changeType: string) => {
    switch (changeType) {
      case 'increase':
        return <TrendingUp className="w-3 h-3 text-error" />
      case 'decrease':
        return <TrendingDown className="w-3 h-3 text-success" />
      default:
        return <Minus className="w-3 h-3 text-muted-foreground" />
    }
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-foreground">
          Products
          {selectedCategories.length > 0 && (
            <span className="ml-2 text-sm text-muted-foreground font-normal">
              ({filteredProducts.length} in {selectedCategories[0]})
            </span>
          )}
        </h2>
        <div className="text-xs text-muted-foreground">
          Click to view details • Shift+Click to compare
        </div>
      </div>

      {filteredProducts.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          {searchQuery ? 'No products found matching your search' : 'No products found'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProducts.map((product: ProductMetrics) => {
            const isSelected = selectedProducts.includes(product.productId)

            return (
              <div
                key={product.productId}
                onClick={(e) => {
                  if (e.shiftKey) {
                    onProductToggle(product.productId)
                  } else {
                    onProductSelect(product.productId)
                  }
                }}
                className={cn(
                  'bg-background border rounded-lg p-4 cursor-pointer transition-all hover:shadow-md',
                  isSelected
                    ? 'border-primary ring-2 ring-primary/20'
                    : 'border-border hover:border-primary/50'
                )}
              >
                {/* Product Name */}
                <div className="mb-3">
                  <h3 className="font-semibold text-foreground text-sm line-clamp-1">
                    {product.productName}
                  </h3>
                  <p className="text-xs text-muted-foreground">{product.productCategory}</p>
                </div>

                {/* Key Metric */}
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="text-2xl font-bold text-primary">
                    {formatNumber(product.metrics.totalCases.value)}
                  </span>
                  <span className="text-xs text-muted-foreground">cases</span>
                </div>

                {/* Trend */}
                <div className="flex items-center gap-1 mb-3">
                  {getTrendIcon(product.metrics.totalCases.changeType)}
                  <span className={cn(
                    'text-xs font-medium',
                    product.metrics.totalCases.changeType === 'increase' ? 'text-error' :
                    product.metrics.totalCases.changeType === 'decrease' ? 'text-success' :
                    'text-muted-foreground'
                  )}>
                    {product.metrics.totalCases.changePercentage > 0 ? '+' : ''}
                    {product.metrics.totalCases.changePercentage}% vs prev period
                  </span>
                </div>

                {/* Sparkline */}
                {product.trend && product.trend.length > 0 && (
                  <div className="h-8 flex items-end gap-0.5">
                    {product.trend.slice(-10).map((point, idx) => {
                      const maxValue = Math.max(...product.trend.slice(-10).map(p => p.value))
                      const height = maxValue > 0 ? (point.value / maxValue) * 100 : 0
                      return (
                        <div
                          key={idx}
                          className="flex-1 bg-primary/40 rounded-t"
                          style={{ height: `${height}%`, minHeight: '2px' }}
                        />
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
