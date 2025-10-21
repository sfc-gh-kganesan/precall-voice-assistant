'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ticketsApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SnowflakeLogo } from '@/components/ui/SnowflakeLogo'
import { NoConfigurationAlert } from '@/components/common/NoConfigurationAlert'
import { useAppStore } from '@/stores/appStore'
import { TicketRow } from '@/components/tickets/TicketRow'
import { X } from 'lucide-react'

export default function TicketsPage() {
  const searchParams = useSearchParams()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [productFilter, setProductFilter] = useState<string | null>(null)
  const configId = useAppStore((state) => state.activeConfigId)
  const isInitializing = useAppStore((state) => state.isInitializing)

  // Read product filter from URL on mount
  useEffect(() => {
    const product = searchParams.get('product')
    if (product) {
      setProductFilter(product)
    }
  }, [searchParams])

  const { data, isLoading } = useQuery({
    queryKey: ['tickets', page, pageSize, sortBy, sortOrder, productFilter],
    queryFn: () => ticketsApi.getTickets({
      page,
      pageSize,
      sortBy,
      sortOrder,
      ...(productFilter && { product: productFilter })
    }),
    enabled: !!configId,
  })

  const handleSort = (column: string) => {
    if (sortBy === column) {
      // Toggle sort order if clicking the same column
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      // Set new column and default to descending
      setSortBy(column)
      setSortOrder('desc')
    }
    // Reset to first page when sorting changes
    setPage(1)
  }

  const renderSortIcon = (column: string) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc' ? ' ↑' : ' ↓'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Closed':
      case 'Solution Provided':
        return 'bg-success/20 text-success'
      case 'In Progress':
        return 'bg-primary/20 text-primary'
      case 'Awaiting Customer':
        return 'bg-warning/20 text-warning'
      case 'Escalated':
        return 'bg-error/20 text-error'
      case 'New':
        return 'bg-muted text-muted-foreground'
      default:
        return 'bg-muted text-muted-foreground'
    }
  }

  const getSeverityColor = (severity: string) => {
    if (severity.startsWith('Severity-1')) {
      return 'text-error'
    } else if (severity.startsWith('Severity-2')) {
      return 'text-warning'
    } else if (severity.startsWith('Severity-3')) {
      return 'text-primary'
    } else if (severity.startsWith('Severity-4')) {
      return 'text-muted-foreground'
    }
    return 'text-muted-foreground'
  }

  const getSeverityLabel = (severity: string) => {
    if (severity.startsWith('Severity-1')) return 'Severity-1'
    if (severity.startsWith('Severity-2')) return 'Severity-2'
    if (severity.startsWith('Severity-3')) return 'Severity-3'
    if (severity.startsWith('Severity-4')) return 'Severity-4'
    return severity
  }

  const filteredTickets = data?.tickets.filter(ticket =>
    searchTerm === '' ||
    ticket.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ticket.case_number.toLowerCase().includes(searchTerm.toLowerCase())
  )

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
                  Support Cases
                </h1>
                <p className="text-xs text-muted-foreground">Powered by Snowflake</p>
              </div>
            </div>
            <nav className="flex gap-6">
              <a href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </a>
              <a href="/products" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Products
              </a>
              <a href="/topics" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Topics
              </a>
              <a href="/tickets" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
                Cases
              </a>
              <a href="/admin" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Admin
              </a>
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
            {/* Search Bar */}
            <div className="mb-6">
              <input
                type="text"
                placeholder="Search cases by case number or title..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-card border border-border rounded-md px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Active Filter Indicator */}
            {productFilter && (
              <div className="mb-4 flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Active filter:</span>
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 rounded-full">
                  <span className="text-sm font-medium text-primary">
                    Product: {productFilter}
                  </span>
                  <button
                    onClick={() => {
                      setProductFilter(null)
                      setPage(1)
                      window.history.pushState({}, '', '/tickets')
                    }}
                    className="text-primary hover:text-primary/80 transition-colors"
                    aria-label="Clear filter"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

        {/* Cases Table */}
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          {isLoading ? (
            <div className="p-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted border-b border-border">
                    <tr>
                      <th className="w-12 px-4 py-3 text-xs font-medium text-muted-foreground uppercase"></th>
                      <th
                        className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition-colors select-none"
                        onClick={() => handleSort('case_number')}
                      >
                        Case Number{renderSortIcon('case_number')}
                      </th>
                      <th
                        className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition-colors select-none"
                        onClick={() => handleSort('subject')}
                      >
                        Subject{renderSortIcon('subject')}
                      </th>
                      <th
                        className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition-colors select-none"
                        onClick={() => handleSort('status')}
                      >
                        Status{renderSortIcon('status')}
                      </th>
                      <th
                        className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition-colors select-none"
                        onClick={() => handleSort('generated_product')}
                      >
                        Product{renderSortIcon('generated_product')}
                      </th>
                      <th
                        className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition-colors select-none"
                        onClick={() => handleSort('severity')}
                      >
                        Severity{renderSortIcon('severity')}
                      </th>
                      <th
                        className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition-colors select-none"
                        onClick={() => handleSort('account_name')}
                      >
                        Account{renderSortIcon('account_name')}
                      </th>
                      <th
                        className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition-colors select-none"
                        onClick={() => handleSort('created_at')}
                      >
                        Created{renderSortIcon('created_at')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTickets && filteredTickets.length > 0 ? (
                      filteredTickets.map((ticket) => (
                        <TicketRow
                          key={ticket.id}
                          ticket={ticket}
                          getStatusColor={getStatusColor}
                          getSeverityColor={getSeverityColor}
                          getSeverityLabel={getSeverityLabel}
                        />
                      ))
                    ) : (
                      <tr>
                        <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                          No cases found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {data && (
                <div className="px-4 py-3 border-t border-border flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data.total)} of {data.total} cases
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 border border-border rounded text-sm hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage(p => p + 1)}
                      disabled={page * pageSize >= data.total}
                      className="px-3 py-1 border border-border rounded text-sm hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
          </>
        )}
      </main>
    </div>
  )
}
