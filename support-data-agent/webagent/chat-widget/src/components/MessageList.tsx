/**
 * Message List Component
 */

import React, { useEffect, useRef } from 'react';
import { Message } from './Message';
import type { Message as MessageType } from '../types';

interface MessageListProps {
  messages: MessageType[];
  isLoading: boolean;
  currentToolCalls: Set<string>;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, isLoading, currentToolCalls }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentToolCalls]);

  return (
    <div
      id="snowflake-chat-messages"
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        backgroundColor: '#eff1f3',
      }}
    >
      {messages.length === 0 && !isLoading && (
        <div className="welcome-message" style={{ textAlign: 'center', color: '#555' }}>
          <h4>👋 Welcome to Snowflake Support</h4>
          <p>I'm here to help you with:</p>
          <p>
            • Snowflake documentation and features<br />
            • Best practices and troubleshooting<br />
            • General technical questions
          </p>
          <p style={{ fontSize: '12px', color: '#999', marginTop: '16px' }}>
            💬 Type or 🎤 hold mic to speak
          </p>
        </div>
      )}
      
      {messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}

      {/* Tool calls are tracked but not displayed - just show loading dots */}

      {isLoading && (
        <div style={{ display: 'flex', gap: '6px', padding: '12px 16px', backgroundColor: '#f5f5f5', borderRadius: '20px', alignSelf: 'flex-start', width: '60px' }}>
          <span style={{ width: '8px', height: '8px', backgroundColor: '#999', borderRadius: '50%', animation: 'bounce 1s infinite' }} />
          <span style={{ width: '8px', height: '8px', backgroundColor: '#999', borderRadius: '50%', animation: 'bounce 1s infinite 0.2s' }} />
          <span style={{ width: '8px', height: '8px', backgroundColor: '#999', borderRadius: '50%', animation: 'bounce 1s infinite 0.4s' }} />
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};
