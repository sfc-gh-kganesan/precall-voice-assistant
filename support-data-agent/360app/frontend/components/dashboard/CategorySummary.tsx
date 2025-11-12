'use client'

import { useState, Fragment } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber, formatPercentage } from '@/lib/utils'
import { CategoryMetrics, SubcategoryMetrics } from '@/types'
import { TrendingUp, TrendingDown, Minus, ChevronRight, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export function CategorySummary() {
  const router = useRouter()
  const { filters, activeConfigId } = useAppStore()
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)

  const { data: categories, isLoading } = useQuery({
    queryKey: ['category-metrics', filters],
    queryFn: () => dashboardApi.getCategoryMetrics(filters),
    enabled: !!activeConfigId,
  })

  const { data: subcategories, isLoading: isLoadingSubcategories } = useQuery({
    queryKey: ['subcategory-metrics', expandedCategory, filters],
    queryFn: () => dashboardApi.getSubcategoryMetrics(expandedCategory!, filters),
    enabled: !!expandedCategory && !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Category Overview</h2>
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
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

  const toggleCategory = (categoryName: string) => {
    if (expandedCategory === categoryName) {
      setExpandedCategory(null)
    } else {
      setExpandedCategory(categoryName)
    }
  }

  const navigateToProducts = (subcategoryName: string, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent row click from bubbling
    router.push(`/products?subcategory=${encodeURIComponent(subcategoryName)}`)
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">Category Overview</h2>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-border">
            <tr className="text-left">
              <th className="pb-3 text-sm font-medium text-muted-foreground">Category</th>
              <th className="pb-3 text-sm font-medium text-muted-foreground text-right">Total Cases</th>
              <th className="pb-3 text-sm font-medium text-muted-foreground text-right">Change</th>
              <th className="pb-3 text-sm font-medium text-muted-foreground text-right">Avg Resolution</th>
              <th className="pb-3 text-sm font-medium text-muted-foreground text-right">Resolution Rate</th>
              <th className="pb-3 text-sm font-medium text-muted-foreground text-right">Products</th>
            </tr>
          </thead>
          <tbody>
            {categories?.map((category: CategoryMetrics) => (
              <Fragment key={category.categoryName}>
                <tr
                  className={cn(
                    'border-b border-border hover:bg-accent/50 cursor-pointer transition-colors',
                    expandedCategory === category.categoryName && 'bg-accent/30'
                  )}
                  onClick={() => toggleCategory(category.categoryName)}
                >
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      {expandedCategory === category.categoryName ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="font-medium text-foreground">{category.categoryName}</span>
                    </div>
                  </td>
                  <td className="py-3 text-right font-semibold text-foreground">
                    {formatNumber(category.totalCases)}
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {getTrendIcon(category.changeType)}
                      <span className={cn('text-sm font-medium', getTrendColor(category.changeType))}>
                        {category.casesChangePercentage > 0 ? '+' : ''}{category.casesChangePercentage}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 text-right text-foreground">
                    {category.avgResolution.toFixed(1)}h
                  </td>
                  <td className="py-3 text-right text-success font-medium">
                    {formatPercentage(category.resolutionRate)}
                  </td>
                  <td className="py-3 text-right text-muted-foreground">
                    {category.productCount}
                  </td>
                </tr>

                {/* Subcategory rows */}
                {expandedCategory === category.categoryName && (
                  <>
                    {isLoadingSubcategories ? (
                      <tr>
                        <td colSpan={6} className="py-4">
                          <div className="flex justify-center">
                            <LoadingSpinner size="sm" />
                          </div>
                        </td>
                      </tr>
                    ) : (
                      subcategories?.map((subcat: SubcategoryMetrics) => (
                        <tr
                          key={`${subcat.categoryName}-${subcat.subcategoryName}`}
                          className="border-b border-border bg-accent/20 hover:bg-accent/40 cursor-pointer transition-colors"
                          onClick={(e) => navigateToProducts(subcat.subcategoryName, e)}
                        >
                          <td className="py-2 pl-10">
                            <span className="text-sm text-muted-foreground">{subcat.subcategoryName}</span>
                          </td>
                          <td className="py-2 text-right text-sm text-foreground">
                            {formatNumber(subcat.totalCases)}
                          </td>
                          <td className="py-2 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <span className={cn('text-xs', getTrendColor(subcat.changeType))}>
                                {subcat.casesChangePercentage > 0 ? '+' : ''}{subcat.casesChangePercentage}%
                              </span>
                            </div>
                          </td>
                          <td className="py-2 text-right text-sm text-foreground">
                            {subcat.avgResolution.toFixed(1)}h
                          </td>
                          <td className="py-2 text-right text-sm text-success">
                            {formatPercentage(subcat.resolutionRate)}
                          </td>
                          <td className="py-2"></td>
                        </tr>
                      ))
                    )}
                  </>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>

        {(!categories || categories.length === 0) && (
          <div className="text-center py-8 text-muted-foreground">
            No category data available for the selected period
          </div>
        )}
      </div>
    </div>
  )
}
