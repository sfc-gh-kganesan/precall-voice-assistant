'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SnowflakeLogo } from '@/components/ui/SnowflakeLogo'
import { NoConfigurationAlert } from '@/components/common/NoConfigurationAlert'
import { formatNumber, formatPercentage, cn } from '@/lib/utils'
import { useAppStore } from '@/stores/appStore'
import { ProductMetrics } from '@/types'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { ProductTrendsSection } from '@/components/products/ProductTrendsSection'
import { CategoryBreakdown } from '@/components/products/CategoryBreakdown'
import { ProductDetailSidebar } from '@/components/products/ProductDetailSidebar'

export default function ProductsPage() {
  const [period, setPeriod] = useState<'week' | 'month'>('week')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedProduct, setSelectedProduct] = useState<ProductMetrics | null>(null)
  const configId = useAppStore((state) => state.activeConfigId)
  const isInitializing = useAppStore((state) => state.isInitializing)
  const setFilters = useAppStore((state) => state.setFilters)

  // Update filters in global store so ProductPerformanceSection can access them
  useEffect(() => {
    setFilters({ period })
  }, [period, setFilters])

  const { data: products, isLoading } = useQuery({
    queryKey: ['product-metrics', period],
    queryFn: () => dashboardApi.getProductMetrics({ period }),
    enabled: !!configId,
  })

  // Set initial category to first category (highest volume) for performance
  useEffect(() => {
    if (products && products.length > 0 && !selectedCategory) {
      const firstCategory = products[0].productCategory
      setSelectedCategory(firstCategory)
    }
  }, [products, selectedCategory])

  const categories = ['all', ...Array.from(new Set(products?.map(p => p.productCategory) || []))]
  const filteredProducts = selectedCategory === 'all'
    ? products
    : products?.filter(p => p.productCategory === selectedCategory)

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
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <SnowflakeLogo size={36} />
              <div>
                <h1 className="text-xl font-bold text-foreground">
                  Product Analytics
                </h1>
                <p className="text-xs text-muted-foreground">Powered by Snowflake</p>
              </div>
            </div>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </Link>
              <Link href="/products" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
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

      <main className="container mx-auto px-4 py-8">
        {isInitializing ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : !configId ? (
          <NoConfigurationAlert />
        ) : (
          <>
            {/* Overview Section - Side by Side on Desktop */}
            {!isLoading && products && products.length > 0 && (
              <div className="flex flex-col lg:flex-row gap-6 mb-8 lg:items-stretch">
                {/* Category Overview - Left 60% */}
                <div className="lg:w-[60%] flex flex-col">
                  <CategoryBreakdown
                    products={products}
                    selectedCategory={selectedCategory}
                    onCategorySelect={setSelectedCategory}
                  />
                </div>

                {/* Product Trends - Right 40% */}
                <div className="lg:w-[40%] flex flex-col">
                  <ProductTrendsSection />
                </div>
              </div>
            )}

            {/* Filters */}
            <div className="flex gap-4 mb-6">
              <div className="flex gap-2">
                <button
                  onClick={() => setPeriod('week')}
                  className={cn(
                    'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                    period === 'week'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-card border border-border text-foreground hover:bg-muted'
                  )}
                >
                  This Week
                </button>
                <button
                  onClick={() => setPeriod('month')}
                  className={cn(
                    'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                    period === 'month'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-card border border-border text-foreground hover:bg-muted'
                  )}
                >
                  This Month
                </button>
              </div>

              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-4 py-2 bg-card border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat === 'all' ? 'All Categories' : cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Products Grid */}
            {isLoading ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="lg" />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {filteredProducts?.map((product: ProductMetrics) => (
              <div
                key={product.productId}
                onClick={() => setSelectedProduct(product)}
                className="bg-card border border-border rounded-lg p-6 hover:border-primary/50 transition-colors cursor-pointer"
              >
                {/* Header */}
                <div className="mb-4 pb-4 border-b border-border">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-bold text-foreground">{product.productName}</h3>
                      <span className="text-sm text-muted-foreground">{product.productCategory}</span>
                    </div>
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">
                      {formatNumber(product.metrics.totalCases.value)}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Total Cases</div>
                    <div className="flex items-center justify-center gap-1 mt-1">
                      {getTrendIcon(product.metrics.totalCases.changeType)}
                      <span className={cn('text-xs font-medium', getTrendColor(product.metrics.totalCases.changeType))}>
                        {product.metrics.totalCases.changePercentage > 0 ? '+' : ''}
                        {product.metrics.totalCases.changePercentage}%
                      </span>
                    </div>
                  </div>

                  <div className="text-center">
                    <div className="text-2xl font-bold text-foreground">
                      {product.metrics.avgCaseLife.value.toFixed(1)}h
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Avg Resolution</div>
                    <div className="flex items-center justify-center gap-1 mt-1">
                      {getTrendIcon(product.metrics.avgCaseLife.changeType)}
                      <span className={cn('text-xs font-medium', getTrendColor(product.metrics.avgCaseLife.changeType))}>
                        {product.metrics.avgCaseLife.changePercentage > 0 ? '+' : ''}
                        {product.metrics.avgCaseLife.changePercentage}%
                      </span>
                    </div>
                  </div>

                  <div className="text-center">
                    <div className="text-2xl font-bold text-success">
                      {formatPercentage(product.metrics.resolutionRate.value)}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Resolution Rate</div>
                    <div className="flex items-center justify-center gap-1 mt-1">
                      {getTrendIcon(product.metrics.resolutionRate.changeType)}
                      <span className={cn('text-xs font-medium', getTrendColor(product.metrics.resolutionRate.changeType))}>
                        {product.metrics.resolutionRate.changePercentage > 0 ? '+' : ''}
                        {product.metrics.resolutionRate.changePercentage}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Trend Chart */}
                <div className="mb-4 pt-4 border-t border-border">
                  <h4 className="text-sm font-medium text-muted-foreground mb-3">Weekly Trend</h4>
                  <div className="h-24 flex items-end gap-1">
                    {product.trend.map((point, idx) => {
                      const maxValue = Math.max(...product.trend.map(p => p.value))
                      const height = (point.value / maxValue) * 100
                      return (
                        <div
                          key={idx}
                          className="flex-1 bg-primary/70 rounded-t hover:bg-primary transition-colors relative group"
                          style={{ height: `${height}%` }}
                          title={`${new Date(point.date).toLocaleDateString()}: ${point.value} cases`}
                        >
                          <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-popover border border-border px-2 py-1 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                            {point.value}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                    <span>{new Date(product.trend[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                    <span>{new Date(product.trend[product.trend.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>

                {/* Top Issues */}
                {product.topIssues.length > 0 && (
                  <div className="pt-4 border-t border-border">
                    <h4 className="text-sm font-medium text-muted-foreground mb-3">Top Issues</h4>
                    <div className="space-y-2">
                      {product.topIssues.map((issue, idx) => (
                        <div key={idx} className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-error/20 text-error flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                            {idx + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm text-foreground truncate">{issue.issue}</div>
                            <div className="text-xs text-muted-foreground">{issue.count} cases</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
              </div>
            )}

            {!isLoading && filteredProducts?.length === 0 && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No products found for the selected category.</p>
              </div>
            )}
          </>
        )}
      </main>

      {/* Product Detail Sidebar */}
      {selectedProduct && (
        <ProductDetailSidebar
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </div>
  )
}
