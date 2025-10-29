'use client'

import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { useAppStore } from '@/stores/appStore'
import { chatApi } from '@/services/api'
import { cn } from '@/lib/utils'
import { UI_CONSTANTS, ERROR_MESSAGES } from '@/lib/constants'
import { VoiceControls } from './VoiceControls'

export function ChatWindow() {
  const messages = useAppStore((state) => state.messages)
  const addMessage = useAppStore((state) => state.addMessage)
  const updateMessage = useAppStore((state) => state.updateMessage)
  const toggleChat = useAppStore((state) => state.toggleChat)
  const voiceEnabled = useAppStore((state) => state.voiceEnabled)

  const [input, setInput] = useState('')
  const [messageHistory, setMessageHistory] = useState<any[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || input.length > UI_CONSTANTS.MAX_MESSAGE_LENGTH) return

    const messageText = input.trim()
    setInput('')

    try {
      // Pass message history to API and capture updated history
      const updatedHistory = await chatApi.streamMessage(messageText, messageHistory, (data) => {
        if (data.role === 'user') {
          // Echo the user message
          addMessage({
            id: Date.now().toString(),
            role: 'user',
            content: data.content || '',
            timestamp: new Date(data.timestamp),
          })

          // Immediately create an empty assistant message placeholder
          const assistantMessageId = (Date.now() + 1).toString()
          addMessage({
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
          })

          // Store the ID in a way that's accessible to subsequent chunks
          ;(handleSend as any).currentAssistantId = assistantMessageId
        } else if (data.role === 'tool_status') {
          // Handle tool execution status messages
          // Add timestamp to ID to make each tool invocation unique
          const toolMessageId = `tool-${data.tool_name}-${Date.now()}`

          if (data.status === 'running') {
            // Add a new tool status message with unique ID
            addMessage({
              id: toolMessageId,
              role: 'tool_status',
              content: '',
              timestamp: new Date(data.timestamp),
              toolName: data.tool_name,
              status: 'running',
            })

            // Store the ID so we can update it when completed
            ;(handleSend as any).currentToolId = toolMessageId
          } else if (data.status === 'completed') {
            // Update the existing tool status message using stored ID
            const storedToolId = (handleSend as any).currentToolId
            if (storedToolId) {
              updateMessage(storedToolId, {
                status: 'completed',
                timestamp: new Date(data.timestamp),
              })
            }
          }
        } else if (data.role === 'model') {
          // Update the existing assistant message with accumulated content
          const assistantId = (handleSend as any).currentAssistantId
          if (assistantId) {
            updateMessage(assistantId, {
              content: data.content || '',
              timestamp: new Date(data.timestamp)
            })
          }
        }
        // Note: history_update messages are captured by the API, not displayed
      })

      // Update message history state with the returned history
      setMessageHistory(updatedHistory)
    } catch (error) {
      console.error('Chat error:', error)

      addMessage({
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `${ERROR_MESSAGES.CHAT_ERROR}: ${error instanceof Error ? error.message : ERROR_MESSAGES.UNKNOWN_ERROR}`,
        timestamp: new Date(),
      })
    } finally {
      // Clean up the stored IDs
      delete (handleSend as any).currentAssistantId
      delete (handleSend as any).currentToolId
    }
  }

  const handleSuggestedQuery = (query: string) => {
    setInput(query)
    inputRef.current?.focus()
  }

  return (
    <div className="fixed bottom-20 right-4 w-96 h-[600px] bg-card border border-border rounded-lg shadow-xl flex flex-col hidden md:flex">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h3 className="font-semibold">Support Assistant</h3>
        <div className="flex items-center gap-2">
          <VoiceControls />
          <button
            onClick={toggleChat}
            className="text-muted-foreground hover:text-foreground"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            Ask me anything about your support data!
          </div>
        )}

        {messages.map((message) => {
          // Special rendering for tool status messages
          if (message.role === 'tool_status') {
            return (
              <div key={message.id} className="flex justify-start">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 border border-primary/20 rounded-full text-xs">
                  {message.status === 'running' ? (
                    <>
                      <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                      <span className="text-primary font-medium">
                        Querying database...
                      </span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-success font-medium">
                        Query completed
                      </span>
                    </>
                  )}
                </div>
              </div>
            )
          }

          // Regular user/assistant messages
          return (
            <div key={message.id} className={cn(
              'flex',
              message.role === 'user' ? 'justify-end' : 'justify-start'
            )}>
              <div className={cn(
                'max-w-[80%] rounded-lg px-4 py-2',
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-muted'
              )}>
                <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-1">
                  {message.content.trim() ? (
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  ) : (
                    <div className="flex items-center gap-2 text-muted-foreground italic animate-pulse">
                      <span>💭 Thinking...</span>
                    </div>
                  )}
                </div>

                {/* Suggested Queries */}
                {message.suggestedQueries && (
                  <div className="mt-2 pt-2 border-t border-border/20">
                    <p className="text-xs opacity-70 mb-1">Suggested:</p>
                    <div className="space-y-1">
                      {message.suggestedQueries.map((query, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSuggestedQuery(query)}
                          className="block text-xs text-left hover:underline"
                        >
                          {query}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSend()
        }}
        className="p-4 border-t border-border"
      >
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={voiceEnabled ? "Voice mode active" : "Ask a question..."}
            maxLength={UI_CONSTANTS.MAX_MESSAGE_LENGTH}
            disabled={voiceEnabled}
            className={cn(
              "flex-1 bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary",
              voiceEnabled && "opacity-50 cursor-not-allowed"
            )}
          />
          <button
            type="submit"
            disabled={!input.trim() || voiceEnabled}
            className="bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
        <div className="mt-1 text-xs text-muted-foreground text-right">
          {voiceEnabled ? "Voice mode enabled - use microphone" : `${input.length}/${UI_CONSTANTS.MAX_MESSAGE_LENGTH}`}
        </div>
      </form>
    </div>
  )
}
