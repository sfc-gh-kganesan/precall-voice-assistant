/**
 * Chat Header Component
 */

import React from 'react';

interface ChatHeaderProps {
  onClose: () => void;
  onResizeStart: (e: React.MouseEvent) => void;
  isConnected?: boolean;
  isProcessing?: boolean;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  onClose,
  onResizeStart,
  isConnected = true,
  isProcessing = false
}) => {
  // Determine status color and animation
  const getStatusStyle = () => {
    if (!isConnected) {
      return {
        backgroundColor: '#999',
        animation: 'none',
      };
    }
    if (isProcessing) {
      return {
        backgroundColor: '#2ecc71',
        animation: 'pulse 1.5s ease-in-out infinite',
      };
    }
    return {
      backgroundColor: '#2ecc71',
      animation: 'none',
    };
  };

  return (
    <>
      <style>
        {`
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
              transform: scale(1);
            }
            50% {
              opacity: 0.6;
              transform: scale(1.1);
            }
          }
        `}
      </style>
      <div
        id="snowflake-chat-header"
        style={{
          padding: '16px 20px',
          backgroundColor: '#1a1a1a',
          color: '#29b5e8',
          borderTopLeftRadius: '12px',
          borderTopRightRadius: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'relative',
        }}
      >
        {/* Resize Handle - Top Left Corner */}
        <div
          onMouseDown={onResizeStart}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '24px',
            height: '24px',
            cursor: 'nwse-resize',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: 0.7,
            transition: 'opacity 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.7')}
          title="Drag to resize"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="white">
            <path d="M0 0h2v2H0zm4 0h2v2H4zm0 4h2v2H4zM0 8h2v2H0zm4 0h2v2H4zm4 0h2v2H8z" opacity="0.8"/>
          </svg>
        </div>

        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, display: 'flex', alignItems: 'center' }}>
          <span
            className="status-indicator"
            style={{
              display: 'inline-block',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              marginRight: '8px',
              ...getStatusStyle(),
            }}
          />
          Snowflake Assistant
        </h3>
        <button
          id="snowflake-chat-close"
          onClick={onClose}
          aria-label="Close chat"
          style={{
            background: 'none',
            border: 'none',
            color: 'white',
            fontSize: '24px',
            cursor: 'pointer',
            padding: '0',
            width: '24px',
            height: '24px',
            lineHeight: '1',
          }}
        >
          &times;
        </button>
      </div>
    </>
  );
};
