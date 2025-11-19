/**
 * TypeScript types for Snowflake Chat Widget with Voice Support
 */

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'agent';
  label?: string;
  timestamp: Date;
  isTyping?: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  status: 'active' | 'completed';
}

export interface VoiceSessionConfig {
  apiUrl: string;
  conversationId: string;
  conversationHistory?: Message[]; // Previous messages for context
  onTranscript?: (text: string) => void;
  onResponse?: (text: string, isStreaming?: boolean) => void;
  onError?: (error: Error) => void;
  onStatusChange?: (status: VoiceStatus) => void;
  onToolCall?: (toolName: string) => void;
  onToolResult?: (toolName: string) => void;
}

export type VoiceStatus = 'idle' | 'connecting' | 'connected' | 'listening' | 'processing' | 'error';

export interface ChatConfig {
  apiUrl: string;
  conversationId: string;
  maxRetries: number;
  retryDelay: number;
}

export interface AgentQueryRequest {
  message: string;
  conversation_id: string;
  stream?: boolean;
}

export interface AgentQueryResponse {
  content: string;
}

// OpenAI Realtime API types
export interface RealtimeSession {
  type: 'realtime';
  model: string;
  instructions: string;
  tools?: RealtimeTool[];
  audio: {
    input: {
      format: { type: string; rate: number };
      transcription: { model: string };
      turn_detection: null;
    };
    output: {
      voice: string;
      format: { type: string; rate: number };
    };
  };
}

export interface RealtimeTool {
  type: 'function';
  name: string;
  description: string;
  parameters: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
}

export interface RealtimeEvent {
  type: string;
  [key: string]: any;
}
