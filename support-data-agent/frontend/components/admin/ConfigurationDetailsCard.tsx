'use client'

import { formatNumber } from '@/lib/utils'

interface TableStatus {
  created: boolean
  rowCount: number
}

interface ConfigurationDetailsCardProps {
  configName: string
  database: string
  schema: string
  sourceTables: string[]
  outputTable: string
  baseTableStatus: TableStatus
  topicMetricsStatus: TableStatus
  productMetricsStatus: TableStatus
  createdAt: string
  isActive: boolean
  onRefresh?: () => void
  onEdit?: () => void
  onDelete?: () => void
}

export function ConfigurationDetailsCard({
  configName,
  database,
  schema,
  sourceTables,
  outputTable,
  baseTableStatus,
  topicMetricsStatus,
  productMetricsStatus,
  createdAt,
  isActive,
  onRefresh,
  onEdit,
  onDelete,
}: ConfigurationDetailsCardProps) {
  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffInMs = now.getTime() - date.getTime()
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60))

    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours} hrs ago`
    const diffInDays = Math.floor(diffInHours / 24)
    if (diffInDays < 7) return `${diffInDays} days ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4 shadow-sm">
      {/* Compact Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-lg font-bold text-foreground">{configName}</h1>
            <p className="text-xs text-muted-foreground">{database}.{schema}</p>
          </div>
          <div className={`
            flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium
            ${isActive ? 'bg-success/20 text-success' : 'bg-muted text-muted-foreground'}
          `}>
            <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-success' : 'bg-muted-foreground'}`} />
            {isActive ? 'Active' : 'Inactive'}
          </div>
        </div>

        {/* Inline Actions */}
        <div className="flex gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors"
              title="Refresh Data"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors"
              title="Edit Configuration"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors"
              title="Delete Configuration"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7h6m-7 0a1 1 0 011-1h6a1 1 0 011 1m-8 0h10" />
              </svg>
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Compact Info Row */}
      <div className="flex items-start gap-6 text-xs">
        {/* Data Source */}
        <div className="flex-1">
          <span className="text-muted-foreground">Source:</span>{' '}
          <span className="font-medium text-foreground">{sourceTables.join(', ')}</span>
        </div>

        {/* Output */}
        <div className="flex-1">
          <span className="text-muted-foreground">Output:</span>{' '}
          <span className="font-medium text-foreground font-mono">{outputTable}</span>
          <span className="text-success ml-1">({formatNumber(baseTableStatus.rowCount)} rows)</span>
        </div>

        {/* Aggregations */}
        <div className="flex-1">
          <span className="text-muted-foreground">Aggregations:</span>{' '}
          <span className="text-foreground">
            {formatNumber(topicMetricsStatus.rowCount)} topics, {formatNumber(productMetricsStatus.rowCount)} products
          </span>
        </div>

        {/* Metadata */}
        <div className="flex-shrink-0">
          <span className="text-muted-foreground">Created:</span>{' '}
          <span className="text-foreground">{new Date(createdAt).toLocaleDateString()}</span>
          {' | '}
          <span className="text-muted-foreground">Last Refreshed:</span>{' '}
          <span className="text-foreground">{formatRelativeTime(createdAt)}</span>
        </div>
      </div>
    </div>
  )
}
