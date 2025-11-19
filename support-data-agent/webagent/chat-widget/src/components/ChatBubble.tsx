/**
 * Floating Chat Bubble Button
 */

import React from 'react';

interface ChatBubbleProps {
  onClick: () => void;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({ onClick }) => {
  return (
    <button
      id="snowflake-chat-bubble"
      onClick={onClick}
      aria-label="Open Snowflake Chat"
      style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        width: '60px',
        height: '60px',
        borderRadius: '50%',
        backgroundColor: '#29b5e8',
        border: 'none',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 999,
      }}
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style={{ width: '32px', height: '32px', fill: 'white' }}>
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
        <path d="M7 9h10v2H7zm0-3h10v2H7zm0 6h7v2H7z"/>
      </svg>
    </button>
  );
};
