'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { usageApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface UsageTrendsSectionProps {
  productName: string
  caseVolumeTrend?: Array<{ date: string; value: number }>
}

export function UsageTrendsSection({ productName, caseVolumeTrend }: UsageTrendsSectionProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  // Note: Backend queries are already product-specific (e.g., cortex_search_* tables)
  // We show ALL accounts using this product, not filtering by account name
  const { data: timeline, isLoading: timelineLoading } = useQuery({
    queryKey: ['usage-credits-timeline', productName],
    queryFn: () => usageApi.getCreditsTimeline(),
  })

  const { data: movers, isLoading: moversLoading } = useQuery({
    queryKey: ['usage-biggest-movers', productName],
    queryFn: () => usageApi.getBiggestMovers({ period: '7d' }),
  })

  if (timelineLoading || moversLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
  }

  // Prepare data for line chart (always 30 days)
  const chartData = timeline && timeline.length > 0
    ? timeline.slice(0, 30).reverse()
    : []

  const maxCredits = chartData.length > 0 ? Math.max(...chartData.map(p => p.credits)) : 0
  const minCredits = chartData.length > 0 ? Math.min(...chartData.map(p => p.credits)) : 0

  // Generate SVG path for line chart
  const generatePath = () => {
    if (chartData.length === 0) return ''

    const width = 100 // percentage
    const height = 100 // percentage
    const points = chartData.map((point, idx) => {
      const x = (idx / (chartData.length - 1)) * width
      const y = height - ((point.credits - minCredits) / (maxCredits - minCredits)) * height
      return `${x},${y}`
    })

    return `M ${points.join(' L ')}`
  }

  // Handle mouse move to find nearest point
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const xPercent = (x / rect.width) * 100

    // Find nearest data point
    const nearestIndex = Math.round((xPercent / 100) * (chartData.length - 1))
    const clampedIndex = Math.max(0, Math.min(chartData.length - 1, nearestIndex))
    setHoveredIndex(clampedIndex)
  }

  const handleMouseLeave = () => {
    setHoveredIndex(null)
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      {/* Header */}
      <h3 className="text-lg font-bold text-foreground mb-4">Usage & Support Trends</h3>

      {/* Credits Timeline - Line Chart (Full Width) */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-foreground">Credits Trend (30 days)</h4>
        </div>
        <div className="bg-background border border-border rounded-lg p-4">
          {chartData.length > 0 ? (
            <div
              className="relative cursor-crosshair"
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
              {/* SVG Line Chart */}
              <svg
                viewBox="0 0 100 100"
                className="w-full h-32"
                preserveAspectRatio="none"
              >
                {/* Area fill under line */}
                <defs>
                  <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="rgb(59, 130, 246)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="rgb(59, 130, 246)" stopOpacity="0.05" />
                  </linearGradient>
                </defs>

                {/* Area */}
                <path
                  d={`${generatePath()} L 100,100 L 0,100 Z`}
                  fill="url(#areaGradient)"
                />

                {/* Line */}
                <path
                  d={generatePath()}
                  fill="none"
                  stroke="rgb(59, 130, 246)"
                  strokeWidth="0.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              </svg>

              {/* Hover elements (HTML/CSS, not SVG) */}
              {hoveredIndex !== null && (
                <>
                  {/* Vertical crosshair line */}
                  <div
                    className="absolute top-0 bottom-0 w-px bg-primary/50 pointer-events-none"
                    style={{
                      left: `${(hoveredIndex / (chartData.length - 1)) * 100}%`,
                    }}
                  />

                  {/* Data point circle */}
                  <div
                    className="absolute w-2 h-2 rounded-full bg-primary border-2 border-background pointer-events-none"
                    style={{
                      left: `${(hoveredIndex / (chartData.length - 1)) * 100}%`,
                      top: `${(1 - (chartData[hoveredIndex].credits - minCredits) / (maxCredits - minCredits)) * 100}%`,
                      transform: 'translate(-50%, -50%)',
                    }}
                  />

                  {/* Tooltip */}
                  <div
                    className="absolute bg-popover border border-border px-3 py-2 rounded-lg shadow-lg pointer-events-none z-10 whitespace-nowrap"
                    style={{
                      left: `${(hoveredIndex / (chartData.length - 1)) * 100}%`,
                      top: `${(1 - (chartData[hoveredIndex].credits - minCredits) / (maxCredits - minCredits)) * 100}%`,
                      transform: 'translate(-50%, -100%)',
                      marginTop: '-12px',
                    }}
                  >
                    <div className="text-sm font-semibold text-foreground">
                      {chartData[hoveredIndex].credits.toLocaleString()} credits
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(chartData[hoveredIndex].ds).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </div>
                  </div>
                </>
              )}

              {/* X-axis labels */}
              <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                <span>{new Date(chartData[0].ds).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                <span>{new Date(chartData[chartData.length - 1].ds).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              </div>
            </div>
          ) : (
            <div className="h-32 flex items-center justify-center text-sm text-muted-foreground">
              No usage data available
            </div>
          )}
        </div>
      </div>

      {/* 7D Biggest Movers - Side by Side */}
      <div className="grid grid-cols-2 gap-4">
        {/* Top Gainers - Left Column */}
        <div>
          <div className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-success" />
            Top Gainers
          </div>
          {movers?.gainers && movers.gainers.length > 0 ? (
            <div className="space-y-2">
              {movers.gainers.slice(0, 3).map((mover, idx) => (
                <div
                  key={idx}
                  className="bg-background border border-border rounded-lg px-3 py-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground truncate flex-1">{mover.salesforce_account_name}</span>
                    <span className="text-sm font-medium text-success ml-2">
                      {mover.pct_change !== null ? `+${(mover.pct_change * 100).toFixed(0)}%` : 'N/A'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">No gainers data</div>
          )}
        </div>

        {/* Top Decliners - Right Column */}
        <div>
          <div className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-error" />
            Top Decliners
          </div>
          {movers?.decliners && movers.decliners.length > 0 ? (
            <div className="space-y-2">
              {movers.decliners.slice(0, 3).map((mover, idx) => (
                <div
                  key={idx}
                  className="bg-background border border-border rounded-lg px-3 py-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground truncate flex-1">{mover.salesforce_account_name}</span>
                    <span className="text-sm font-medium text-error ml-2">
                      {mover.pct_change !== null ? `${(mover.pct_change * 100).toFixed(0)}%` : 'N/A'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">No decliners data</div>
          )}
        </div>
      </div>

      {/* Case Volume Trend */}
      {caseVolumeTrend && caseVolumeTrend.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border">
          <h4 className="text-sm font-medium text-foreground mb-3">📈 Case Volume Trend</h4>
          <div className="bg-background border border-border rounded-lg p-4">
            <div className="h-32 flex items-end gap-1">
              {caseVolumeTrend.map((point, idx) => {
                const maxValue = Math.max(...caseVolumeTrend.map(p => p.value))
                const height = maxValue > 0 ? (point.value / maxValue) * 100 : 0
                return (
                  <div
                    key={idx}
                    className="flex-1 bg-primary/70 rounded-t hover:bg-primary transition-colors relative group"
                    style={{ height: `${height}%`, minHeight: '4px' }}
                  >
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-popover border border-border px-2 py-1 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                      {point.value} cases<br/>
                      {new Date(point.date).toLocaleDateString()}
                    </div>
                  </div>
                )
              })}
            </div>
            <div className="flex justify-between mt-3 text-xs text-muted-foreground">
              <span>{new Date(caseVolumeTrend[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              <span>{new Date(caseVolumeTrend[caseVolumeTrend.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
