'use client'

import type { ImprovementSuggestion } from '@/lib/types'

interface KnowledgeRecommendationModalProps {
  insight: ImprovementSuggestion
  isOpen: boolean
  onClose: () => void
}

export default function KnowledgeRecommendationModal({
  insight,
  isOpen,
  onClose,
}: KnowledgeRecommendationModalProps) {
  if (!isOpen || !insight.knowledge_recommendation) return null

  const knowledgeRec = insight.knowledge_recommendation

  // Doc type badge styling
  const docTypeBadges = {
    new_page: {
      label: 'New Page',
      className: 'bg-green-900/50 text-green-300 border border-green-700'
    },
    update_existing: {
      label: 'Update Existing',
      className: 'bg-amber-900/50 text-amber-300 border border-amber-700'
    },
    add_example: {
      label: 'Add Example',
      className: 'bg-blue-900/50 text-blue-300 border border-blue-700'
    }
  }

  const docTypeBadge = docTypeBadges[knowledgeRec.doc_type]

  return (
    <div
      className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm overflow-y-auto z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="relative mx-auto border-2 border-slate-700 w-full max-w-4xl shadow-2xl rounded-lg bg-slate-900 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-slate-900 border-b border-slate-700 px-6 py-4 flex justify-between items-start z-10">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl">📚</span>
              <h3 className="text-lg font-serif font-semibold text-parchment-100">
                Documentation Recommendation
              </h3>
            </div>
            <p className="text-sm text-parchment-300 mt-2">{knowledgeRec.title}</p>
          </div>
          <button
            onClick={onClose}
            className="text-parchment-300 hover:text-parchment-100 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Doc Type & Priority */}
          <div className="flex gap-4 flex-wrap">
            <div>
              <span className="text-xs text-parchment-400">Documentation Type:</span>
              <span className={`ml-2 px-2 py-1 text-xs rounded ${docTypeBadge.className}`}>
                {docTypeBadge.label}
              </span>
            </div>
            <div>
              <span className="text-xs text-parchment-400">Priority:</span>
              <span
                className={`ml-2 px-2 py-1 text-xs rounded ${
                  knowledgeRec.priority === 'high'
                    ? 'bg-red-900/50 text-red-300 border border-red-700'
                    : knowledgeRec.priority === 'medium'
                    ? 'bg-amber-900/50 text-amber-300 border border-amber-700'
                    : 'bg-blue-900/50 text-blue-300 border border-blue-700'
                }`}
              >
                {knowledgeRec.priority}
              </span>
            </div>
            {knowledgeRec.status && (
              <div>
                <span className="text-xs text-parchment-400">Status:</span>
                <span className="ml-2 px-2 py-1 text-xs rounded bg-slate-800 text-parchment-300 border border-slate-600">
                  {knowledgeRec.status}
                </span>
              </div>
            )}
          </div>

          {/* Target Document */}
          <div>
            <h4 className="text-sm font-semibold text-parchment-200 mb-2">Target Document</h4>
            <div className="bg-slate-800/50 px-4 py-3 rounded border border-slate-700">
              <code className="text-sm font-mono text-strategic-400">{knowledgeRec.target_doc}</code>
            </div>
          </div>

          {/* Existing Coverage */}
          {knowledgeRec.existing_doc_coverage && (
            <div>
              <h4 className="text-sm font-semibold text-parchment-200 mb-2">Current Documentation Coverage</h4>
              <div className="bg-slate-800/50 px-4 py-3 rounded border border-slate-700">
                <p className="text-sm text-parchment-300">{knowledgeRec.existing_doc_coverage}</p>
              </div>
            </div>
          )}

          {/* Rationale */}
          <div>
            <h4 className="text-sm font-semibold text-parchment-200 mb-2">Rationale</h4>
            <div className="bg-slate-800/50 px-4 py-3 rounded border border-slate-700">
              <p className="text-sm text-parchment-300">{knowledgeRec.rationale}</p>
            </div>
          </div>

          {/* Recommended Content */}
          <div>
            <h4 className="text-sm font-semibold text-parchment-200 mb-2">Recommended Content</h4>
            <div className="border border-slate-700 rounded-lg overflow-hidden">
              {/* Header */}
              <div className="bg-slate-800/50 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
                <span className="text-xs text-parchment-400">Markdown Preview</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(knowledgeRec.recommended_content)
                  }}
                  className="text-xs text-strategic-500 hover:text-strategic-400 transition-colors"
                >
                  📋 Copy
                </button>
              </div>
              {/* Content */}
              <div className="bg-slate-950 p-4 max-h-96 overflow-y-auto">
                <pre className="text-xs font-mono text-parchment-300 whitespace-pre-wrap break-words">
                  {knowledgeRec.recommended_content}
                </pre>
              </div>
            </div>
          </div>

          {/* Glean Sources */}
          {knowledgeRec.glean_sources && knowledgeRec.glean_sources.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-parchment-200 mb-2">
                Internal Knowledge Sources ({knowledgeRec.glean_sources.length})
              </h4>
              <div className="bg-slate-800/50 px-4 py-3 rounded border border-slate-700">
                <ul className="space-y-2">
                  {knowledgeRec.glean_sources.map((source, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-strategic-500 mt-0.5">→</span>
                      <a
                        href={source}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-strategic-400 hover:text-strategic-300 hover:underline break-all"
                      >
                        {source}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Generation Timestamp */}
          {knowledgeRec.generated_at && (
            <div className="text-xs text-parchment-400">
              Generated at: {new Date(knowledgeRec.generated_at).toLocaleString()}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="sticky bottom-0 bg-slate-900 border-t border-slate-700 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border border-slate-600 text-parchment-300 rounded hover:bg-slate-800 transition-colors"
          >
            Close
          </button>
          <button
            onClick={() => {
              navigator.clipboard.writeText(knowledgeRec.recommended_content)
            }}
            className="px-4 py-2 text-sm bg-strategic-600 text-parchment-50 rounded hover:bg-strategic-500 transition-colors flex items-center gap-2"
          >
            📋 Copy Content
          </button>
        </div>
      </div>
    </div>
  )
}
