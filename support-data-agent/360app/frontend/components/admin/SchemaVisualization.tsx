'use client'

import { useState } from 'react'
import { TableNode } from './TableNode'
import { PerformanceMetrics } from './PerformanceMetrics'

interface TableStatus {
  created: boolean
  rowCount: number
}

interface SchemaVisualizationProps {
  sourceName: string
  sourceTables: string[]
  outputTable: string
  baseTableStatus: TableStatus
  topicMetricsStatus: TableStatus
  productMetricsStatus: TableStatus
  activeTable: 'enriched' | 'topics' | 'products'
  onTableClick: (table: 'enriched' | 'topics' | 'products') => void
}

export function SchemaVisualization({
  sourceName,
  sourceTables,
  outputTable,
  baseTableStatus,
  topicMetricsStatus,
  productMetricsStatus,
  activeTable,
  onTableClick,
}: SchemaVisualizationProps) {
  const [activeView, setActiveView] = useState<'diagram' | 'performance'>('diagram')

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      {/* Header with Tabs */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Knowledge Base Overview</h2>

        {/* Tab Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveView('diagram')}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              activeView === 'diagram'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            Diagram
          </button>
          <button
            onClick={() => setActiveView('performance')}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              activeView === 'performance'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            Performance
          </button>
        </div>
      </div>

      {/* Content */}
      {activeView === 'diagram' ? (
        <>
          <div className="flex items-center justify-center gap-6 py-4">
        {/* Source */}
        <div className="flex flex-col items-center">
          <TableNode
            type="source"
            title={sourceName}
            items={sourceTables}
          />
        </div>

        {/* Arrow: Source to Base */}
        <div className="flex flex-col items-center justify-center">
          <span className="text-xs text-muted-foreground mb-1 whitespace-nowrap">Extract & Enrich</span>
          <div className="flex items-center">
            <div className="h-px w-16 bg-border border-t-2 border-dashed" />
            <svg className="w-4 h-4 text-muted-foreground -ml-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </div>
        </div>

        {/* Base Table */}
        <div className="flex flex-col items-center">
          <TableNode
            type="base"
            title="Enriched Cases"
            tableName={outputTable}
            rowCount={baseTableStatus.rowCount}
            isActive={activeTable === 'enriched'}
            onClick={() => onTableClick('enriched')}
          />
        </div>

        {/* Arrow: Base to Aggregations */}
        <div className="flex flex-col items-center justify-center">
          <span className="text-xs text-muted-foreground mb-1">Aggregate</span>
          <div className="flex items-center">
            <div className="h-px w-16 bg-border border-t-2 border-dashed" />
            <svg className="w-4 h-4 text-muted-foreground -ml-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </div>
        </div>

        {/* Aggregations (Stacked Vertically) */}
        <div className="flex flex-col gap-4">
          <TableNode
            type="aggregation"
            title="Topic Metrics"
            tableName="TOPIC_METRICS"
            rowCount={topicMetricsStatus.rowCount}
            isActive={activeTable === 'topics'}
            onClick={topicMetricsStatus.created ? () => onTableClick('topics') : undefined}
          />
          <TableNode
            type="aggregation"
            title="Product Metrics"
            tableName="PRODUCT_METRICS"
            rowCount={productMetricsStatus.rowCount}
            isActive={activeTable === 'products'}
            onClick={productMetricsStatus.created ? () => onTableClick('products') : undefined}
          />
        </div>
      </div>

      {/* Hint */}
      <div className="mt-2 flex items-center justify-center gap-2 text-xs text-muted-foreground">
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
        <span>Click any table to preview its data below</span>
      </div>
        </>
      ) : (
        <PerformanceMetrics />
      )}
    </div>
  )
}
