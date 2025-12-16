/**
 * Reusable components for displaying conversation quality, gaps, and ending assessments
 */

interface QualityScoreBadgeProps {
  score?: number
  showLabel?: boolean
  compact?: boolean
}

export function QualityScoreBadge({ score, showLabel = false, compact = false }: QualityScoreBadgeProps) {
  if (score === undefined || score === null) return null

  // Color based on score
  let colorClass = ''
  let label = ''
  if (score >= 0.8) {
    colorClass = 'bg-green-900/50 text-green-300 border-green-700'
    label = 'Excellent'
  } else if (score >= 0.6) {
    colorClass = 'bg-yellow-900/50 text-yellow-300 border-yellow-700'
    label = 'Good'
  } else if (score >= 0.4) {
    colorClass = 'bg-orange-900/50 text-orange-300 border-orange-700'
    label = 'Fair'
  } else {
    colorClass = 'bg-red-900/50 text-red-300 border-red-700'
    label = 'Poor'
  }

  const displayScore = (score * 100).toFixed(0)

  if (compact) {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}
        title={`Quality Score: ${displayScore}% (${label})`}
      >
        {displayScore}%
      </span>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${colorClass}`}>
        {displayScore}%
      </span>
      {showLabel && <span className="text-xs text-text-tertiary">{label}</span>}
    </div>
  )
}

interface EndingAssessmentBadgeProps {
  assessment?: string
  showLabel?: boolean
  compact?: boolean
}

export function EndingAssessmentBadge({ assessment, showLabel = false, compact = false }: EndingAssessmentBadgeProps) {
  if (!assessment || assessment === 'unknown') return null

  let icon = ''
  let colorClass = ''
  let label = ''
  let tooltip = ''

  switch (assessment) {
    case 'appropriate':
      icon = '✓'
      colorClass = 'bg-green-900/50 text-green-300 border-green-700'
      label = 'Appropriate'
      tooltip = 'Ended at natural conclusion'
      break
    case 'premature':
      icon = '⚠️'
      colorClass = 'bg-yellow-900/50 text-yellow-300 border-yellow-700'
      label = 'Premature'
      tooltip = 'Ended too early, user had more questions'
      break
    case 'excessive':
      icon = '⏳'
      colorClass = 'bg-orange-900/50 text-orange-300 border-orange-700'
      label = 'Excessive'
      tooltip = 'Continued past resolution'
      break
    default:
      return null
  }

  if (compact) {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}
        title={tooltip}
      >
        {icon}
      </span>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${colorClass}`}>
        {icon} {label}
      </span>
      {showLabel && <span className="text-xs text-text-muted">{tooltip}</span>}
    </div>
  )
}

interface GapBadgeProps {
  gap: {
    type: string
    description: string
    evidence: string
  }
  compact?: boolean
}

export function KnowledgeGapBadge({ gap, compact = false }: GapBadgeProps) {
  if (!gap) return null

  const typeLabel = gap.type === 'missing_documentation' ? 'Missing Docs' : 'Incomplete KB'

  if (compact) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-blue-900/50 text-blue-300 border-blue-700 cursor-help"
        title={`${typeLabel}: ${gap.description}`}
      >
        📚
      </span>
    )
  }

  return (
    <div
      className="group relative inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border bg-blue-900/50 text-blue-300 border-blue-700 cursor-help"
      title={gap.description}
    >
      <span>📚</span>
      <span>{typeLabel}</span>

      {/* Tooltip */}
      <div className="invisible group-hover:visible absolute bottom-full left-0 mb-2 w-64 p-3 bg-navy-900 border border-navy-800 rounded-lg shadow-xl z-50">
        <div className="text-xs font-semibold text-text-secondary mb-1">{typeLabel}</div>
        <div className="text-xs text-text-tertiary mb-2">{gap.description}</div>
        {gap.evidence && (
          <div className="text-xs text-text-muted italic border-l-2 border-blue-700 pl-2">
            "{gap.evidence}"
          </div>
        )}
      </div>
    </div>
  )
}

export function CapabilityGapBadge({ gap, compact = false }: GapBadgeProps) {
  if (!gap) return null

  let typeLabel = ''
  switch (gap.type) {
    case 'missing_tool':
      typeLabel = 'Missing Tool'
      break
    case 'missing_integration':
      typeLabel = 'Missing Integration'
      break
    case 'unsupported_action':
      typeLabel = 'Unsupported Action'
      break
    default:
      typeLabel = gap.type
  }

  if (compact) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-purple-900/50 text-purple-300 border-purple-700 cursor-help"
        title={`${typeLabel}: ${gap.description}`}
      >
        🔧
      </span>
    )
  }

  return (
    <div
      className="group relative inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border bg-purple-900/50 text-purple-300 border-purple-700 cursor-help"
      title={gap.description}
    >
      <span>🔧</span>
      <span>{typeLabel}</span>

      {/* Tooltip */}
      <div className="invisible group-hover:visible absolute bottom-full left-0 mb-2 w-64 p-3 bg-navy-900 border border-navy-800 rounded-lg shadow-xl z-50">
        <div className="text-xs font-semibold text-text-secondary mb-1">{typeLabel}</div>
        <div className="text-xs text-text-tertiary mb-2">{gap.description}</div>
        {gap.evidence && (
          <div className="text-xs text-text-muted italic border-l-2 border-purple-700 pl-2">
            "{gap.evidence}"
          </div>
        )}
      </div>
    </div>
  )
}

interface GapCardProps {
  type: 'knowledge' | 'capability'
  gap: {
    type: string
    description: string
    evidence: string
  }
}

export function GapCard({ type, gap }: GapCardProps) {
  const isKnowledge = type === 'knowledge'
  const icon = isKnowledge ? '📚' : '🔧'
  const colorClass = isKnowledge
    ? 'border-blue-700 bg-blue-950/30'
    : 'border-purple-700 bg-purple-950/30'
  const titleColorClass = isKnowledge ? 'text-blue-300' : 'text-purple-300'

  let typeLabel = ''
  if (isKnowledge) {
    typeLabel = gap.type === 'missing_documentation' ? 'Missing Documentation' : 'Incomplete Knowledge Base'
  } else {
    switch (gap.type) {
      case 'missing_tool':
        typeLabel = 'Missing Tool'
        break
      case 'missing_integration':
        typeLabel = 'Missing Integration'
        break
      case 'unsupported_action':
        typeLabel = 'Unsupported Action'
        break
      default:
        typeLabel = gap.type
    }
  }

  return (
    <div className={`rounded-lg border p-3 ${colorClass}`}>
      <div className="flex items-start gap-2">
        <span className="text-lg">{icon}</span>
        <div className="flex-1">
          <div className={`text-sm font-semibold ${titleColorClass} mb-1`}>
            {typeLabel}
          </div>
          <div className="text-sm text-text-secondary mb-2">{gap.description}</div>
          {gap.evidence && (
            <div className="text-xs text-text-muted italic border-l-2 border-current pl-2">
              "{gap.evidence}"
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
