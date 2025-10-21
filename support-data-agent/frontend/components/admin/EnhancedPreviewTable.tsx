'use client'

import { useState, useMemo } from 'react'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface EnhancedPreviewTableProps {
  columns: string[]
  rows: Record<string, unknown>[]
  isLoading?: boolean
  tableName?: string
}

export function EnhancedPreviewTable({
  columns,
  rows,
  isLoading,
  tableName = 'Data',
}: EnhancedPreviewTableProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [currentPage, setCurrentPage] = useState(1)
  const [rowsPerPage] = useState(10)

  // Filter rows based on search query
  const filteredRows = useMemo(() => {
    if (!searchQuery) return rows

    return rows.filter((row) =>
      Object.values(row).some((value) =>
        String(value).toLowerCase().includes(searchQuery.toLowerCase())
      )
    )
  }, [rows, searchQuery])

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortColumn) return filteredRows

    return [...filteredRows].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortColumn]
      const bVal = (b as Record<string, unknown>)[sortColumn]

      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1

      const aStr = String(aVal as unknown)
      const bStr = String(bVal as unknown)

      if (sortDirection === 'asc') {
        return aStr.localeCompare(bStr, undefined, { numeric: true })
      } else {
        return bStr.localeCompare(aStr, undefined, { numeric: true })
      }
    })
  }, [filteredRows, sortColumn, sortDirection])

  // Paginate rows
  const paginatedRows = useMemo(() => {
    const startIdx = (currentPage - 1) * rowsPerPage
    return sortedRows.slice(startIdx, startIdx + rowsPerPage)
  }, [sortedRows, currentPage, rowsPerPage])

  const totalPages = Math.ceil(sortedRows.length / rowsPerPage)

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const handleExport = () => {
    const csv = [
      columns.join(','),
      ...rows.map((row) => columns.map((col) => JSON.stringify((row as Record<string, unknown>)[col] ?? '')).join(',')),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${tableName.replace(/\s+/g, '_')}_export.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="md" />
      </div>
    )
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <svg className="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p className="text-sm">No preview data available</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header Controls */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 max-w-md">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search data..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setCurrentPage(1)
              }}
              className="w-full pl-10 pr-4 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted sticky top-0 z-10">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:bg-muted/80 transition-colors select-none"
                  >
                    <div className="flex items-center gap-1">
                      <span>{col}</span>
                      {sortColumn === col && (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          {sortDirection === 'asc' ? (
                            <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
                          ) : (
                            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                          )}
                        </svg>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedRows.map((row, idx) => (
                <tr key={idx} className="border-t border-border hover:bg-muted/30 transition-colors">
                  {columns.map((col) => (
                    <td
                      key={col}
                      className="px-3 py-2 text-xs max-w-xs truncate"
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
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>
          Showing rows {((currentPage - 1) * rowsPerPage) + 1}-{Math.min(currentPage * rowsPerPage, sortedRows.length)} of {sortedRows.length}
          {searchQuery && ` (filtered from ${rows.length} total)`}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            ← Prev
          </button>
          <span className="px-3">
            Page {currentPage} of {totalPages || 1}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages || totalPages === 0}
            className="px-3 py-1 border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  )
}
