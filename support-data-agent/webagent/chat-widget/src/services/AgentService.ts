/**
 * Service for communicating with the Snowflake Agent backend
 */

import type { AgentQueryRequest, AgentQueryResponse } from '../types';

export class AgentService {
  private apiUrl: string;

  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }

  /**
   * Query the agent backend (non-streaming, for voice)
   */
  async query(message: string, conversationId: string): Promise<string> {
    console.log('[AgentService] Querying backend:', { message: message.substring(0, 50) });

    const request: AgentQueryRequest = {
      message,
      conversation_id: conversationId,
      stream: false,
    };

    const response = await fetch(`${this.apiUrl}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Agent API error: ${response.status} ${response.statusText}`);
    }

    const data: AgentQueryResponse = await response.json();
    console.log('[AgentService] Got response:', data.content.substring(0, 100));

    return data.content;
  }

  /**
   * Query the agent backend with streaming (for text chat)
   * Calls onChunk with cumulative text as it streams in
   */
  async queryStream(
    message: string,
    conversationId: string,
    onChunk: (text: string) => void,
    onComplete: (fullText: string) => void,
    onToolCall?: (toolName: string) => void,
    onToolResult?: (toolName: string) => void
  ): Promise<void> {
    console.log('[AgentService] Streaming query:', { message: message.substring(0, 50) });

    const request: AgentQueryRequest = {
      message,
      conversation_id: conversationId,
      stream: true,
    };

    const response = await fetch(`${this.apiUrl}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Agent API error: ${response.status} ${response.statusText}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete lines (SSE format)
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            // Event type line, we'll determine type from data content
            continue;
          }

          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6);
            try {
              const data = JSON.parse(dataStr);

              // Handle different event types based on the data structure
              // Check tool result first (has both tool and status)
              if (data.status === 'completed' && data.tool) {
                // Tool result event
                onToolResult?.(data.tool);
              } else if (data.tool) {
                // Tool call event (has tool but no status)
                onToolCall?.(data.tool);
              } else if (data.content) {
                // Text delta or final event
                fullResponse += data.content;
                onChunk(fullResponse);
              } else if (data.error) {
                throw new Error(data.error);
              }
            } catch (e) {
              console.warn('[AgentService] Failed to parse SSE data:', dataStr, e);
            }
          }
        }
      }

      console.log('[AgentService] Streaming complete, total length:', fullResponse.length);
      onComplete(fullResponse);
    } catch (error) {
      console.error('[AgentService] Streaming error:', error);
      throw error;
    }
  }

  /**
   * Check if voice is available
   */
  async checkVoiceAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.apiUrl}/api/v1/voice/available`);
      if (response.ok) {
        const data = await response.json();
        return data.available;
      }
      return false;
    } catch (error) {
      console.warn('[AgentService] Could not check voice availability:', error);
      return false;
    }
  }

  /**
   * Get ephemeral token for OpenAI Realtime API
   */
  async getVoiceToken(): Promise<string> {
    const response = await fetch(`${this.apiUrl}/api/v1/voice/token`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to get voice token');
    }

    const data = await response.json();
    return data.token;
  }
}
