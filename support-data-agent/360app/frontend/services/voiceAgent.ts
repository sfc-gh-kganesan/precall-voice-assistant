/**
 * Voice Agent Service
 *
 * Provides voice chat capabilities using OpenAI's Realtime API.
 * This service manages the RealtimeAgent connection, handles audio streaming,
 * transcriptions, and integrates with the backend Cortex Analyst.
 */

import { RealtimeAgent, RealtimeSession, tool } from '@openai/agents/realtime'
import { z } from 'zod'
import { API_CONFIG } from '@/lib/constants'

const API_BASE = API_CONFIG.BASE_URL

export type VoiceStatus = 'idle' | 'connecting' | 'connected' | 'listening' | 'processing' | 'speaking'

export interface VoiceMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface VoiceAgentCallbacks {
  onStatusChange?: (status: VoiceStatus) => void
  onMessage?: (message: VoiceMessage) => void
  onError?: (error: Error) => void
  onToolCall?: (toolName: string, status: 'started' | 'completed' | 'failed') => void
}

/**
 * Check if voice features are available (backend has OpenAI key configured)
 */
export async function checkVoiceAvailability(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/voice/available`)
    if (!response.ok) {
      console.error('Voice availability check failed:', response.statusText)
      return false
    }
    const data = await response.json()
    return data.available === true
  } catch (error) {
    console.error('Error checking voice availability:', error)
    return false
  }
}

/**
 * Generate an ephemeral token for voice connection
 */
async function generateEphemeralToken(): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/voice/token`, {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Failed to generate voice token: ${error}`)
  }

  const data = await response.json()
  return data.token
}

/**
 * Create the Cortex Analyst tool that integrates with the backend
 */
function createCortexAnalystTool() {
  return tool({
    name: 'query_cortex_analyst',
    description: `Query the support database for metrics, cases, and product information using natural language.
Use this tool when the user asks questions about data, metrics, reports, support tickets, or any database-related queries.

Examples of when to use this tool:
- "What were our top products last month?"
- "Show me support cases by category"
- "How many open tickets do we have?"
- Any data analysis or reporting questions`,
    parameters: z.object({
      query: z.string().describe("The user's natural language question about support data")
    }),
    async execute({ query }) {
      console.log(`[Voice Tool] Querying Cortex Analyst: ${query}`)

      try {
        // Prepare FormData to match the existing chat API
        const formData = new FormData()
        formData.append('message', query)

        const response = await fetch(`${API_BASE}/api/v1/chat/messages`, {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          throw new Error(`API error: ${response.status} ${response.statusText}`)
        }

        // Read the streaming response and accumulate the result
        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('No response body')
        }

        const decoder = new TextDecoder()
        let buffer = ''
        let fullResponse = ''

        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
              if (line.trim()) {
                try {
                  const data = JSON.parse(line)

                  // Accumulate model responses
                  if (data.role === 'model' && data.content) {
                    fullResponse = data.content
                  }
                } catch (e) {
                  console.error('Failed to parse JSON line:', line, e)
                }
              }
            }
          }
        } finally {
          reader.releaseLock()
        }

        if (!fullResponse) {
          return 'I queried the database but didn\'t receive any results.'
        }

        console.log('[Voice Tool] Query successful, response length:', fullResponse.length)
        return fullResponse

      } catch (error) {
        console.error('[Voice Tool] Error:', error)
        return `I'm sorry, I couldn't query the database. Error: ${error instanceof Error ? error.message : 'Unknown error'}`
      }
    }
  })
}

/**
 * Voice Agent class to manage the realtime session
 */
export class VoiceAgentManager {
  private session: RealtimeSession | null = null
  private agent: RealtimeAgent | null = null
  private callbacks: VoiceAgentCallbacks

  constructor(callbacks: VoiceAgentCallbacks = {}) {
    this.callbacks = callbacks
  }

  /**
   * Connect to the voice session
   */
  async connect(): Promise<void> {
    if (this.session) {
      console.warn('Voice session already connected')
      return
    }

    try {
      this.callbacks.onStatusChange?.('connecting')

      // Generate ephemeral token from backend
      const ephemeralToken = await generateEphemeralToken()

      // Create agent with instructions and tools
      this.agent = new RealtimeAgent({
        name: 'Support Data Assistant',
        instructions: `You are a helpful customer support data analyst assistant with access to a support database through the query_cortex_analyst tool.

**CRITICAL RULES - YOU MUST FOLLOW THESE:**
1. **NEVER make up, guess, or speculate about data.** You must ONLY answer based on the actual results returned by the query_cortex_analyst tool.
2. **WAIT for tool results.** Do NOT start answering the user's question until AFTER you receive the tool's response.
3. **DO NOT ANSWER PREMATURELY.** Even if the tool is taking a long time, DO NOT make up an answer. Instead, say "Still checking the database, give me just a moment" and continue waiting.
4. **If you don't have data, say so.** If the tool returns no results or an error, tell the user honestly - don't fabricate information.
5. **Only use tool outputs.** Your responses must be based solely on what the query_cortex_analyst tool returns. Do not use your training data knowledge about their support data.

**LANGUAGE MATCHING:**
Always respond in the SAME LANGUAGE that the user speaks to you in. If they speak Spanish, respond in Spanish. If they speak English, respond in English, etc.

**HOW TO HANDLE QUERIES:**
1. When the user asks about support data, metrics, cases, or products, immediately call the query_cortex_analyst tool
2. You can say "Let me check that for you" or "One moment, checking the database" BEFORE calling the tool
3. WAIT for the tool to return results
4. If it's taking longer than expected, you can say "Still searching the database, just a moment please" - but DO NOT provide an answer yet
5. AFTER receiving tool results, summarize the findings clearly and conversationally
6. Focus on the most important numbers and insights from the actual results

**EXAMPLE:**
User: "Which product had the most cases?"
You: "Let me check that for you." [calls tool, WAITS for response]
[If taking long]: "Still checking the database, give me just a moment..."
[Tool returns: User Access & Password Reset - 1,204 cases]
You: "Based on the database, User Access and Password Reset had the most cases with 1,204 new cases."

**WHAT NOT TO DO:**
❌ NEVER say things like "I think it might be..." or "It's probably..." before the tool returns
❌ NEVER provide specific numbers or data before the tool returns
❌ NEVER start answering the question while the tool is still running

Remember: WAIT for tool results. If it's taking time, tell the user you're still checking - but DO NOT make up an answer.`,
        tools: [createCortexAnalystTool()]
      })

      // Create session with input transcription enabled and VAD disabled (PTT mode)
      this.session = new RealtimeSession(this.agent, {
        model: 'gpt-realtime',
        config: {
          audio: {
            input: {
              transcription: {
                model: 'whisper-1'
              }
            }
          }
        }
      })

      // Set up event listeners
      this.setupEventListeners()

      // Connect to the session
      await this.session.connect({ apiKey: ephemeralToken })

      console.log('[Voice Agent] Session connected, waiting before disabling VAD')

      // IMPORTANT: Disable VAD after connection to enable PTT mode
      // Add a small delay to ensure connection is fully established
      // Must be sent after session is connected
      try {
        // Wait a moment for connection to stabilize
        await new Promise(resolve => setTimeout(resolve, 100))

        this.session.transport.sendEvent({
          type: 'session.update',
          session: {
            type: 'realtime',  // Required by OpenAI Realtime API
            audio: {
              input: {
                turn_detection: null
              }
            }
          }
        } as unknown)

        console.log('[Voice Agent] VAD disabled successfully for PTT mode')
      } catch (error) {
        console.error('[Voice Agent] Error disabling VAD:', error)
        throw new Error(`Failed to configure PTT mode: ${error}`)
      }

      this.callbacks.onStatusChange?.('connected')
      console.log('[Voice Agent] Connected successfully')

    } catch (error) {
      console.error('[Voice Agent] Connection error:', error)
      this.callbacks.onStatusChange?.('idle')
      this.callbacks.onError?.(error instanceof Error ? error : new Error(String(error)))
      throw error
    }
  }

  /**
   * Disconnect from the voice session
   */
  async disconnect(): Promise<void> {
    if (this.session) {
      try {
        this.session.close()
      } catch (error) {
        console.error('[Voice Agent] Error disconnecting:', error)
      }
      this.session = null
      this.agent = null
    }
    this.callbacks.onStatusChange?.('idle')
    console.log('[Voice Agent] Disconnected')
  }

  /**
   * Start push-to-talk recording
   */
  startPushToTalk(): void {
    if (!this.session) {
      console.warn('Cannot start recording: session not connected')
      return
    }

    // Clear any previous audio in the buffer before starting new recording
    this.session.transport.sendEvent({
      type: 'input_audio_buffer.clear'
    })

    this.callbacks.onStatusChange?.('listening')
    console.log('[Voice Agent] Recording started, buffer cleared')
  }

  /**
   * Stop push-to-talk recording
   */
  stopPushToTalk(): void {
    if (!this.session) return

    // Commit the audio buffer to create a conversation item
    this.session.transport.sendEvent({
      type: 'input_audio_buffer.commit'
    })

    // Trigger a response from the model
    this.session.transport.sendEvent({
      type: 'response.create'
    })

    this.callbacks.onStatusChange?.('connected')
    console.log('[Voice Agent] Recording stopped, audio committed, response requested')
  }

  /**
   * Toggle continuous listening mode
   */
  toggleContinuousListening(enabled: boolean): void {
    if (!this.session) {
      console.warn('Cannot toggle continuous listening: session not connected')
      return
    }

    // Update session to enable/disable VAD
    // Note: Using snake_case for raw server events (not TypeScript config format)
    this.session.transport.sendEvent({
      type: 'session.update',
      session: {
        type: 'realtime',  // Required by OpenAI Realtime API
        audio: {
          input: {
            turn_detection: enabled ? {
              type: 'semantic_vad'
            } : null
          }
        }
      }
    } as unknown) // Cast to unknown because we're using snake_case for server format

    console.log(`[Voice Agent] Continuous listening ${enabled ? 'enabled' : 'disabled'}`)
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.session !== null
  }

  /**
   * Set up event listeners for the session
   */
  private setupEventListeners(): void {
    if (!this.session) return

    const session = this.session

    // Tool call events (using high-level agent events)
    session.on('agent_tool_start', (_context, _agent, tool, _details) => {
      console.log('[Voice Agent] Tool call started:', tool.name)
      this.callbacks.onStatusChange?.('processing')
      this.callbacks.onToolCall?.(tool.name, 'started')
    })

    session.on('agent_tool_end', (_context, _agent, tool, _result, _details) => {
      console.log('[Voice Agent] Tool call completed:', tool.name)
      this.callbacks.onToolCall?.(tool.name, 'completed')
    })

    // User speech transcription (via transport events)
    session.on('transport_event', (event: Record<string, unknown>) => {
      // Log all transport events during development to debug issues
      if (event.type.includes('error')) {
        console.error('[Voice Agent] Transport error event:', JSON.stringify(event, null, 2))
      }

      // Listen for input audio transcription completed
      if (event.type === 'conversation.item.input_audio_transcription.completed') {
        if (event.transcript) {
          console.log('[Voice Agent] User said:', event.transcript)
          this.callbacks.onMessage?.({
            id: `user-${Date.now()}`,
            role: 'user',
            content: event.transcript,
            timestamp: new Date()
          })
        }
      }

      // Listen for input audio transcription failures
      if (event.type === 'conversation.item.input_audio_transcription.failed') {
        console.error('[Voice Agent] Transcription failed:', event.error)
        this.callbacks.onMessage?.({
          id: `error-${Date.now()}`,
          role: 'system',
          content: 'Could not transcribe audio',
          timestamp: new Date()
        })
      }

      // Listen for assistant audio output transcript
      if (event.type === 'response.output_audio_transcript.done') {
        if (event.transcript) {
          console.log('[Voice Agent] Assistant said:', event.transcript)
          this.callbacks.onMessage?.({
            id: event.item_id || `assistant-${Date.now()}`,
            role: 'assistant',
            content: event.transcript,
            timestamp: new Date()
          })
        }
      }
    })

    // History updates (for assistant messages)
    session.on('history_added', (item: Record<string, unknown>) => {
      console.log('[Voice Agent] History item added:', item)

      // If it's an assistant message with content, add it to chat
      if (item.role === 'assistant' && item.content && Array.isArray(item.content)) {
        // Extract text content
        const textContent = item.content
          .filter((c: Record<string, unknown>) => c.type === 'text')
          .map((c: Record<string, unknown>) => c.text as string)
          .join('')

        if (textContent) {
          console.log('[Voice Agent] Assistant response:', textContent)
          this.callbacks.onMessage?.({
            id: item.id || `assistant-${Date.now()}`,
            role: 'assistant',
            content: textContent,
            timestamp: new Date()
          })
        }
      }
    })

    // Audio playback status
    session.on('audio_start', () => {
      this.callbacks.onStatusChange?.('speaking')
    })

    session.on('audio_stopped', () => {
      this.callbacks.onStatusChange?.('connected')
    })

    // Error handling
    session.on('error', (error: Record<string, unknown>) => {
      console.error('[Voice Agent] Session error (raw):', error)
      console.error('[Voice Agent] Session error (JSON):', JSON.stringify(error, null, 2))

      // Try to extract error message from various possible structures
      let errorMessage = 'Unknown session error'
      if (error?.error?.message) {
        errorMessage = error.error.message
      } else if (error?.message) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      } else if (Object.keys(error || {}).length > 0) {
        errorMessage = `Session error: ${JSON.stringify(error)}`
      }

      const err = new Error(errorMessage)
      this.callbacks.onError?.(err)
    })
  }
}
