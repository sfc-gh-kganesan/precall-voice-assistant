'use client'

import { cn } from '@/lib/utils'
import type { HighValueCustomer } from '@/types'

interface CustomerUsageCardProps {
  customer: HighValueCustomer
  rank: number
}

export function CustomerUsageCard({ customer, rank }: CustomerUsageCardProps) {
  // Determine priority indicator based on usage + cases
  const getPriorityIndicator = () => {
    if (customer.cases_last_30_days >= 5) {
      return '🔴' // High activity + many cases
    }
    if (customer.cases_last_30_days > 0) {
      return '🟡' // Has some cases
    }
    return '🟢' // Healthy - no recent cases
  }

  return (
    <div className="bg-background border rounded-lg p-3 hover:bg-accent/20 transition-colors">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-base flex-shrink-0">{getPriorityIndicator()}</span>
          <span className="text-xs font-medium text-muted-foreground flex-shrink-0">#{rank}</span>
          <h4 className="font-medium text-sm text-foreground truncate">{customer.salesforce_account_name}</h4>
        </div>

        <div className="flex items-center gap-4 flex-shrink-0">
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Active Rows</div>
            <div className="text-sm font-medium text-foreground">
              {(customer.total_active_serving_rows / 1000000).toFixed(0)}M
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Cases (30d)</div>
            <div className={cn(
              "text-sm font-medium",
              customer.cases_last_30_days >= 5 ? "text-error" :
              customer.cases_last_30_days > 0 ? "text-warning" :
              "text-success"
            )}>
              {customer.cases_last_30_days}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
