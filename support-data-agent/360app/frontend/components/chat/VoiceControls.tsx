/**
 * VoiceControls Component
 *
 * Provides UI controls for voice chat functionality:
 * - Microphone toggle button (enable/disable voice mode)
 * - Push-to-talk button
 * - Continuous listening toggle
 * - Status indicators
 */

import { useVoiceAgent } from '@/hooks/useVoiceAgent'
import { cn } from '@/lib/utils'

export function VoiceControls() {
  const {
    isAvailable,
    isChecking,
    isEnabled,
    isConnected,
    status,
    pushToTalkActive,
    continuousListening,
    error,
    connect,
    disconnect,
    startPushToTalk,
    stopPushToTalk,
    toggleContinuousListening,
  } = useVoiceAgent()

  // Determine microphone button state
  const getMicButtonClasses = () => {
    if (!isAvailable || isChecking) {
      return 'opacity-40 cursor-not-allowed'
    }
    if (isEnabled) {
      return 'text-primary hover:text-primary/80'
    }
    return 'text-muted-foreground hover:text-foreground'
  }

  const getMicTitle = () => {
    if (isChecking) return 'Checking voice availability...'
    if (!isAvailable) return 'Voice chat unavailable - OpenAI API key not configured'
    if (isEnabled) return 'Disable voice chat'
    return 'Enable voice chat'
  }

  const getStatusText = () => {
    switch (status) {
      case 'connecting':
        return 'Connecting...'
      case 'connected':
        return 'Ready'
      case 'listening':
        return 'Listening...'
      case 'processing':
        return 'Processing...'
      case 'speaking':
        return 'Speaking...'
      default:
        return null
    }
  }

  const handleMicClick = () => {
    if (!isAvailable || isChecking) return

    if (isEnabled) {
      disconnect()
    } else {
      connect()
    }
  }

  return (
    <div className="flex items-center gap-2">
      {/* Microphone Toggle Button */}
      <button
        onClick={handleMicClick}
        disabled={!isAvailable || isChecking}
        title={getMicTitle()}
        className={cn(
          'p-2 rounded-md transition-colors',
          getMicButtonClasses()
        )}
      >
        {isEnabled ? (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 12c1.104 0 2-.896 2-2V4c0-1.104-.896-2-2-2S8 2.896 8 4v6c0 1.104.896 2 2 2z" />
            <path d="M14 8c-.552 0-1 .448-1 1v1c0 1.654-1.346 3-3 3s-3-1.346-3-3V9c0-.552-.448-1-1-1s-1 .448-1 1v1c0 2.434 1.721 4.463 4 4.898V17H7c-.552 0-1 .448-1 1s.448 1 1 1h6c.552 0 1-.448 1-1s-.448-1-1-1h-2v-2.102c2.279-.435 4-2.464 4-4.898V9c0-.552-.448-1-1-1z" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        )}
      </button>

      {/* Voice Controls - Only show when voice is enabled */}
      {isEnabled && isConnected && (
        <div className="flex items-center gap-2">
          {/* Hold to Speak Button - Only show in PTT mode */}
          {!continuousListening && (
            <button
              onMouseDown={startPushToTalk}
              onMouseUp={stopPushToTalk}
              onTouchStart={(e) => {
                e.preventDefault()
                startPushToTalk()
              }}
              onTouchEnd={(e) => {
                e.preventDefault()
                stopPushToTalk()
              }}
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                pushToTalkActive
                  ? 'bg-red-500 text-white animate-pulse'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90'
              )}
            >
              {pushToTalkActive ? '🔴 Recording' : '🎤 Hold to Speak'}
            </button>
          )}

          {/* Continuous Listening Toggle */}
          <button
            onClick={toggleContinuousListening}
            className={cn(
              'px-2 py-1 rounded text-xs transition-colors',
              continuousListening
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            )}
            title={continuousListening ? 'Disable continuous listening' : 'Enable continuous listening'}
          >
            {continuousListening ? '🔊 Always Listening' : '🔇 PTT Mode'}
          </button>

          {/* Status Indicator */}
          {getStatusText() && (
            <span className="text-xs text-muted-foreground">
              {getStatusText()}
            </span>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <span className="text-xs text-destructive" title={error}>
          ⚠ {error.substring(0, 30)}{error.length > 30 ? '...' : ''}
        </span>
      )}
    </div>
  )
}
