'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { ProductMetrics, SupportTicket } from '@/types'
import { formatNumber, formatPercentage, cn } from '@/lib/utils'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { API_CONFIG } from '@/lib/constants'

interface ProductDetailSidebarProps {
  product: ProductMetrics
  onClose: () => void
}

interface TicketResponse {
  tickets: SupportTicket[]
  total: number
  page: number
  pageSize: number
}

export function ProductDetailSidebar({ product, onClose }: ProductDetailSidebarProps) {
  const [page, setPage] = useState(1)
  const pageSize = 20
  const API_BASE = API_CONFIG.BASE_URL

  const { data, isLoading } = useQuery<TicketResponse>({
    queryKey: ['product-tickets', product.productName, page],
    queryFn: async () => {
      const response = await fetch(
        `${API_BASE}/api/v1/tickets?product=${encodeURIComponent(product.productName)}&page=${page}&pageSize=${pageSize}`
      )
      if (!response.ok) throw new Error('Failed to fetch tickets')
      return response.json()
    },
  })

  const getSeverityColor = (severity: string) => {
    if (severity.includes('Severity-1')) return 'text-error'
    if (severity.includes('Severity-2')) return 'text-warning'
    if (severity.includes('Severity-3')) return 'text-info'
    return 'text-muted-foreground'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Closed':
        return 'bg-success/10 text-success'
      case 'In Progress':
        return 'bg-info/10 text-info'
      case 'Awaiting Customer':
        return 'bg-warning/10 text-warning'
      case 'Escalated':
        return 'bg-error/10 text-error'
      default:
        return 'bg-muted/10 text-muted-foreground'
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="fixed right-0 top-0 h-full w-full md:w-2/5 lg:w-1/3 bg-card border-l border-border z-50 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="border-b border-border p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h2 className="text-xl font-bold text-foreground mb-1">
                {product.productName}
              </h2>
              <p className="text-sm text-muted-foreground">{product.productCategory}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          </div>

          {/* Quick Metrics Recap */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-background rounded-lg p-3">
              <div className="text-lg font-bold text-primary">
                {formatNumber(product.metrics.totalCases.value)}
              </div>
              <div className="text-xs text-muted-foreground">Cases</div>
            </div>
            <div className="bg-background rounded-lg p-3">
              <div className="text-lg font-bold text-foreground">
                {product.metrics.avgCaseLife.value.toFixed(1)}h
              </div>
              <div className="text-xs text-muted-foreground">Avg Resolution</div>
            </div>
            <div className="bg-background rounded-lg p-3">
              <div className="text-lg font-bold text-success">
                {formatPercentage(product.metrics.resolutionRate.value)}
              </div>
              <div className="text-xs text-muted-foreground">Resolution</div>
            </div>
          </div>
        </div>

        {/* Case List */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="md" />
            </div>
          ) : data?.tickets && data.tickets.length > 0 ? (
            <>
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-foreground mb-1">
                  Cases for this Product
                </h3>
                <p className="text-xs text-muted-foreground">
                  Showing {((page - 1) * pageSize) + 1}-{Math.min(page * pageSize, data.total)} of {data.total} cases
                </p>
              </div>

              <div className="space-y-3">
                {data.tickets.map((ticket) => (
                  <div
                    key={ticket.id}
                    className="bg-background border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
                  >
                    {/* Case Header */}
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono font-medium text-primary">
                          {ticket.case_number}
                        </span>
                        <span className={cn('text-xs font-medium', getSeverityColor(ticket.severity))}>
                          S{ticket.severity.charAt(9)}
                        </span>
                      </div>
                      <span className={cn('text-xs px-2 py-1 rounded-full font-medium', getStatusColor(ticket.status))}>
                        {ticket.status}
                      </span>
                    </div>

                    {/* Subject */}
                    <div className="mb-2">
                      <p className="text-sm text-foreground font-medium line-clamp-2">
                        {ticket.subject}
                      </p>
                    </div>

                    {/* Metadata */}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{ticket.account_name}</span>
                      <span>•</span>
                      <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                      {ticket.resolution_time_hours && (
                        <>
                          <span>•</span>
                          <span>{ticket.resolution_time_hours.toFixed(1)}h</span>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {Math.ceil(data.total / pageSize) > 1 && (
                <div className="mt-6 flex items-center justify-between">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className={cn(
                      'px-3 py-2 text-sm rounded-md transition-colors',
                      page === 1
                        ? 'bg-muted text-muted-foreground cursor-not-allowed'
                        : 'bg-primary text-primary-foreground hover:bg-primary/90'
                    )}
                  >
                    Previous
                  </button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {Math.ceil(data.total / pageSize)}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(Math.ceil(data.total / pageSize), p + 1))}
                    disabled={page === Math.ceil(data.total / pageSize)}
                    className={cn(
                      'px-3 py-2 text-sm rounded-md transition-colors',
                      page === Math.ceil(data.total / pageSize)
                        ? 'bg-muted text-muted-foreground cursor-not-allowed'
                        : 'bg-primary text-primary-foreground hover:bg-primary/90'
                    )}
                  >
                    Next
                  </button>
                </div>
              )}

              {/* View All Link */}
              <div className="mt-6 pt-4 border-t border-border">
                <a
                  href={`/tickets?product=${encodeURIComponent(product.productName)}`}
                  className="text-sm text-primary hover:underline font-medium"
                >
                  View all {data.total} cases in Cases page →
                </a>
              </div>
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground text-sm">
                No cases found for this product
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
