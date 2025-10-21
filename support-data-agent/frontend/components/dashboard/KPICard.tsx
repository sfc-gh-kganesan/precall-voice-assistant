'use client'

import { KPIMetric } from '@/types'
import { formatNumber, formatPercentage, formatDuration, getTrendInfo } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface KPICardProps {
  metric: KPIMetric
  className?: string
}

export function KPICard({ metric, className }: KPICardProps) {
  const { arrow, className: trendClass } = getTrendInfo(metric.changeType)

  // Format value based on unit
  const formatValue = (value: number) => {
    if (metric.unit === '%') return formatPercentage(value, 1)
    if (metric.unit === 'hours') return formatDuration(value)
    return formatNumber(value)
  }

  return (
    <div className={cn('bg-card border border-border rounded-lg p-6', className)}>
      <div className="space-y-2">
        {/* Large metric value */}
        <div className="text-4xl font-bold text-foreground">
          {formatValue(metric.value)}
        </div>

        {/* Metric label */}
        <div className="text-sm text-muted-foreground">
          {metric.name}
        </div>

        {/* Change indicator */}
        <div className="flex items-center gap-1">
          <span className={cn('text-sm', trendClass)}>
            {arrow} {formatPercentage(Math.abs(metric.changePercentage), 1)}
          </span>
          <span className="text-xs text-muted-foreground">
            {metric.comparisonPeriod}
          </span>
        </div>
      </div>
    </div>
  )
}
