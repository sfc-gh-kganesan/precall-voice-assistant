'use client'

import { useState } from 'react'
import { Filters } from '@/types'
import { useAppStore } from '@/stores/appStore'
import { cn } from '@/lib/utils'

interface FilterBarProps {
  className?: string
}

export function FilterBar({ className }: FilterBarProps) {
  const { filters, setFilters } = useAppStore()
  const [isExpanded, setIsExpanded] = useState(false)

  const handlePeriodChange = (period: Filters['period']) => {
    setFilters({ period })
  }

  return (
    <div className={cn('bg-card border border-border rounded-lg p-4', className)}>
      <div className="flex items-center justify-between">
        {/* Time Period Selector */}
        <div className="flex gap-2">
          {(['week', 'month'] as const).map((period) => (
            <button
              key={period}
              onClick={() => handlePeriodChange(period)}
              className={cn(
                'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                filters.period === period
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              )}
            >
              {period === 'week' ? 'This Week' : 'This Month'}
            </button>
          ))}
        </div>

        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {isExpanded ? 'Hide' : 'Show'} Filters
        </button>
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Product Filter */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                Products
              </label>
              <select
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
                multiple
                size={3}
                value={filters.products || []}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value)
                  setFilters({ products: selected })
                }}
              >
                <option value="snowflake-db">Snowflake Database</option>
                <option value="snowpark">Snowpark</option>
                <option value="snowpipe">Snowpipe</option>
              </select>
            </div>

            {/* Topic Filter */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                Topics
              </label>
              <select
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
                multiple
                size={3}
                value={filters.topics || []}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value)
                  setFilters({ topics: selected })
                }}
              >
                <option value="performance">Performance</option>
                <option value="connectivity">Connectivity</option>
                <option value="security">Security</option>
              </select>
            </div>

            {/* Category Filter */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                Categories
              </label>
              <select
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
                multiple
                size={3}
                value={filters.categories || []}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value)
                  setFilters({ categories: selected })
                }}
              >
                <option value="core-platform">Core Platform</option>
                <option value="data-cloud">Data Cloud</option>
                <option value="ai-ml">AI/ML</option>
              </select>
            </div>
          </div>

          {/* Reset Filters */}
          <div className="mt-4 flex justify-end">
            <button
              onClick={() => useAppStore.getState().resetFilters()}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Reset Filters
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
