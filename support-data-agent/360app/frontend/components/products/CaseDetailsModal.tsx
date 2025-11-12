'use client'

import { useEffect } from 'react'
import { X } from 'lucide-react'
import { SupportTicket } from '@/types'
import { TicketDetails } from '@/components/tickets/TicketDetails'

interface CaseDetailsModalProps {
  ticket: SupportTicket | null
  onClose: () => void
}

export function CaseDetailsModal({ ticket, onClose }: CaseDetailsModalProps) {
  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  if (!ticket) return null

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg shadow-xl w-full max-w-4xl my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-border">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground mb-1">
              {ticket.subject}
            </h2>
            <p className="text-sm text-muted-foreground">
              Case #{ticket.case_number}
            </p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-1 hover:bg-accent rounded transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <TicketDetails ticket={ticket} />
        </div>
      </div>
    </div>
  )
}
