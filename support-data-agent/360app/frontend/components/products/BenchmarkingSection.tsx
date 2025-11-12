'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { productsApi } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber } from '@/lib/utils'
import { TrendingUp, Award, Target, ChevronDown, ChevronUp, LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BenchmarkingSectionProps {
  selectedCategory?: string
  selectedSubcategory?: string
  selectedProductId?: string
}

interface ProductMetrics {
  name?: string
  cases?: number
  time?: number
  rate?: number
}

export function BenchmarkingSection({
  selectedCategory,
  selectedSubcategory,
  selectedProductId,
}: BenchmarkingSectionProps) {
  const { filters, activeConfigId } = useAppStore()
  const [isCollapsed, setIsCollapsed] = useState(true)

  const { data: benchmarks, isLoading } = useQuery({
    queryKey: ['product-benchmarks', filters, selectedCategory, selectedSubcategory, selectedProductId],
    queryFn: () => productsApi.getBenchmarks({
      ...filters,
      category: selectedCategory,
      subcategory: selectedSubcategory,
      productId: selectedProductId,
    }),
    enabled: !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Benchmarking</h2>
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
  }

  if (!benchmarks) {
    return null
  }

  const MetricCard = ({
    label,
    value,
    unit,
    icon: Icon,
    className,
  }: {
    label: string
    value: number
    unit: string
    icon: LucideIcon
    className?: string
  }) => (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="p-2 rounded-lg bg-accent">
        <Icon className="w-4 h-4 text-primary" />
      </div>
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-lg font-bold text-foreground">
          {unit === 'hours' ? `${value.toFixed(1)}h` : unit === '%' ? `${value.toFixed(1)}%` : formatNumber(value)}
        </div>
      </div>
    </div>
  )

  const ProductCard = ({
    title,
    product,
    showAllMetrics = false,
  }: {
    title: string
    product: ProductMetrics | undefined
    showAllMetrics?: boolean
  }) => {
    if (!product) return null

    return (
      <div className="bg-background border border-border rounded-lg p-4">
        <div className="text-xs font-medium text-muted-foreground mb-2">{title}</div>
        <div className="font-semibold text-foreground mb-3">{product.name}</div>
        <div className="grid grid-cols-1 gap-3">
          {showAllMetrics ? (
            <>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Cases</span>
                <span className="text-sm font-medium text-foreground">{formatNumber(product.cases || 0)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Resolution Time</span>
                <span className="text-sm font-medium text-foreground">{(product.time || 0).toFixed(1)}h</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Resolution Rate</span>
                <span className="text-sm font-medium text-success">{(product.rate || 0).toFixed(1)}%</span>
              </div>
            </>
          ) : (
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                {product.time !== undefined ? 'Resolution Time' : product.rate !== undefined ? 'Resolution Rate' : 'Cases'}
              </span>
              <span className="text-sm font-medium text-foreground">
                {product.time !== undefined
                  ? `${product.time.toFixed(1)}h`
                  : product.rate !== undefined
                  ? `${product.rate.toFixed(1)}%`
                  : formatNumber(product.cases || 0)}
              </span>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between p-6 hover:bg-accent/50 transition-colors"
      >
        <div>
          <h2 className="text-lg font-semibold text-foreground text-left">Benchmarking</h2>
          <p className="text-sm text-muted-foreground text-left">
            {benchmarks.scope === 'All Products' ? 'All Products' : `Filtered by: ${benchmarks.scope}`}
          </p>
        </div>
        {isCollapsed ? (
          <ChevronDown className="w-5 h-5 text-muted-foreground" />
        ) : (
          <ChevronUp className="w-5 h-5 text-muted-foreground" />
        )}
      </button>

      {/* Collapsible Content */}
      {!isCollapsed && (
        <div className="px-6 pb-6 space-y-6">{/* Average Metrics */}
        <div className="bg-accent/30 border border-border rounded-lg p-4">
          <div className="text-sm font-medium text-muted-foreground mb-3">Average Metrics</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard
              label="Cases"
              value={benchmarks.average.cases}
              unit="cases"
              icon={TrendingUp}
            />
            <MetricCard
              label="Resolution Time"
              value={benchmarks.average.time}
              unit="hours"
              icon={Target}
            />
            <MetricCard
              label="Resolution Rate"
              value={benchmarks.average.rate}
              unit="%"
              icon={Award}
            />
          </div>
        </div>

        {/* Your Product (if selected) */}
        {benchmarks.yourProduct && (
          <div>
            <div className="text-sm font-medium text-foreground mb-3">Your Product</div>
            <ProductCard
              title="Your Product Performance"
              product={benchmarks.yourProduct}
              showAllMetrics={true}
            />
          </div>
        )}

        {/* Top & Bottom Performers */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-sm font-medium text-foreground mb-3">Top Performers</div>
            <div className="space-y-3">
              <ProductCard title="Highest Case Volume" product={benchmarks.topPerformer} />
              <ProductCard title="Fastest Resolution" product={benchmarks.bestTimePerformer} />
              <ProductCard title="Best Resolution Rate" product={benchmarks.bestRatePerformer} />
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-foreground mb-3">Needs Attention</div>
            <div className="space-y-3">
              <ProductCard title="Lowest Case Volume" product={benchmarks.bottomPerformer} />
            </div>
          </div>
        </div>
      </div>
      )}
    </div>
  )
}
