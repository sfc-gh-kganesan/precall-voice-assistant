'use client'

import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface PreviewTableProps {
  columns: string[]
  rows: Record<string, unknown>[]
  isLoading?: boolean
  highlightedColumns?: string[]
}

export function PreviewTable({ columns, rows, isLoading, highlightedColumns = [] }: PreviewTableProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="md" />
      </div>
    )
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        No preview data available
      </div>
    )
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="overflow-x-auto max-h-96">
        <table className="w-full text-sm">
          <thead className="bg-muted sticky top-0">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className={`
                    px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase
                    ${highlightedColumns.includes(col) ? 'bg-primary/10 text-primary' : ''}
                  `}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className="border-t border-border hover:bg-muted/50">
                {columns.map((col) => (
                <td
                    key={col}
                    className={`
                      px-3 py-2 text-xs max-w-xs truncate
                      ${highlightedColumns.includes(col) ? 'bg-primary/5' : ''}
                    `}
                    title={String((row as Record<string, unknown>)[col] as unknown)}
                  >
                    {(row as Record<string, unknown>)[col] !== null && (row as Record<string, unknown>)[col] !== undefined ? String((row as Record<string, unknown>)[col] as unknown) : '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-3 py-2 bg-muted text-xs text-muted-foreground border-t border-border">
        Showing {rows.length} sample rows
      </div>
    </div>
  )
}
