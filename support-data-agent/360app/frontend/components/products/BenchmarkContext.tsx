'use client'

import React from 'react'
import { Minus } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { productsApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface BenchmarkMetrics {
  cases: number
  avgTime: number
  resolutionRate: number
}

interface BenchmarkComparison {
  delta: number
  direction: 'higher' | 'lower' | 'neutral'
  status: 'better' | 'worse' | 'neutral'
}

interface BenchmarkLevel {
  name: string
  metrics: BenchmarkMetrics
  comparison: {
    cases: BenchmarkComparison
    avgTime: BenchmarkComparison
    resolutionRate: BenchmarkComparison
  }
}

interface BenchmarkContextData {
  yourProduct: {
    productId: string
    productName: string
    category: string
    subcategory: string | null
    metrics: BenchmarkMetrics
  }
  subcategoryAverage?: BenchmarkLevel
  categoryAverage?: BenchmarkLevel
}

interface BenchmarkContextProps {
  productId: string
  period?: string
}

export function BenchmarkContext({ productId, period = 'week' }: BenchmarkContextProps) {
  const { data, isLoading } = useQuery<BenchmarkContextData>({
    queryKey: ['benchmark-context', productId, period],
    queryFn: async () => {
      return await productsApi.getBenchmarkContext(productId, period)
    },
  })

  const getStatusIcon = (status: string) => {
    if (status === 'better') return <span className="text-green-600">✓</span>
    if (status === 'worse') return <span className="text-red-600">✗</span>
    return <Minus size={14} className="text-gray-400" />
  }

  const getDeltaColor = (status: string) => {
    if (status === 'better') return 'text-green-600'
    if (status === 'worse') return 'text-red-600'
    return 'text-gray-600'
  }

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-foreground mb-3">📊 Performance Benchmarks</h3>
        <LoadingSpinner size="sm" className="h-32" />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-foreground mb-3">📊 Performance Benchmarks</h3>
      <div className="space-y-4">
        {/* Your Product */}
        <div>
          <h4 className="font-medium text-xs mb-2 text-muted-foreground">Your Product</h4>
          <p className="text-xs text-muted-foreground mb-2">{data.yourProduct.productName}</p>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Cases:</span>
              <span className="font-medium text-foreground">{data.yourProduct.metrics.cases}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Avg Time:</span>
              <span className="font-medium text-foreground">{data.yourProduct.metrics.avgTime.toFixed(1)}h</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Resolution:</span>
              <span className="font-medium text-foreground">{data.yourProduct.metrics.resolutionRate.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Subcategory Average */}
        {data.subcategoryAverage && (
          <div className="border-t border-border pt-3">
            <h4 className="font-medium text-xs mb-2 text-muted-foreground">vs. Subcategory Average</h4>
            <p className="text-xs text-muted-foreground mb-2">({data.subcategoryAverage.name})</p>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Cases:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">
                    {data.subcategoryAverage.metrics.cases.toFixed(1)}
                  </span>
                  <span className={`text-xs font-medium ${getDeltaColor(data.subcategoryAverage.comparison.cases.status)}`}>
                    {data.subcategoryAverage.comparison.cases.direction === 'higher' && '↑'}
                    {data.subcategoryAverage.comparison.cases.direction === 'lower' && '↓'}
                    {' '}You: {data.subcategoryAverage.comparison.cases.delta > 0 ? '+' : ''}
                    {data.subcategoryAverage.comparison.cases.delta.toFixed(0)}%
                  </span>
                  {getStatusIcon(data.subcategoryAverage.comparison.cases.status)}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Avg Time:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">
                    {data.subcategoryAverage.metrics.avgTime.toFixed(1)}h
                  </span>
                  <span className={`text-xs font-medium ${getDeltaColor(data.subcategoryAverage.comparison.avgTime.status)}`}>
                    {data.subcategoryAverage.comparison.avgTime.status === 'better' ? 'Better' :
                     data.subcategoryAverage.comparison.avgTime.status === 'worse' ? 'Worse' : 'Same'}
                  </span>
                  {getStatusIcon(data.subcategoryAverage.comparison.avgTime.status)}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Resolution:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">
                    {data.subcategoryAverage.metrics.resolutionRate.toFixed(1)}%
                  </span>
                  <span className={`text-xs font-medium ${getDeltaColor(data.subcategoryAverage.comparison.resolutionRate.status)}`}>
                    {data.subcategoryAverage.comparison.resolutionRate.status === 'better' ? 'Better' :
                     data.subcategoryAverage.comparison.resolutionRate.status === 'worse' ? 'Worse' : 'Same'}
                  </span>
                  {getStatusIcon(data.subcategoryAverage.comparison.resolutionRate.status)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Category Average */}
        {data.categoryAverage && (
          <div className="border-t border-border pt-3">
            <h4 className="font-medium text-xs mb-2 text-muted-foreground">vs. Category Average</h4>
            <p className="text-xs text-muted-foreground mb-2">({data.categoryAverage.name})</p>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Cases:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">
                    {data.categoryAverage.metrics.cases.toFixed(1)}
                  </span>
                  <span className={`text-xs font-medium ${getDeltaColor(data.categoryAverage.comparison.cases.status)}`}>
                    {data.categoryAverage.comparison.cases.direction === 'higher' && '↑'}
                    {data.categoryAverage.comparison.cases.direction === 'lower' && '↓'}
                    {' '}You: {data.categoryAverage.comparison.cases.delta > 0 ? '+' : ''}
                    {data.categoryAverage.comparison.cases.delta.toFixed(0)}%
                  </span>
                  {getStatusIcon(data.categoryAverage.comparison.cases.status)}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Avg Time:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">
                    {data.categoryAverage.metrics.avgTime.toFixed(1)}h
                  </span>
                  <span className={`text-xs font-medium ${getDeltaColor(data.categoryAverage.comparison.avgTime.status)}`}>
                    {data.categoryAverage.comparison.avgTime.status === 'better' ? 'Better' :
                     data.categoryAverage.comparison.avgTime.status === 'worse' ? 'Worse' : 'Same'}
                  </span>
                  {getStatusIcon(data.categoryAverage.comparison.avgTime.status)}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Resolution:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">
                    {data.categoryAverage.metrics.resolutionRate.toFixed(1)}%
                  </span>
                  <span className={`text-xs font-medium ${getDeltaColor(data.categoryAverage.comparison.resolutionRate.status)}`}>
                    {data.categoryAverage.comparison.resolutionRate.status === 'better' ? 'Better' :
                     data.categoryAverage.comparison.resolutionRate.status === 'worse' ? 'Worse' : 'Same'}
                  </span>
                  {getStatusIcon(data.categoryAverage.comparison.resolutionRate.status)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
