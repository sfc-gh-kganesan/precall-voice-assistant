'use client'

import React, { useState } from 'react'
import { Clock, ExternalLink } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ticketsApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SupportTicket } from '@/types'
import { CaseDetailsModal } from './CaseDetailsModal'

interface RecentCasesSidebarProps {
  productName: string
}

export function RecentCasesSidebar({ productName }: RecentCasesSidebarProps) {
  const router = useRouter()
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null)

  const calculateAgeInDays = (createdAt: string): number => {
    const created = new Date(createdAt)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - created.getTime())
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  const { data: cases, isLoading } = useQuery({
    queryKey: ['recent-cases', productName],
    queryFn: async () => {
      const response = await ticketsApi.getTickets({
        product: productName,
        severity: 'Severity-1,Severity-2',
        page: 1,
        pageSize: 5,
        sortBy: 'created_at',
        sortOrder: 'desc',
      })
      return response.tickets
    },
  })

  const getSeverityColor = (severity: string) => {
    if (severity.startsWith('Severity-1')) {
      return 'text-red-600'
    }
    return 'text-orange-600'
  }

  const getSeverityLabel = (severity: string) => {
    if (severity.startsWith('Severity-1')) return 'S1'
    if (severity.startsWith('Severity-2')) return 'S2'
    return severity
  }

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase()
    if (statusLower.includes('closed')) return 'text-gray-500'
    if (statusLower.includes('progress')) return 'text-blue-600'
    if (statusLower.includes('awaiting')) return 'text-amber-600'
    return 'text-green-600'
  }

  const getAgeColor = (ageInDays: number, status: string) => {
    const isOpen = !status.toLowerCase().includes('closed')
    if (isOpen && ageInDays > 7) return 'text-red-600 font-semibold'
    if (isOpen && ageInDays > 3) return 'text-orange-600'
    return 'text-gray-600'
  }

  const formatAge = (ageInDays: number) => {
    if (ageInDays === 0) return 'Today'
    if (ageInDays === 1) return '1d ago'
    return `${ageInDays}d ago`
  }

  const handleCaseClick = (ticket: SupportTicket) => {
    setSelectedTicket(ticket)
  }

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          🚨 Recent Critical Cases
        </h3>
        <LoadingSpinner size="sm" className="h-32" />
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
        🚨 Recent Critical Cases
      </h3>
      <div className="space-y-3">
        {cases && cases.length > 0 ? (
          <>
            {cases.map((ticket) => {
              const ageInDays = calculateAgeInDays(ticket.created_at)
              return (
                <div
                  key={ticket.case_number}
                  onClick={() => handleCaseClick(ticket)}
                  className="cursor-pointer hover:bg-accent/50 p-3 rounded-lg transition-all border border-border hover:border-primary/20 hover:shadow-sm"
                >
                  {/* Subject - Most Prominent */}
                  <div className="mb-2">
                    <p className="text-sm font-semibold line-clamp-2 text-foreground leading-snug">{ticket.subject}</p>
                  </div>

                  {/* Customer - Second Most Prominent */}
                  <div className="mb-2">
                    <p className="text-xs text-muted-foreground font-medium">{ticket.account_name}</p>
                  </div>

                  {/* Metadata row - Small and subtle */}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className={`font-medium ${getSeverityColor(ticket.severity)}`}>
                      {getSeverityLabel(ticket.severity)}
                    </span>
                    <span>•</span>
                    <span className={getStatusColor(ticket.status)}>
                      {ticket.status}
                    </span>
                    <span>•</span>
                    <span className={`flex items-center gap-1 ${getAgeColor(ageInDays, ticket.status)}`}>
                      <Clock size={10} />
                      {formatAge(ageInDays)}
                    </span>
                    <span className="ml-auto text-[10px]">#{ticket.case_number}</span>
                  </div>
                </div>
              )
            })}
            <button
              onClick={() => router.push(`/tickets?product=${productName}&severity=Severity-1,Severity-2`)}
              className="w-full text-xs text-blue-600 hover:text-blue-800 flex items-center justify-center gap-1 py-2 hover:bg-accent rounded transition-colors"
            >
              View All Cases
              <ExternalLink size={12} />
            </button>
          </>
        ) : (
          <p className="text-xs text-muted-foreground text-center py-4">
            No Sev 1 or Sev 2 cases found for this product
          </p>
        )}
      </div>

      {/* Case Details Modal */}
      <CaseDetailsModal ticket={selectedTicket} onClose={() => setSelectedTicket(null)} />
    </div>
  )
}
