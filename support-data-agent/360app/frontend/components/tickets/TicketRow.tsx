'use client'

import { useState } from 'react'
import { SupportTicket } from '@/types'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TicketDetails } from './TicketDetails'

interface TicketRowProps {
  ticket: SupportTicket
  getStatusColor: (status: string) => string
  getSeverityColor: (severity: string) => string
  getSeverityLabel: (severity: string) => string
  shouldAutoExpand?: boolean
}

export function TicketRow({
  ticket,
  getStatusColor,
  getSeverityColor,
  getSeverityLabel,
  shouldAutoExpand = false
}: TicketRowProps) {
  const [isExpanded, setIsExpanded] = useState(shouldAutoExpand)

  const handleToggle = () => {
    setIsExpanded(!isExpanded)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleToggle()
    }
  }

  return (
    <>
      <tr
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        className={cn(
          'border-b border-border transition-colors cursor-pointer',
          'hover:bg-muted/50 focus:outline-none focus:bg-muted/50',
          isExpanded && 'bg-muted/30'
        )}
        role="button"
        aria-expanded={isExpanded}
      >
        <td className="px-4 py-3">
          <div className="flex items-center justify-center">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-primary transition-transform" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground transition-transform" />
            )}
          </div>
        </td>
        <td className="px-4 py-3 text-sm font-mono text-primary">{ticket.case_number}</td>
        <td className="px-4 py-3 text-sm max-w-md truncate">{ticket.subject}</td>
        <td className="px-4 py-3">
          <span className={cn('px-2 py-1 rounded text-xs font-medium', getStatusColor(ticket.status))}>
            {ticket.status}
          </span>
        </td>
        <td className="px-4 py-3 text-sm">{ticket.generated_product || 'N/A'}</td>
        <td className="px-4 py-3">
          <span className={cn('text-sm font-medium', getSeverityColor(ticket.severity))}>
            {getSeverityLabel(ticket.severity)}
          </span>
        </td>
        <td className="px-4 py-3 text-sm">{ticket.account_name}</td>
        <td className="px-4 py-3 text-sm text-muted-foreground">
          {new Date(ticket.created_at).toLocaleDateString()}
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={8} className="p-0 border-b border-border">
            <div className="animate-in slide-in-from-top-2 duration-200">
              <TicketDetails ticket={ticket} />
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
