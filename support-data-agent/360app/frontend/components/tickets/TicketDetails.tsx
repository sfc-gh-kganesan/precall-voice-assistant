import { SupportTicket } from '@/types'
import { Calendar, Clock, TrendingUp, User, MessageSquare, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TicketDetailsProps {
  ticket: SupportTicket
}

export function TicketDetails({ ticket }: TicketDetailsProps) {
  const formatDate = (date: string | null) => {
    if (!date) return 'N/A'
    return new Date(date).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (hours: number | null) => {
    if (hours === null) return 'N/A'
    if (hours < 1) return `${Math.round(hours * 60)} minutes`
    if (hours < 24) return `${hours.toFixed(1)} hours`
    return `${(hours / 24).toFixed(1)} days`
  }

  const _getSentimentColor = (sentiment?: string) => {
    switch (sentiment) {
      case 'positive': return 'text-success'
      case 'negative': return 'text-error'
      case 'neutral': return 'text-muted-foreground'
      default: return 'text-muted-foreground'
    }
  }

  const getSentimentLabel = (sentiment?: string) => {
    if (!sentiment) return null
    return sentiment.charAt(0).toUpperCase() + sentiment.slice(1)
  }

  return (
    <div className="p-3 bg-muted/30 border-t border-border">
      {/* Two Column Layout: Description + Key Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mb-3">
        {/* Description - Takes 2 columns on large screens */}
        {ticket.description && (
          <div className="lg:col-span-2 bg-card border border-border rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-primary" />
              <h4 className="font-semibold text-xs text-foreground">Description</h4>
            </div>
            <p className="text-xs text-foreground leading-normal whitespace-pre-wrap">
              {ticket.description}
            </p>
          </div>
        )}

        {/* Quick Summary - 1 column on large screens */}
        <div className="bg-card border border-border rounded-lg p-3 space-y-2">
          {/* Timeline Compact */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Calendar className="w-3.5 h-3.5 text-primary" />
              <h4 className="font-semibold text-xs text-foreground">Timeline</h4>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">Created:</span>
                <span className="text-foreground text-right">{formatDate(ticket.created_at)}</span>
              </div>
              {ticket.closed_at && (
                <div className="flex justify-between gap-2">
                  <span className="text-muted-foreground">Closed:</span>
                  <span className="text-foreground text-right">{formatDate(ticket.closed_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Resolution Compact */}
          <div className="pt-2 border-t border-border">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Clock className="w-3.5 h-3.5 text-primary" />
              <h4 className="font-semibold text-xs text-foreground">Resolution</h4>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">Duration:</span>
                <span className="text-foreground">{formatDuration(ticket.resolution_time_hours)}</span>
              </div>
              <div className="flex justify-between items-center gap-2">
                <span className="text-muted-foreground">SLA:</span>
                <span className={cn(
                  'flex items-center gap-1 font-medium',
                  ticket.sla_violated ? 'text-error' : 'text-success'
                )}>
                  {ticket.sla_violated ? (
                    <>
                      <XCircle className="w-3 h-3" />
                      Violated
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-3 h-3" />
                      Met
                    </>
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Condensed Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
        {/* Priority History Section */}
        <div className="bg-card border border-border rounded-lg p-2.5">
          <div className="flex items-center gap-1.5 mb-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-primary" />
            <h4 className="font-semibold text-xs text-foreground">Priority History</h4>
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">Initial:</span>
              <span className="text-foreground text-right text-[11px]">{ticket.initial_severity}</span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">Peak:</span>
              <span className="text-foreground text-right text-[11px]">{ticket.peak_severity}</span>
            </div>
          </div>
        </div>

        {/* Account Details */}
        <div className="bg-card border border-border rounded-lg p-2.5">
          <div className="flex items-center gap-1.5 mb-1.5">
            <User className="w-3.5 h-3.5 text-primary" />
            <h4 className="font-semibold text-xs text-foreground">Account</h4>
          </div>
          <div className="space-y-1 text-xs">
            <div>
              <span className="text-muted-foreground block">Name:</span>
              <span className="text-foreground font-medium">{ticket.account_name}</span>
            </div>
            {ticket.is_priority_support && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-warning/10 text-warning rounded text-[11px] font-medium">
                <AlertCircle className="w-3 h-3" />
                Priority
              </span>
            )}
          </div>
        </div>

        {/* Metadata Compact */}
        <div className="bg-card border border-border rounded-lg p-2.5">
          <div className="flex items-center gap-1.5 mb-1.5">
            <MessageSquare className="w-3.5 h-3.5 text-primary" />
            <h4 className="font-semibold text-xs text-foreground">Activity</h4>
          </div>
          <div className="flex flex-wrap gap-1">
            <span className="px-2 py-0.5 bg-muted text-foreground rounded text-[11px] font-medium">
              {ticket.total_comments} Comments
            </span>
            {ticket.has_jira_issues && (
              <span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-[11px] font-medium">
                Jira
              </span>
            )}
            {ticket.has_escalations && (
              <span className="px-2 py-0.5 bg-error/10 text-error rounded text-[11px] font-medium">
                Escalated
              </span>
            )}
            {ticket.has_collaborations && (
              <span className="px-2 py-0.5 bg-success/10 text-success rounded text-[11px] font-medium">
                Collab
              </span>
            )}
          </div>
        </div>
      </div>

      {/* AI-Generated Insights */}
      {(ticket.generated_topic || ticket.generated_product_category || ticket.generated_feature || ticket.sentiment) && (
        <div className="bg-card border border-border rounded-lg p-2.5">
          <div className="flex items-center gap-1.5 mb-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-primary" />
            <h4 className="font-semibold text-xs text-foreground">AI Insights</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ticket.generated_topic && (
              <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-[11px] font-medium">
                {ticket.generated_topic}
              </span>
            )}
            {ticket.generated_product_category && (
              <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-[11px] font-medium">
                {ticket.generated_product_category}
              </span>
            )}
            {ticket.generated_feature && (
              <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-[11px] font-medium">
                {ticket.generated_feature}
              </span>
            )}
            {ticket.sentiment && (
              <span className={cn(
                'px-2 py-0.5 rounded-full text-[11px] font-medium',
                ticket.sentiment === 'positive' && 'bg-success/10 text-success',
                ticket.sentiment === 'negative' && 'bg-error/10 text-error',
                ticket.sentiment === 'neutral' && 'bg-muted text-muted-foreground'
              )}>
                {getSentimentLabel(ticket.sentiment)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
