'use client'

import { useQuery } from '@tanstack/react-query'
import { usageApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { CustomerUsageCard } from './CustomerUsageCard'
import type { HighValueCustomer } from '@/types'

interface HighValueCustomersProps {
  productName: string
}

export function HighValueCustomers({ productName }: HighValueCustomersProps) {
  // Note: Backend queries are already product-specific (e.g., cortex_search_* tables)
  // We show ALL accounts using this product, ranked by usage
  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['usage-top-accounts', productName],
    queryFn: () => usageApi.getTopAccounts(),
  })

  const { data: caseCounts, isLoading: casesLoading } = useQuery({
    queryKey: ['usage-case-counts', productName],
    queryFn: () => usageApi.getCaseCounts({ product_name: productName, days: 30 }),
  })

  if (accountsLoading || casesLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-foreground mb-4">High-Value Customers</h3>
        <LoadingSpinner size="md" className="h-48" />
      </div>
    )
  }

  // Transform and merge data
  const customers: HighValueCustomer[] = accounts?.map((account) => ({
    salesforce_account_name: account.salesforce_account_name,
    salesforce_account_id: account.salesforce_account_id,
    total_active_serving_rows: account.total_active_serving_rows,
    cases_last_30_days: caseCounts?.[account.salesforce_account_name] || 0,
  })) || []

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-foreground">💎 High-Value Customers</h3>
        <span className="text-xs text-muted-foreground">
          Prioritized by usage + issues
        </span>
      </div>

      {customers.length > 0 ? (
        <>
          <div className="space-y-2">
            {customers.slice(0, 5).map((customer, idx) => (
              <CustomerUsageCard
                key={customer.salesforce_account_id}
                customer={customer}
                rank={idx + 1}
              />
            ))}
          </div>
          {customers.length > 5 && (
            <div className="mt-4 text-center">
              <button className="text-sm text-primary hover:text-primary/80 hover:underline transition-colors">
                View all {customers.length} customers →
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          No customer usage data available
        </div>
      )}
    </div>
  )
}
