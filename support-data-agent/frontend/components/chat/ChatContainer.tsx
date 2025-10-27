'use client'

import { useAppStore } from '@/stores/appStore'
import { ChatWindow } from './ChatWindow'

export function ChatContainer() {
  const chatOpen = useAppStore((state) => state.chatOpen)
  const toggleChat = useAppStore((state) => state.toggleChat)

  return (
    <>
      {/* Chat Window */}
      {chatOpen && <ChatWindow />}

      {/* Chat Toggle Button */}
      <button
        onClick={toggleChat}
        className="fixed bottom-4 right-4 w-14 h-14 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 hover:scale-110 transition-all flex items-center justify-center ring-2 ring-primary/20"
        aria-label="Toggle chat"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </button>
    </>
  )
}
