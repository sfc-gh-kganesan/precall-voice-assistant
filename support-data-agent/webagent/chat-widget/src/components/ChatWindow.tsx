/**
 * Chat Window Container
 */

import React, { useState } from 'react';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import { VoiceStatus } from './VoiceStatus';
import type { Message } from '../types';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  voiceStatus: string;
  voiceAvailable: boolean;
  currentToolCalls: Set<string>;
  voiceConnected: boolean;
  isAgentSpeaking: boolean;
  onClose: () => void;
  onSendMessage: (message: string) => void;
  onStartVoiceRecording: () => void;
  onStopVoiceRecording: () => void;
  onMuteVoice: () => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  voiceStatus,
  voiceAvailable,
  currentToolCalls,
  voiceConnected,
  isAgentSpeaking,
  onClose,
  onSendMessage,
  onStartVoiceRecording,
  onStopVoiceRecording,
  onMuteVoice,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 400, height: 600 });
  const [isResizing, setIsResizing] = useState(false);

  const handleStartRecording = () => {
    setIsRecording(true);
    onStartVoiceRecording();
  };

  const handleStopRecording = () => {
    setIsRecording(false);
    onStopVoiceRecording();
  };

  // Resize handler
  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);

    const startX = e.clientX;
    const startY = e.clientY;
    const startWidth = dimensions.width;
    const startHeight = dimensions.height;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      // Calculate deltas (negative = drag left/up)
      const deltaX = startX - moveEvent.clientX; // Drag left = positive delta = increase width
      const deltaY = startY - moveEvent.clientY; // Drag up = positive delta = increase height

      // Calculate new dimensions
      const newWidth = Math.max(300, Math.min(window.innerWidth - 40, startWidth + deltaX));
      const newHeight = Math.max(400, Math.min(window.innerHeight - 110, startHeight + deltaY));

      setDimensions({ width: newWidth, height: newHeight });
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // Determine if agent is processing (loading, tool calls, or voice status active)
  const isProcessing = isLoading || currentToolCalls.size > 0 || voiceStatus.length > 0;

  return (
    <div
      id="snowflake-chat-window"
      style={{
        position: 'fixed',
        bottom: '90px',
        right: '20px',
        width: `${dimensions.width}px`,
        height: `${dimensions.height}px`,
        backgroundColor: '#eff1f3',
        borderRadius: '12px',
        boxShadow: isResizing ? '0 12px 48px rgba(0,0,0,0.3)' : '0 12px 48px rgba(0,0,0,0.15)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000,
        transition: isResizing ? 'none' : 'box-shadow 0.2s',
      }}
    >
      <ChatHeader
        onClose={onClose}
        onResizeStart={handleResizeStart}
        isConnected={voiceConnected || voiceAvailable}
        isProcessing={isProcessing}
      />
      <MessageList messages={messages} isLoading={isLoading} currentToolCalls={currentToolCalls} />
      {voiceStatus && <VoiceStatus status={voiceStatus} />}
      <InputArea
        onSendMessage={onSendMessage}
        onStartRecording={handleStartRecording}
        onStopRecording={handleStopRecording}
        onMuteVoice={onMuteVoice}
        isRecording={isRecording}
        isAgentSpeaking={isAgentSpeaking}
        voiceAvailable={voiceAvailable}
        disabled={isLoading}
      />
    </div>
  );
};
