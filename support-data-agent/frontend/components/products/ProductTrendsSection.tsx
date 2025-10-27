'use client'

import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { TrendingUp, Clock, CheckCircle } from 'lucide-react'

export function ProductTrendsSection() {
  const { filters, activeConfigId } = useAppStore()

  const { data, isLoading } = useQuery({
    queryKey: ['product-performance', filters],
    queryFn: () => dashboardApi.getProductPerformance(filters),
    enabled: !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Product Trends</h2>
        <LoadingSpinner size="lg" className="h-64" />
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className="h-full flex flex-col">
      <div className="mb-3">
        <h2 className="text-lg font-bold text-foreground mb-1">Product Trends</h2>
        <p className="text-xs text-muted-foreground">
          Issues requiring attention
        </p>
      </div>

      {/* Single consolidated card with flex-1 to fill remaining height */}
      <div className="bg-card border border-border rounded-lg p-3 flex-1 flex flex-col justify-between">
        {/* Case Volume Increases */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-primary" />
            <h3 className="text-xs font-semibold text-foreground">Case Volume Increases</h3>
          </div>
          {data.caseVolume.topPerformers.slice(0, 1).map((item) => (
            <div key={item.id} className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="font-medium text-foreground truncate">{item.name}</span>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground text-[10px] truncate">{item.category}</span>
              </div>
              <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                <span className="text-error font-medium">{item.changePercentage > 0 ? '+' : ''}{item.changePercentage}%</span>
                <span className="text-muted-foreground">{item.value}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Slowest Resolution Times */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Clock className="w-3.5 h-3.5 text-primary" />
            <h3 className="text-xs font-semibold text-foreground">Slowest Resolution Times</h3>
          </div>
          {data.resolutionTime.topPerformers.slice(0, 1).map((item) => (
            <div key={item.id} className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="font-medium text-foreground truncate">{item.name}</span>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground text-[10px] truncate">{item.category}</span>
              </div>
              <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                <span className="text-error font-medium">{item.changePercentage > 0 ? '+' : ''}{item.changePercentage}%</span>
                <span className="text-muted-foreground">{item.value}h</span>
              </div>
            </div>
          ))}
        </div>

        {/* Lowest Resolution Rates */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <CheckCircle className="w-3.5 h-3.5 text-primary" />
            <h3 className="text-xs font-semibold text-foreground">Lowest Resolution Rates</h3>
          </div>
          {data.resolutionRate.bottomPerformers.slice(0, 1).map((item) => (
            <div key={item.id} className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="font-medium text-foreground truncate">{item.name}</span>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground text-[10px] truncate">{item.category}</span>
              </div>
              <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                <span className="text-error font-medium">{item.changePercentage > 0 ? '+' : ''}{item.changePercentage}%</span>
                <span className="text-muted-foreground">{item.value}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

