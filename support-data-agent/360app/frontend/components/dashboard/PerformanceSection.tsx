'use client'

import { PerformanceCard, PerformanceItem } from './PerformanceCard'

interface PerformanceSectionProps {
  title: string
  topLabel: string
  bottomLabel: string
  topItems: PerformanceItem[]
  bottomItems: PerformanceItem[]
  metricType: 'caseVolume' | 'resolutionTime' | 'resolutionRate'
  icon?: React.ReactNode
}

export function PerformanceSection({
  title,
  topLabel,
  bottomLabel,
  topItems,
  bottomItems,
  metricType,
  icon,
}: PerformanceSectionProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-4">
        {icon && <div className="text-primary">{icon}</div>}
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-2 gap-4">
        {/* Top Performers */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-3">{topLabel}</h4>
          <div className="space-y-2">
            {topItems.map((item) => (
              <PerformanceCard
                key={item.id}
                item={item}
                metricType={metricType}
                isTopPerformer={true}
              />
            ))}
          </div>
        </div>

        {/* Bottom Performers */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-3">{bottomLabel}</h4>
          <div className="space-y-2">
            {bottomItems.map((item) => (
              <PerformanceCard
                key={item.id}
                item={item}
                metricType={metricType}
                isTopPerformer={false}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
