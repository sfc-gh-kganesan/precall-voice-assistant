'use client'

import { formatNumber } from '@/lib/utils'

interface TableNodeProps {
  type: 'source' | 'base' | 'aggregation'
  title: string
  tableName?: string
  rowCount?: number
  items?: string[]
  isActive?: boolean
  onClick?: () => void
}

const TYPE_CONFIG = {
  source: {
    icon: '📥',
    label: 'Source',
    borderColor: 'border-blue-500',
    bgColor: 'bg-blue-500/5',
    hoverBg: 'hover:bg-blue-500/10',
  },
  base: {
    icon: '🔄',
    label: 'Base Table',
    borderColor: 'border-purple-500',
    bgColor: 'bg-purple-500/5',
    hoverBg: 'hover:bg-purple-500/10',
  },
  aggregation: {
    icon: '📊',
    label: 'Aggregation',
    borderColor: 'border-green-500',
    bgColor: 'bg-green-500/5',
    hoverBg: 'hover:bg-green-500/10',
  },
}

export function TableNode({
  type,
  title,
  tableName,
  rowCount,
  items,
  isActive,
  onClick,
}: TableNodeProps) {
  const config = TYPE_CONFIG[type]

  return (
    <button
      onClick={onClick}
      className={`
        relative w-full max-w-[160px] p-3 rounded-lg border-2 transition-all
        ${config.borderColor} ${config.bgColor} ${config.hoverBg}
        ${isActive ? 'ring-2 ring-offset-2 ring-primary shadow-lg' : 'shadow-md hover:shadow-lg'}
        ${onClick ? 'cursor-pointer' : 'cursor-default'}
        text-left
      `}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{config.icon}</span>
        <span className="text-[10px] font-medium text-muted-foreground uppercase">
          {config.label}
        </span>
      </div>

      {/* Divider */}
      <div className="w-full h-px bg-border mb-2" />

      {/* Content */}
      <div className="space-y-1.5">
        <h3 className="font-semibold text-xs text-foreground">{title}</h3>

        {tableName && (
          <p className="text-[10px] font-mono text-muted-foreground truncate">{tableName}</p>
        )}

        {items && items.length > 0 && (
          <ul className="text-[10px] text-muted-foreground space-y-0.5">
            {items.map((item, idx) => (
              <li key={idx} className="truncate">• {item}</li>
            ))}
          </ul>
        )}

        {rowCount !== undefined && (
          <p className="text-xs font-bold text-foreground">
            {formatNumber(rowCount)} {type === 'aggregation' ? 'items' : 'rows'}
          </p>
        )}
      </div>

      {/* View Data Link */}
      {onClick && (
        <div className="mt-2 pt-2 border-t border-border">
          <span className="text-[10px] text-primary font-medium">
            View Data →
          </span>
        </div>
      )}
    </button>
  )
}
