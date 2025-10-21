'use client'

import { TrendingUp, TrendingDown } from 'lucide-react'
import { formatNumber, formatPercentage, cn } from '@/lib/utils'

export interface PerformanceItem {
  id: string
  name: string
  category: string
  currentValue: number
  previousValue: number
  changeAbsolute: number
  changePercentage: number
}

interface PerformanceCardProps {
  item: PerformanceItem
  metricType: 'caseVolume' | 'resolutionTime' | 'resolutionRate'
  isTopPerformer?: boolean
}

export function PerformanceCard({ item, metricType, isTopPerformer }: PerformanceCardProps) {
  // Determine colors and icons based on metric type and change direction
  const getMetricConfig = () => {
    const isIncrease = item.changePercentage > 0

    switch (metricType) {
      case 'caseVolume':
        return {
          color: isIncrease ? 'text-error' : 'text-success',
          icon: isIncrease ? TrendingUp : TrendingDown,
          valueFormatter: (val: number) => formatNumber(val),
        }
      case 'resolutionTime':
        return {
          color: isIncrease ? 'text-error' : 'text-success',
          icon: isIncrease ? TrendingUp : TrendingDown,
          valueFormatter: (val: number) => val.toFixed(1),
        }
      case 'resolutionRate':
        return {
          color: isIncrease ? 'text-success' : 'text-error',
          icon: isIncrease ? TrendingUp : TrendingDown,
          valueFormatter: (val: number) => formatPercentage(val),
        }
    }
  }

  const config = getMetricConfig()
  const Icon = config.icon

  return (
    <div className={`h-[68px] bg-card border border-border rounded-md p-2 hover:bg-accent/5 transition-colors flex justify-between items-center gap-3 ${isTopPerformer ? '' : ''}`}>
      {/* Left: Name + Category */}
      <div className="flex flex-col flex-1 min-w-0">
        <span
          className="font-semibold text-foreground text-xs line-clamp-2 leading-tight"
          title={item.name}
        >
          {item.name}
        </span>
        <span className="text-xs text-muted-foreground truncate leading-tight">
          {item.category}
        </span>
      </div>

      {/* Right: Icon + % (top), Value (bottom) */}
      <div className="flex flex-col items-end shrink-0">
        <div className="flex items-center gap-1.5 text-xs">
          <Icon className={cn('w-3 h-3 flex-shrink-0', config.color)} />
          <span className={cn('flex-shrink-0', config.color)}>
            {item.changePercentage > 0 ? '+' : ''}
            {item.changePercentage.toFixed(1)}%
          </span>
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {config.valueFormatter(item.currentValue)}
        </span>
      </div>
    </div>
  )
}
