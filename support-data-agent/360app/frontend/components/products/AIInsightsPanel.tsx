'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

interface AIInsightsPanelProps {
  aiSummary?: string
  rootCauses?: string
}

export function AIInsightsPanel({ aiSummary, rootCauses }: AIInsightsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // If no AI data available, show placeholder
  if (!aiSummary && !rootCauses) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <span>🤖</span> AI Insights (Last 30 Days)
          </h3>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">
            No AI insights available yet. Run the enrichment pipeline to generate insights.
          </p>
        </div>
      </div>
    )
  }

  // Check if data is placeholder text
  const isPlaceholder = (text?: string) => {
    return !text || text.includes('No cases in analysis period') || text.includes('pending')
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between mb-4 hover:opacity-70 transition-opacity"
      >
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span>🤖</span> AI Insights (Last 30 Days)
        </h3>
        {isExpanded ? (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <span>Show less</span>
            <ChevronUp className="w-5 h-5" />
          </div>
        ) : (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <span>Show more</span>
            <ChevronDown className="w-5 h-5" />
          </div>
        )}
      </button>
      <div className={`space-y-6 transition-all duration-300 ${isExpanded ? '' : 'max-h-48 overflow-hidden relative'}`}>
        {/* Customer Sentiment Section */}
        {!isPlaceholder(aiSummary) && (
          <div className="space-y-3">
            <h4 className="text-base font-semibold text-foreground flex items-center gap-2 mb-4">
              <span>📊</span> Customer Sentiment
            </h4>
            <div className="text-sm text-muted-foreground whitespace-pre-wrap">
              {formatMarkdown(aiSummary || '')}
            </div>
          </div>
        )}

        {/* Root Cause Analysis Section */}
        {!isPlaceholder(rootCauses) && (
          <div className="space-y-3 pt-4 border-t border-border">
            <h4 className="text-base font-semibold text-foreground flex items-center gap-2 mb-4">
              <span>🔍</span> Root Cause Analysis
            </h4>
            <div className="text-sm text-muted-foreground whitespace-pre-wrap">
              {formatMarkdown(rootCauses || '')}
            </div>
          </div>
        )}

        {/* Show placeholder if both are placeholders */}
        {isPlaceholder(aiSummary) && isPlaceholder(rootCauses) && (
          <p className="text-sm text-muted-foreground">
            No cases in analysis period (last 30 days). Insights will appear once cases are created.
          </p>
        )}

        {/* Fade overlay when collapsed */}
        {!isExpanded && (
          <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-card to-transparent pointer-events-none" />
        )}
      </div>
    </div>
  )
}

/**
 * Format markdown-like text with proper styling
 * Handles: **bold**, bullet points, and line breaks
 */
function formatMarkdown(text: string) {
  // Split by lines
  const lines = text.split('\n')

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        // Skip empty lines
        if (!line.trim()) return null

        // Handle bold headers like **Sentiment:**
        if (line.includes('**')) {
          const formatted = line.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-foreground">$1</strong>')
          return (
            <div
              key={index}
              className="text-sm"
              dangerouslySetInnerHTML={{ __html: formatted }}
            />
          )
        }

        // Handle bullet points
        if (line.trim().startsWith('-')) {
          const content = line.trim().substring(1).trim()
          return (
            <div key={index} className="flex gap-2 pl-4">
              <span className="text-muted-foreground mt-0.5">•</span>
              <span className="text-sm text-foreground">{content}</span>
            </div>
          )
        }

        // Regular text
        return (
          <p key={index} className="text-sm text-foreground">
            {line}
          </p>
        )
      })}
    </div>
  )
}
