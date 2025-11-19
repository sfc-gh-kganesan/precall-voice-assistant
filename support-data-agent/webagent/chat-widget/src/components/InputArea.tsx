/**
 * Input Area with Fin-Style Design
 */

import React, { useState, useRef, KeyboardEvent } from 'react';

interface InputAreaProps {
  onSendMessage: (message: string) => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onMuteVoice: () => void;
  isRecording: boolean;
  isAgentSpeaking: boolean;
  voiceAvailable: boolean;
  disabled: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({
  onSendMessage,
  onStartRecording,
  onStopRecording,
  onMuteVoice,
  isRecording,
  isAgentSpeaking,
  voiceAvailable,
  disabled,
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const autoResize = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
    }
  };

  return (
    <div
      id="snowflake-chat-input-area"
      style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      {/* Input Container with Icons Inside */}
      <div
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          border: '1.5px solid #e0e0e0',
          borderRadius: '24px',
          backgroundColor: 'white',
          paddingLeft: '16px',
          paddingRight: message.trim() ? '8px' : '16px',
          transition: 'border-color 0.2s',
        }}
        onFocus={() => {
          const container = document.getElementById('input-container');
          if (container) container.style.borderColor = '#29b5e8';
        }}
        onBlur={() => {
          const container = document.getElementById('input-container');
          if (container) container.style.borderColor = '#e0e0e0';
        }}
        id="input-container"
      >
        {/* Left Icons */}
        <div style={{ display: 'flex', gap: '8px', marginRight: '12px', alignItems: 'center' }}>
          {/* Attachment Icon (placeholder) */}
          <button
            title="Attach file"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
              opacity: 0.5,
            }}
            disabled
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#666">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          {/* Emoji Icon (placeholder) */}
          <button
            title="Add emoji"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
              opacity: 0.5,
            }}
            disabled
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#666">
              <circle cx="12" cy="12" r="10" strokeWidth="2"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2" strokeWidth="2" strokeLinecap="round"/>
              <line x1="9" y1="9" x2="9.01" y2="9" strokeWidth="2" strokeLinecap="round"/>
              <line x1="15" y1="9" x2="15.01" y2="9" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>

          {/* Voice/Mic Icon */}
          {voiceAvailable && (
            <button
              onClick={() => {
                // Simple click when agent is speaking = mute only
                if (isAgentSpeaking) {
                  onMuteVoice();
                }
              }}
              onMouseDown={() => {
                // Hold-to-talk only when agent NOT speaking
                if (!isAgentSpeaking) {
                  onStartRecording();
                }
              }}
              onMouseUp={() => {
                // Stop recording only if actually recording
                if (isRecording && !isAgentSpeaking) {
                  onStopRecording();
                }
              }}
              onTouchStart={(e) => {
                e.preventDefault();
                // Touch: click to mute if agent speaking
                if (isAgentSpeaking) {
                  onMuteVoice();
                } else {
                  // Otherwise start recording (hold-to-talk)
                  onStartRecording();
                }
              }}
              onTouchEnd={(e) => {
                e.preventDefault();
                // Stop recording only if actually recording
                if (isRecording && !isAgentSpeaking) {
                  onStopRecording();
                }
              }}
              title={isAgentSpeaking ? 'Click to mute' : 'Hold to speak'}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
                opacity: isRecording || isAgentSpeaking ? 1 : 0.6,
              }}
            >
              {isAgentSpeaking ? (
                // Microphone with indicator when agent is speaking (ready to interrupt)
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" fill="#ff4444"/>
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" fill="#ff4444"/>
                  {/* Animated pulse to indicate agent is speaking */}
                  <circle cx="12" cy="12" r="10" fill="none" stroke="#ff4444" strokeWidth="1" opacity="0.3">
                    <animate attributeName="r" from="8" to="12" dur="1s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" from="0.5" to="0" dur="1s" repeatCount="indefinite"/>
                  </circle>
                </svg>
              ) : (
                // Microphone icon
                <svg width="18" height="18" viewBox="0 0 24 24" fill={isRecording ? '#ff4444' : '#666'}>
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                </svg>
              )}
            </button>
          )}
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          id="snowflake-chat-input"
          placeholder="Message..."
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          style={{
            flex: 1,
            padding: '10px 0',
            border: 'none',
            outline: 'none',
            fontSize: '14px',
            resize: 'none',
            fontFamily: 'inherit',
            maxHeight: '100px',
            overflowY: 'auto',
            backgroundColor: 'transparent',
          }}
        />

        {/* Send Button (always visible, grayed when empty) */}
        <button
          id="snowflake-chat-send"
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          aria-label="Send message"
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            border: 'none',
            backgroundColor: message.trim() ? '#29b5e8' : '#d0d0d0',
            color: 'white',
            cursor: disabled || !message.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginLeft: '8px',
            flexShrink: 0,
            opacity: message.trim() ? 1 : 0.5,
            transition: 'background-color 0.2s, opacity 0.2s',
          }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style={{ width: '18px', height: '18px', fill: 'white', transform: 'rotate(-90deg)' }}>
            <path d="M7 10l5 5 5-5z"/>
          </svg>
        </button>
      </div>

      {/* Powered by Snowflake */}
      <div style={{ textAlign: 'center', fontSize: '11px', color: '#999' }}>
        Powered by Snowflake
      </div>
    </div>
  );
};
