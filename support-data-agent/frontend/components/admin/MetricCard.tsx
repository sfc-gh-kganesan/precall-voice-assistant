'use client'

import { formatNumber } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: {
    value: number
    direction: 'up' | 'down' | 'neutral'
    isPositive?: boolean
  }
  icon?: string
  variant?: 'default' | 'success' | 'warning' | 'error'
}

const VARIANT_STYLES = {
  default: 'bg-card border-border',
  success: 'bg-success/5 border-success/20',
  warning: 'bg-warning/5 border-warning/20',
  error: 'bg-error/5 border-error/20',
}

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  variant = 'default',
}: MetricCardProps) {
  const formattedValue = typeof value === 'number' ? formatNumber(value) : value

  return (
    <div className={`border rounded-lg p-4 ${VARIANT_STYLES[variant]}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon && <span className="text-lg">{icon}</span>}
          <h3 className="text-xs font-medium text-muted-foreground uppercase">
            {title}
          </h3>
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-xs font-medium ${
              trend.isPositive !== false
                ? trend.direction === 'up'
                  ? 'text-success'
                  : trend.direction === 'down'
                  ? 'text-error'
                  : 'text-muted-foreground'
                : trend.direction === 'up'
                ? 'text-error'
                : trend.direction === 'down'
                ? 'text-success'
                : 'text-muted-foreground'
            }`}
          >
            {trend.direction === 'up' && '↑'}
            {trend.direction === 'down' && '↓'}
            {trend.direction === 'neutral' && '→'}
            {Math.abs(trend.value)}%
          </div>
        )}
      </div>

      {/* Value */}
      <div className="mb-1">
        <div className="text-2xl font-bold text-foreground">{formattedValue}</div>
      </div>

      {/* Subtitle */}
      {subtitle && (
        <div className="text-xs text-muted-foreground">{subtitle}</div>
      )}
    </div>
  )
}
