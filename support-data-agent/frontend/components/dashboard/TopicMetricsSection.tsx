'use client'

import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber, formatPercentage } from '@/lib/utils'
import { TopicMetrics } from '@/types'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export function TopicMetricsSection() {
  const { filters, activeConfigId } = useAppStore()

  const { data: topics, isLoading } = useQuery({
    queryKey: ['topic-metrics', filters],
    queryFn: () => dashboardApi.getTopicMetrics(filters),
    enabled: !!activeConfigId,
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Topic Metrics</h2>
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

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">Topic Metrics</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4">
        {topics?.map((topic: TopicMetrics) => (
          <div
            key={topic.topicId}
            className="bg-background border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
          >
            {/* Header */}
            <div className="mb-3 pb-3 border-b border-border">
              <h3 className="font-semibold text-foreground text-sm">{topic.topicName}</h3>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-2xl font-bold text-primary">
                  {formatNumber(topic.totalCases)}
                </span>
                <div className="flex items-center gap-1">
                  {getTrendIcon(topic.changeType)}
                  <span className={`text-xs font-medium ${getTrendColor(topic.changeType)}`}>
                    {topic.changePercentage > 0 ? '+' : ''}{topic.changePercentage}%
                  </span>
                </div>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <div className="text-sm font-semibold text-foreground">
                  {topic.avgResolutionTime.toFixed(1)}h
                </div>
                <div className="text-xs text-muted-foreground">Avg Time</div>
              </div>
              <div>
                <div className="text-sm font-semibold text-success">
                  {formatPercentage(topic.resolutionRate)}
                </div>
                <div className="text-xs text-muted-foreground">Resolved</div>
              </div>
            </div>

            {/* Sentiment Bar */}
            <div className="mb-3">
              <div className="text-xs text-muted-foreground mb-1">Sentiment</div>
              <div className="flex gap-1 h-2 rounded overflow-hidden">
                <div
                  className="bg-success"
                  style={{ width: `${topic.sentiment.positive}%` }}
                  title={`${topic.sentiment.positive}% Positive`}
                />
                <div
                  className="bg-muted"
                  style={{ width: `${topic.sentiment.neutral}%` }}
                  title={`${topic.sentiment.neutral}% Neutral`}
                />
                <div
                  className="bg-error"
                  style={{ width: `${topic.sentiment.negative}%` }}
                  title={`${topic.sentiment.negative}% Negative`}
                />
              </div>
            </div>

            {/* Top Products */}
            {topic.topProducts.length > 0 && (
              <div className="pt-3 border-t border-border">
                <div className="text-xs font-medium text-muted-foreground mb-1">Top Products</div>
                <div className="space-y-1">
                  {topic.topProducts.slice(0, 2).map((prod, idx) => (
                    <div key={idx} className="flex justify-between items-center text-xs">
                      <span className="text-foreground truncate flex-1">{prod.product}</span>
                      <span className="text-muted-foreground ml-2">{prod.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
