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
import { TopicMetrics } from '@/types'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { TopicPerformanceSection } from '@/components/dashboard/TopicPerformanceSection'

export default function TopicsPage() {
  const [period, setPeriod] = useState<'week' | 'month'>('week')
  const [sortBy, setSortBy] = useState<'cases' | 'resolution'>('cases')
  const configId = useAppStore((state) => state.activeConfigId)
  const isInitializing = useAppStore((state) => state.isInitializing)
  const setFilters = useAppStore((state) => state.setFilters)

  useEffect(() => {
    setFilters({ period })
  }, [period, setFilters])

  const { data: topics, isLoading } = useQuery({
    queryKey: ['topic-metrics', period],
    queryFn: () => dashboardApi.getTopicMetrics({ period }),
    enabled: !!configId,
  })

  const sortedTopics = [...(topics || [])].sort((a, b) => {
    if (sortBy === 'cases') {
      return b.totalCases - a.totalCases
    }
    return b.resolutionRate - a.resolutionRate
  })

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
                  Topic Analysis
                </h1>
                <p className="text-xs text-muted-foreground">Powered by Snowflake</p>
              </div>
            </div>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </Link>
              <Link href="/products" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Products
              </Link>
              <Link href="/topics" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
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
            {/* Topic Trends - Always visible at top */}
            <div className="mb-8">
              <TopicPerformanceSection />
            </div>

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
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'cases' | 'resolution')}
            className="px-4 py-2 bg-card border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="cases">Sort by Case Volume</option>
            <option value="resolution">Sort by Resolution Rate</option>
          </select>
        </div>

        {/* Overview Stats */}
        {!isLoading && topics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="text-sm text-muted-foreground mb-1">Total Topics</div>
              <div className="text-2xl font-bold text-foreground">{topics.length}</div>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="text-sm text-muted-foreground mb-1">Total Cases</div>
              <div className="text-2xl font-bold text-primary">
                {formatNumber(topics.reduce((sum, t) => sum + t.totalCases, 0))}
              </div>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="text-sm text-muted-foreground mb-1">Avg Resolution Rate</div>
              <div className="text-2xl font-bold text-success">
                {formatPercentage(topics.reduce((sum, t) => sum + t.resolutionRate, 0) / topics.length)}
              </div>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="text-sm text-muted-foreground mb-1">Avg Resolution Time</div>
              <div className="text-2xl font-bold text-foreground">
                {(topics.reduce((sum, t) => sum + t.avgResolutionTime, 0) / topics.length).toFixed(1)}h
              </div>
            </div>
          </div>
        )}

        {/* Topics List */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <div className="space-y-4">
            {sortedTopics?.map((topic: TopicMetrics) => (
              <div
                key={topic.topicId}
                className="bg-card border border-border rounded-lg p-6 hover:border-primary/50 transition-colors"
              >
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left: Topic Info */}
                  <div className="lg:col-span-1">
                    <div className="mb-4">
                      <h3 className="text-lg font-bold text-foreground mb-2">{topic.topicName}</h3>
                      <div className="flex items-center gap-3">
                        <div>
                          <div className="text-3xl font-bold text-primary">
                            {formatNumber(topic.totalCases)}
                          </div>
                          <div className="text-xs text-muted-foreground">Cases</div>
                        </div>
                        <div className="flex items-center gap-1">
                          {getTrendIcon(topic.changeType)}
                          <span className={cn('text-sm font-medium', getTrendColor(topic.changeType))}>
                            {topic.changePercentage > 0 ? '+' : ''}{topic.changePercentage}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Sentiment */}
                    <div>
                      <div className="text-sm font-medium text-muted-foreground mb-2">Sentiment Distribution</div>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="w-full bg-background rounded-full h-2">
                            <div
                              className="bg-success h-2 rounded-full"
                              style={{ width: `${topic.sentiment.positive}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground w-12 text-right">
                            {topic.sentiment.positive}%
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-full bg-background rounded-full h-2">
                            <div
                              className="bg-muted h-2 rounded-full"
                              style={{ width: `${topic.sentiment.neutral}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground w-12 text-right">
                            {topic.sentiment.neutral}%
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-full bg-background rounded-full h-2">
                            <div
                              className="bg-error h-2 rounded-full"
                              style={{ width: `${topic.sentiment.negative}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground w-12 text-right">
                            {topic.sentiment.negative}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Middle: Metrics */}
                  <div className="lg:col-span-1 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-background border border-border rounded-lg p-4">
                        <div className="text-sm text-muted-foreground mb-1">Avg Resolution</div>
                        <div className="text-xl font-bold text-foreground">
                          {topic.avgResolutionTime.toFixed(1)}h
                        </div>
                      </div>
                      <div className="bg-background border border-border rounded-lg p-4">
                        <div className="text-sm text-muted-foreground mb-1">Resolution Rate</div>
                        <div className="text-xl font-bold text-success">
                          {formatPercentage(topic.resolutionRate)}
                        </div>
                      </div>
                    </div>

                    {/* Comparison Bars */}
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-xs text-muted-foreground mb-1">
                          <span>Volume vs Avg</span>
                          <span>{sortedTopics ? Math.round((topic.totalCases / (sortedTopics.reduce((sum, t) => sum + t.totalCases, 0) / sortedTopics.length)) * 100) : 0}%</span>
                        </div>
                        <div className="w-full bg-background rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, sortedTopics ? (topic.totalCases / (sortedTopics.reduce((sum, t) => sum + t.totalCases, 0) / sortedTopics.length)) * 100 : 0)}%`
                            }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs text-muted-foreground mb-1">
                          <span>Resolution vs Avg</span>
                          <span>{sortedTopics ? Math.round((topic.resolutionRate / (sortedTopics.reduce((sum, t) => sum + t.resolutionRate, 0) / sortedTopics.length)) * 100) : 0}%</span>
                        </div>
                        <div className="w-full bg-background rounded-full h-2">
                          <div
                            className="bg-success h-2 rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, sortedTopics ? (topic.resolutionRate / (sortedTopics.reduce((sum, t) => sum + t.resolutionRate, 0) / sortedTopics.length)) * 100 : 0)}%`
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right: Top Products */}
                  <div className="lg:col-span-1">
                    <h4 className="text-sm font-medium text-muted-foreground mb-3">Most Affected Products</h4>
                    <div className="space-y-3">
                      {topic.topProducts.map((prod, idx) => (
                        <div key={idx} className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center text-sm font-bold flex-shrink-0">
                            {idx + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-foreground truncate">
                              {prod.product}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {prod.count} cases
                            </div>
                          </div>
                          <div className="flex-shrink-0">
                            <div className="w-16 bg-background rounded-full h-2">
                              <div
                                className="bg-primary h-2 rounded-full"
                                style={{
                                  width: `${topic.topProducts.length > 0 ? (prod.count / topic.topProducts[0].count) * 100 : 0}%`
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && sortedTopics?.length === 0 && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No topics found for the selected period.</p>
          </div>
        )}
        </>
      )}
      </main>
    </div>
  )
}
