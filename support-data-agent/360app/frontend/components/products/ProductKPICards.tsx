import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatNumber, formatPercentage } from '@/lib/utils';

interface MetricValue {
  value: number;
  changeType: 'increase' | 'decrease' | 'neutral';
  changePercentage: number;
}

interface ProductKPICardsProps {
  totalCases: MetricValue;
  avgCaseLife: MetricValue;
  resolutionRate: MetricValue;
}

export function ProductKPICards({ totalCases, avgCaseLife, resolutionRate }: ProductKPICardsProps) {
  const getTrendIcon = (changeType: string) => {
    switch (changeType) {
      case 'increase':
        return <TrendingUp className="w-4 h-4" />
      case 'decrease':
        return <TrendingDown className="w-4 h-4" />
      default:
        return <Minus className="w-4 h-4" />
    }
  }

  const getTrendColor = (changeType: string, metricType: 'cases' | 'time' | 'rate') => {
    if (changeType === 'neutral') return 'text-muted-foreground';

    if (metricType === 'rate') {
      // Higher rate = better
      return changeType === 'increase' ? 'text-success' : 'text-error';
    } else {
      // Lower cases/time = better
      return changeType === 'decrease' ? 'text-success' : 'text-error';
    }
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      {/* Total Cases */}
      <div className="bg-card border border-border rounded-lg p-6 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between mb-2">
          <div className="text-sm font-medium text-muted-foreground">Total Cases</div>
          <div className={cn(
            'flex items-center gap-1',
            getTrendColor(totalCases.changeType, 'cases')
          )}>
            {getTrendIcon(totalCases.changeType)}
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <div className="text-3xl font-bold text-foreground">
            {formatNumber(totalCases.value)}
          </div>
          <div className={cn(
            'text-sm font-medium',
            getTrendColor(totalCases.changeType, 'cases')
          )}>
            {totalCases.changePercentage > 0 ? '+' : ''}
            {totalCases.changePercentage}%
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          vs. previous period
        </div>
      </div>

      {/* Avg Resolution Time */}
      <div className="bg-card border border-border rounded-lg p-6 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between mb-2">
          <div className="text-sm font-medium text-muted-foreground">Avg Resolution Time</div>
          <div className={cn(
            'flex items-center gap-1',
            getTrendColor(avgCaseLife.changeType, 'time')
          )}>
            {getTrendIcon(avgCaseLife.changeType)}
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <div className="text-3xl font-bold text-foreground">
            {avgCaseLife.value.toFixed(1)}h
          </div>
          <div className={cn(
            'text-sm font-medium',
            getTrendColor(avgCaseLife.changeType, 'time')
          )}>
            {avgCaseLife.changePercentage > 0 ? '+' : ''}
            {avgCaseLife.changePercentage}%
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          {avgCaseLife.changeType === 'decrease' ? 'Faster ✓' :
           avgCaseLife.changeType === 'increase' ? 'Slower ⚠' : 'Stable'}
        </div>
      </div>

      {/* Resolution Rate */}
      <div className="bg-card border border-border rounded-lg p-6 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between mb-2">
          <div className="text-sm font-medium text-muted-foreground">Resolution Rate</div>
          <div className={cn(
            'flex items-center gap-1',
            getTrendColor(resolutionRate.changeType, 'rate')
          )}>
            {getTrendIcon(resolutionRate.changeType)}
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <div className="text-3xl font-bold text-success">
            {formatPercentage(resolutionRate.value)}
          </div>
          <div className={cn(
            'text-sm font-medium',
            getTrendColor(resolutionRate.changeType, 'rate')
          )}>
            {resolutionRate.changePercentage > 0 ? '+' : ''}
            {resolutionRate.changePercentage}%
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          {resolutionRate.value >= 80 ? 'Excellent ✓' :
           resolutionRate.value >= 60 ? 'Good' : 'Needs attention ⚠'}
        </div>
      </div>
    </div>
  );
}
