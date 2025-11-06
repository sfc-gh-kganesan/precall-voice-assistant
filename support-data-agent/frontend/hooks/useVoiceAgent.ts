/**
 * useVoiceAgent Hook
 *
 * React hook for managing voice agent functionality.
 * Integrates with Zustand store and provides voice capabilities.
 */

import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '@/stores/appStore'
import { VoiceAgentManager, checkVoiceAvailability, type VoiceMessage } from '@/services/voiceAgent'

export function useVoiceAgent() {
  const agentRef = useRef<VoiceAgentManager | null>(null)
  const [isChecking, setIsChecking] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Get state and actions from Zustand store
  const voiceAvailable = useAppStore((state) => state.voiceAvailable)
  const voiceEnabled = useAppStore((state) => state.voiceEnabled)
  const voiceStatus = useAppStore((state) => state.voiceStatus)
  const pushToTalkActive = useAppStore((state) => state.pushToTalkActive)
  const continuousListening = useAppStore((state) => state.continuousListening)
  const setVoiceAvailable = useAppStore((state) => state.setVoiceAvailable)
  const toggleVoice = useAppStore((state) => state.toggleVoice)
  const setVoiceStatus = useAppStore((state) => state.setVoiceStatus)
  const setPushToTalk = useAppStore((state) => state.setPushToTalk)
  const toggleContinuousListening = useAppStore((state) => state.toggleContinuousListening)
  const addMessage = useAppStore((state) => state.addMessage)
  const _updateMessage = useAppStore((state) => state.updateMessage)

  // Check voice availability on mount
  useEffect(() => {
    async function checkAvailability() {
      try {
        const available = await checkVoiceAvailability()
        setVoiceAvailable(available)
        console.log(`[useVoiceAgent] Voice availability: ${available}`)
      } catch (error) {
        console.error('[useVoiceAgent] Error checking voice availability:', error)
        setVoiceAvailable(false)
      } finally {
        setIsChecking(false)
      }
    }

    checkAvailability()
  }, [setVoiceAvailable])

  // Initialize voice agent when enabled
  useEffect(() => {
    if (!voiceEnabled || !voiceAvailable) {
      return
    }

    async function initializeAgent() {
      if (agentRef.current) {
        console.warn('[useVoiceAgent] Agent already initialized')
        return
      }

      try {
        setError(null)

        // Create agent with callbacks
        const agent = new VoiceAgentManager({
          onStatusChange: (status) => {
            console.log(`[useVoiceAgent] Status changed: ${status}`)
            setVoiceStatus(status)
          },
          onMessage: (message: VoiceMessage) => {
            console.log('[useVoiceAgent] Message:', message.role, message.content.substring(0, 50))
            addMessage({
              id: message.id,
              role: message.role === 'system' ? 'tool_status' : message.role,
              content: message.content,
              timestamp: message.timestamp,
            })
          },
          onError: (err) => {
            console.error('[useVoiceAgent] Error:', err)
            setError(err.message)
          },
          onToolCall: (toolName, status) => {
            console.log(`[useVoiceAgent] Tool: ${toolName}, status: ${status}`)
            if (status === 'started') {
              addMessage({
                id: `tool-${toolName}-${Date.now()}`,
                role: 'tool_status',
                content: '',
                timestamp: new Date(),
                toolName,
                status: 'running',
              })
            }
          },
        })

        agentRef.current = agent
        await agent.connect()

        console.log('[useVoiceAgent] Agent connected successfully')
      } catch (error) {
        console.error('[useVoiceAgent] Failed to initialize agent:', error)
        setError(error instanceof Error ? error.message : 'Failed to connect to voice service')
        toggleVoice() // Turn off voice mode on error
      }
    }

    initializeAgent()

    // Cleanup on unmount or when voice disabled
    return () => {
      if (agentRef.current) {
        console.log('[useVoiceAgent] Disconnecting agent')
        agentRef.current.disconnect()
        agentRef.current = null
      }
    }
  }, [voiceEnabled, voiceAvailable, setVoiceStatus, addMessage, toggleVoice])

  // Handle push-to-talk
  const startPushToTalk = () => {
    if (agentRef.current && agentRef.current.isConnected()) {
      setPushToTalk(true)
      agentRef.current.startPushToTalk()
    }
  }

  const stopPushToTalk = () => {
    if (agentRef.current) {
      setPushToTalk(false)
      agentRef.current.stopPushToTalk()
    }
  }

  // Handle continuous listening toggle
  const handleToggleContinuousListening = () => {
    if (agentRef.current && agentRef.current.isConnected()) {
      const newValue = !continuousListening
      toggleContinuousListening() // Update Zustand store
      agentRef.current.toggleContinuousListening(newValue) // Update session
    }
  }

  // Connect/disconnect
  const connect = async () => {
    if (!voiceAvailable) {
      console.warn('[useVoiceAgent] Voice not available')
      return
    }
    toggleVoice()
  }

  const disconnect = async () => {
    if (agentRef.current) {
      await agentRef.current.disconnect()
      agentRef.current = null
    }
    toggleVoice()
  }

  return {
    // State
    isAvailable: voiceAvailable,
    isChecking,
    isEnabled: voiceEnabled,
    isConnected: voiceStatus !== 'idle',
    status: voiceStatus,
    pushToTalkActive,
    continuousListening,
    error,

    // Actions
    connect,
    disconnect,
    startPushToTalk,
    stopPushToTalk,
    toggleContinuousListening: handleToggleContinuousListening,
  }
}
