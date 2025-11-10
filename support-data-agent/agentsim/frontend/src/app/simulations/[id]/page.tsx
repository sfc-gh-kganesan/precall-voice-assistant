'use client'

import { use, useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { simulationsApi, conversationsApi } from '@/lib/api'
import type { Simulation, ConversationSummary, Conversation } from '@/lib/types'

export default function MonitorSimulationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const simulationId = parseInt(id)
  const [simulation, setSimulation] = useState<Simulation | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [modalLoading, setModalLoading] = useState(false)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 2000)
    return () => clearInterval(interval)
  }, [])

  // Poll for conversation details when modal is open
  useEffect(() => {
    if (!selectedConversation) return

    const pollConversation = async () => {
      try {
        const res = await conversationsApi.get(selectedConversation.id)
        setSelectedConversation(res.data)
      } catch (err) {
        console.error('Failed to poll conversation:', err)
      }
    }

    // Only poll if conversation is not completed
    if (!selectedConversation.completed_at) {
      const interval = setInterval(pollConversation, 2000)
      return () => clearInterval(interval)
    }
  }, [selectedConversation?.id, selectedConversation?.completed_at])

  const loadData = async () => {
    try {
      const [simRes, convRes] = await Promise.all([
        simulationsApi.get(simulationId),
        simulationsApi.getConversations(simulationId)
      ])
      setSimulation(simRes.data)
      setConversations(convRes.data)
      setLoading(false)
    } catch (err) {
      console.error(err)
      setLoading(false)
    }
  }

  const openConversationModal = async (conversationId: number) => {
    setModalLoading(true)
    try {
      const res = await conversationsApi.get(conversationId)
      setSelectedConversation(res.data)
    } catch (err) {
      console.error('Failed to load conversation:', err)
      alert('Failed to load conversation details')
    } finally {
      setModalLoading(false)
    }
  }

  const closeModal = () => {
    setSelectedConversation(null)
  }

  if (loading) {
    return <div className="p-8 text-center text-parchment-200">Loading...</div>
  }

  if (!simulation) {
    return <div className="p-8 text-center text-parchment-200">Simulation not found</div>
  }

  const completed = conversations.filter(c => c.completed_at)
  const inProgress = conversations.filter(c => !c.completed_at)
  const successful = completed.filter(c => c.success)
  const progress = conversations.length > 0 ? (completed.length / conversations.length) * 100 : 0

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-serif font-bold text-parchment-100">Simulation Monitor</h1>
          <p className="text-sm text-parchment-200 mt-2">ID: {simulation.id} • Status: {simulation.status}</p>
        </div>
        {simulation.status === 'completed' && (
          <Link href={`/simulations/${simulationId}/results`} className="px-4 py-2 bg-strategic-600 text-parchment-50 rounded-md hover:bg-strategic-500 transition-colors">
            View Results
          </Link>
        )}
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 mb-6">
        <div className="flex justify-between mb-2">
          <span className="text-sm font-medium text-parchment-100">Overall Progress</span>
          <span className="text-sm text-parchment-200">{completed.length} of {conversations.length}</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-4">
          <div className="bg-strategic-600 h-4 rounded-full transition-all" style={{ width: `${progress}%` }}></div>
        </div>
        <div className="mt-3 flex gap-4 text-sm">
          <span className="text-green-400">✓ {successful.length} successful</span>
          <span className="text-red-400">✗ {completed.length - successful.length} failed</span>
          {inProgress.length > 0 && <span className="text-strategic-500">⟳ {inProgress.length} in progress</span>}
        </div>
      </div>

      {inProgress.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-serif font-semibold text-parchment-100 mb-3">In Progress ({inProgress.length})</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {inProgress.map(c => <ConversationCard key={c.id} conversation={c} onClick={() => openConversationModal(c.id)} />)}
          </div>
        </div>
      )}

      {completed.length > 0 && (
        <div>
          <h2 className="text-lg font-serif font-semibold text-parchment-100 mb-3">Completed ({completed.length})</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {completed.map(c => <ConversationCard key={c.id} conversation={c} onClick={() => openConversationModal(c.id)} />)}
          </div>
        </div>
      )}

      {/* Live Conversation Modal */}
      {selectedConversation && (
        <ConversationModal
          conversation={selectedConversation}
          onClose={closeModal}
          isLoading={modalLoading}
        />
      )}
    </div>
  )
}

function ConversationCard({ conversation, onClick }: { conversation: ConversationSummary, onClick: () => void }) {
  const name = conversation.persona?.name || 'Unknown'
  const duration = (conversation.total_duration_ms / 1000).toFixed(1)
  const isComplete = !!conversation.completed_at
  const turns = conversation.num_turns || 0

  return (
    <div
      onClick={onClick}
      className={`bg-slate-800 rounded-lg border p-4 relative overflow-hidden cursor-pointer transition-all hover:shadow-lg ${
        isComplete
          ? (conversation.success ? 'border-green-700 bg-green-950/30 hover:bg-green-950/50' : 'border-red-700 bg-red-950/30 hover:bg-red-950/50')
          : 'border-strategic-600 bg-strategic-950/30 hover:bg-strategic-950/50'
      }`}>
      {/* Pulsing indicator for in-progress */}
      {!isComplete && (
        <div className="absolute top-0 right-0 w-2 h-full bg-strategic-500 animate-pulse"></div>
      )}

      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-parchment-100">{name}</h3>
            {!isComplete && (
              <span className="flex items-center gap-1 text-xs text-strategic-500 font-medium">
                <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Active
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-2">
            <div className="flex items-center gap-1">
              <span className="text-xs font-medium text-parchment-200">Turn</span>
              <span className="text-sm font-bold text-parchment-100">{turns}</span>
            </div>
            <div className="text-xs text-parchment-300">•</div>
            <div className="flex items-center gap-1">
              <span className="text-xs font-medium text-parchment-200">Time</span>
              <span className="text-sm font-bold text-parchment-100">{duration}s</span>
            </div>
          </div>
        </div>

        <div className="text-xs font-medium ml-2">
          {isComplete ? (
            <span className={`px-2 py-1 rounded-full ${
              conversation.success
                ? 'bg-green-900/50 text-green-300 border border-green-700'
                : 'bg-red-900/50 text-red-300 border border-red-700'
            }`}>
              {conversation.success ? '✓ Success' : '✗ Failed'}
            </span>
          ) : (
            <span className="px-2 py-1 rounded-full bg-strategic-900/50 text-strategic-300 border border-strategic-600">
              Running
            </span>
          )}
        </div>
      </div>

      {/* Stop reason for failed conversations */}
      {isComplete && !conversation.success && conversation.stop_reason && (
        <div className="mt-2 text-xs text-parchment-200">
          <span className="font-medium">Reason:</span> {conversation.stop_reason}
        </div>
      )}
    </div>
  )
}

function ConversationModal({ conversation, onClose, isLoading }: {
  conversation: Conversation,
  onClose: () => void,
  isLoading: boolean
}) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const name = conversation.persona?.name || 'Unknown'
  const duration = (conversation.total_duration_ms / 1000).toFixed(1)
  const isComplete = !!conversation.completed_at
  const turns = conversation.num_turns || 0

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation.messages.length])

  return (
    <div
      className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm overflow-y-auto z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl bg-slate-800 rounded-lg shadow-2xl border border-slate-700"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-start p-6 border-b border-slate-700">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h3 className="text-xl font-serif font-semibold text-parchment-100">{name}</h3>
              {!isComplete && (
                <span className="flex items-center gap-1 text-sm text-strategic-500 font-medium">
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Live
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-2 text-sm text-parchment-200">
              <span className="flex items-center gap-1">
                <span className="font-medium">Turn:</span>
                <span className="font-bold text-parchment-100">{turns}</span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <span className="font-medium">Duration:</span>
                <span className="font-bold text-parchment-100">{duration}s</span>
              </span>
              <span>•</span>
              <span className={`font-medium ${
                isComplete
                  ? (conversation.success ? 'text-green-400' : 'text-red-400')
                  : 'text-strategic-500'
              }`}>
                {isComplete
                  ? (conversation.success ? '✓ Success' : '✗ Failed')
                  : '⟳ In Progress'
                }
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-parchment-300 hover:text-parchment-100 text-2xl font-bold ml-4 transition-colors"
          >
            ×
          </button>
        </div>

        {/* Failure details */}
        {isComplete && !conversation.success && (conversation.stop_reason || conversation.error_message) && (
          <div className="mx-6 mt-4 p-4 bg-red-950/30 border border-red-700 rounded-md">
            <div className="font-medium text-red-300 mb-1">Conversation Failed</div>
            {conversation.stop_reason && (
              <div className="text-sm text-red-400">
                <span className="font-medium">Reason:</span> {conversation.stop_reason}
              </div>
            )}
            {conversation.error_message && (
              <div className="text-sm text-red-400 mt-1">
                <span className="font-medium">Error:</span> {conversation.error_message}
              </div>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {conversation.messages.length === 0 ? (
            <div className="text-center py-12 text-parchment-300">
              <p>No messages yet...</p>
              {!isComplete && <p className="text-sm mt-2">Waiting for conversation to start</p>}
            </div>
          ) : (
            <div className="space-y-4">
              {conversation.messages.map((msg, i) => {
                const isLatest = i === conversation.messages.length - 1
                return (
                  <div
                    key={i}
                    className={`p-4 rounded-lg transition-all ${
                      msg.role === 'user'
                        ? 'bg-strategic-950/40 border-l-4 border-strategic-500'
                        : 'bg-slate-700/50 border-l-4 border-slate-600'
                    } ${isLatest && !isComplete ? 'ring-2 ring-strategic-600 animate-pulse' : ''}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs font-medium text-parchment-200">
                        {msg.role === 'user' ? '👤 User' : '🤖 Assistant'}
                      </div>
                      {msg.latency_ms && (
                        <div className="text-xs text-parchment-300">
                          {msg.latency_ms < 1000
                            ? `${msg.latency_ms.toFixed(0)}ms`
                            : `${(msg.latency_ms / 1000).toFixed(1)}s`
                          }
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-parchment-100 whitespace-pre-wrap">{msg.content}</div>
                  </div>
                )
              })}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Typing indicator for active conversations */}
          {!isComplete && conversation.messages.length > 0 && turns > conversation.messages.filter(m => m.role === 'user').length && (
            <div className="mt-4 p-4 bg-slate-700/50 rounded-lg border-l-4 border-slate-600">
              <div className="flex items-center gap-2 text-sm text-parchment-200">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-parchment-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 bg-parchment-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 bg-parchment-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
                <span>Agent is thinking...</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700 bg-slate-900 rounded-b-lg">
          <div className="flex justify-between items-center">
            <div className="text-sm text-parchment-200">
              {isComplete ? 'Conversation completed' : 'Updates every 2 seconds'}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-600 text-parchment-50 rounded-md hover:bg-slate-500 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
