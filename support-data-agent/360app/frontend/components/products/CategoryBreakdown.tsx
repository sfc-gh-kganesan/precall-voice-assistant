'use client'

import { ProductMetrics } from '@/types'
import { formatNumber, cn } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface CategoryBreakdownProps {
  products: ProductMetrics[]
  selectedCategory: string
  onCategorySelect: (category: string) => void
}

interface CategoryStats {
  name: string
  totalCases: number
  percentOfTotal: number
  avgResolutionTime: number
  trend: number
  trendType: 'increase' | 'decrease' | 'neutral'
}

interface CategoryAggregation {
  name: string
  totalCases: number
  casesList: number[]
  resolutionTimes: number[]
  trends: number[]
}

export function CategoryBreakdown({ products, selectedCategory, onCategorySelect }: CategoryBreakdownProps) {
  // Aggregate products by category
  const categoryStats = products.reduce((acc, product) => {
    const category = product.productCategory
    if (!acc[category]) {
      acc[category] = {
        name: category,
        totalCases: 0,
        casesList: [],
        resolutionTimes: [],
        trends: [],
      }
    }
    acc[category].totalCases += product.metrics.totalCases.value
    acc[category].casesList.push(product.metrics.totalCases.value)
    acc[category].resolutionTimes.push(product.metrics.avgCaseLife.value)
    acc[category].trends.push(product.metrics.totalCases.changePercentage)
    return acc
  }, {} as Record<string, CategoryAggregation>)

  const totalCases = Object.values(categoryStats).reduce((sum: number, cat: CategoryAggregation) => sum + cat.totalCases, 0)

  const categories: CategoryStats[] = Object.values(categoryStats).map((cat: CategoryAggregation) => {
    const avgTrend = cat.trends.reduce((sum: number, t: number) => sum + t, 0) / cat.trends.length
    const avgResolution = cat.resolutionTimes.reduce((sum: number, t: number) => sum + t, 0) / cat.resolutionTimes.length

    return {
      name: cat.name,
      totalCases: cat.totalCases,
      percentOfTotal: (cat.totalCases / totalCases) * 100,
      avgResolutionTime: avgResolution,
      trend: avgTrend,
      trendType: (avgTrend > 0 ? 'increase' : avgTrend < 0 ? 'decrease' : 'neutral') as 'neutral' | 'increase' | 'decrease',
    }
  }).sort((a, b) => b.totalCases - a.totalCases).slice(0, 4)

  const getTrendColor = (trendType: string) => {
    switch (trendType) {
      case 'increase':
        return 'text-error'
      case 'decrease':
        return 'text-success'
      default:
        return 'text-muted-foreground'
    }
  }

  // Find max total cases for bar chart scaling
  const maxTotalCases = Math.max(...categories.map(c => c.totalCases))

  return (
    <div>
      <div className="mb-3">
        <h2 className="text-lg font-bold text-foreground mb-1">Category Overview</h2>
        <p className="text-xs text-muted-foreground">
          Click a category to filter products below
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-[2fr,1.5fr,1fr,1fr] gap-3 px-4 py-2 bg-muted/50 border-b border-border text-xs font-medium text-muted-foreground">
          <div>Category</div>
          <div>Total Cases</div>
          <div>Avg Resolution</div>
          <div>Trend</div>
        </div>

        {/* Table Rows */}
        <div>
          {categories.map((category) => {
            const isSelected = selectedCategory === category.name
            const barWidth = (category.totalCases / maxTotalCases) * 100

            return (
              <button
                key={category.name}
                onClick={() => onCategorySelect(category.name)}
                className={cn(
                  'w-full grid grid-cols-[2fr,1.5fr,1fr,1fr] gap-3 px-4 py-3 text-left transition-all hover:bg-muted/30',
                  isSelected && 'bg-primary/5 border-l-4 border-l-primary'
                )}
              >
                {/* Category Name */}
                <div className="text-sm font-medium text-foreground truncate">
                  {category.name}
                </div>

                {/* Total Cases with Bar Chart */}
                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-sm font-bold text-primary">
                      {formatNumber(category.totalCases)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      ({category.percentOfTotal.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary/60 rounded-full transition-all"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>

                {/* Avg Resolution Time */}
                <div className="text-sm text-foreground">
                  {category.avgResolutionTime.toFixed(1)}h
                </div>

                {/* Trend */}
                <div className="flex items-center gap-1">
                  {category.trendType === 'increase' ? (
                    <TrendingUp className="w-3.5 h-3.5 text-error flex-shrink-0" />
                  ) : category.trendType === 'decrease' ? (
                    <TrendingDown className="w-3.5 h-3.5 text-success flex-shrink-0" />
                  ) : null}
                  <span className={cn('text-sm font-medium', getTrendColor(category.trendType))}>
                    {category.trend > 0 ? '+' : ''}{category.trend.toFixed(1)}%
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
