'use client'

import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '@/stores/appStore'
import { chatApi } from '@/services/api'
import { cn } from '@/lib/utils'
import { DEFAULTS, UI_CONSTANTS, ERROR_MESSAGES } from '@/lib/constants'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  suggestedQueries?: string[]
}

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const toggleChat = useAppStore((state) => state.toggleChat)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || input.length > UI_CONSTANTS.MAX_MESSAGE_LENGTH) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    try {
      const response = await chatApi.sendMessage(input, DEFAULTS.SESSION_ID)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        suggestedQueries: response.suggestedQueries,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat error:', error)
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `${ERROR_MESSAGES.CHAT_ERROR}: ${error instanceof Error ? error.message : ERROR_MESSAGES.UNKNOWN_ERROR}`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
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
        <button
          onClick={toggleChat}
          className="text-muted-foreground hover:text-foreground"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            Ask me anything about your support data!
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={cn(
            'flex',
            message.role === 'user' ? 'justify-end' : 'justify-start'
          )}>
            <div className={cn(
              'max-w-[80%] rounded-lg px-4 py-2',
              message.role === 'user'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted'
            )}>
              <p className="text-sm">{message.content}</p>

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
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-lg px-4 py-2">
              <div className="dots-pulse" />
            </div>
          </div>
        )}

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
            placeholder="Ask a question..."
            maxLength={UI_CONSTANTS.MAX_MESSAGE_LENGTH}
            className="flex-1 bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
        <div className="mt-1 text-xs text-muted-foreground text-right">
          {input.length}/{UI_CONSTANTS.MAX_MESSAGE_LENGTH}
        </div>
      </form>
    </div>
  )
}
