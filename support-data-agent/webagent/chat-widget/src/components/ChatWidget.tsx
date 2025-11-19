/**
 * Main Chat Widget Component
 */

import React, { useState, useEffect, useRef } from 'react';
import { ChatBubble } from './ChatBubble';
import { ChatWindow } from './ChatWindow';
import { VoiceService } from '../services/VoiceService';
import { AgentService } from '../services/AgentService';
import type { Message } from '../types';

interface ChatWidgetProps {
  apiUrl: string;
  conversationId: string;
}

export const ChatWidget: React.FC<ChatWidgetProps> = ({ apiUrl, conversationId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [voiceService, setVoiceService] = useState<VoiceService | null>(null);
  const [agentService] = useState(() => new AgentService(apiUrl));
  const [voiceStatus, setVoiceStatus] = useState('');
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [voiceConnected, setVoiceConnected] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<Set<string>>(new Set());
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);

  // Use ref instead of state for synchronous updates during streaming
  const currentStreamingMessageIdRef = useRef<string | null>(null);
  // Track if user message was added (to prevent agent responding before user message)
  const userMessageAddedRef = useRef(false);

  // Check voice availability on mount
  useEffect(() => {
    checkVoiceAvailability();
  }, []);

  const checkVoiceAvailability = async () => {
    const available = await agentService.checkVoiceAvailable();
    setVoiceAvailable(available);
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  const addMessage = (content: string, role: 'user' | 'agent', label?: string) => {
    const message: Message = {
      id: `${Date.now()}-${Math.random()}`, // Prevent ID collisions
      content,
      role,
      label,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, message]);
    return message;
  };

  return (
    <div className="snowflake-chat-widget">
      <ChatBubble onClick={toggleChat} />
      {isOpen && (
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          voiceStatus={voiceStatus}
          voiceAvailable={voiceAvailable}
          voiceConnected={voiceConnected}
          currentToolCalls={currentToolCalls}
          onClose={toggleChat}
          onSendMessage={async (message) => {
            addMessage(message, 'user', 'You');
            setIsLoading(true);

            // Track the agent message ID (will be created on first chunk)
            let agentMessageId: string | null = null;

            try {
              await agentService.queryStream(
                message,
                conversationId,
                // onChunk: Update message content as it streams
                (partialText) => {
                  setMessages((prev) => {
                    // First chunk - create the agent message
                    if (!agentMessageId) {
                      agentMessageId = `${Date.now()}-${Math.random()}`;
                      return [...prev, {
                        id: agentMessageId,
                        content: partialText,
                        role: 'agent',
                        label: 'Snowflake Assistant',
                        timestamp: new Date(),
                      }];
                    }
                    // Subsequent chunks - update existing message
                    return prev.map((m) =>
                      m.id === agentMessageId ? { ...m, content: partialText } : m
                    );
                  });
                  setIsLoading(false); // Stop loading dots once streaming starts
                },
                // onComplete: Final update and clear all tool indicators
                (fullText) => {
                  if (agentMessageId) {
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === agentMessageId ? { ...m, content: fullText } : m
                      )
                    );
                  }
                  // Clear any lingering tool indicators
                  setCurrentToolCalls(new Set());
                },
                // onToolCall: Show tool usage
                (toolName) => {
                  setCurrentToolCalls((prev) => new Set([...prev, toolName]));
                },
                // onToolResult: Hide tool when done
                (toolName) => {
                  setCurrentToolCalls((prev) => {
                    const next = new Set(prev);
                    next.delete(toolName);
                    return next;
                  });
                }
              );
            } catch (error) {
              // Update the agent message with error (or create if no chunks received)
              if (agentMessageId) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === agentMessageId ? { ...m, content: `Error: ${error}` } : m
                  )
                );
              } else {
                addMessage(`Error: ${error}`, 'agent', 'Snowflake Assistant');
              }
            } finally {
              setIsLoading(false);
            }
          }}
          onStartVoiceRecording={async () => {
            if (!voiceService) {
              // Initialize voice service
              try {
                const token = await agentService.getVoiceToken();
                const service = new VoiceService(token, {
                  apiUrl,
                  conversationId,
                  conversationHistory: messages, // Pass current conversation for context
                  onTranscript: (text) => {
                    addMessage(text, 'user', 'You (voice)');
                    setVoiceStatus('');
                    setIsLoading(true); // Show loading dots while waiting for response
                    userMessageAddedRef.current = true; // Mark that user message was added
                  },
                  onResponse: (text, isStreaming) => {
                    if (isStreaming) {
                      // Mark agent as speaking when streaming starts
                      setIsAgentSpeaking(true);
                      setIsLoading(false); // Stop loading dots when response starts

                      // Update or create streaming message (using REF for sync access)
                      setMessages((prev) => {
                        const newMessages = [...prev];

                        // Check ref for existing streaming message ID (synchronous!)
                        if (currentStreamingMessageIdRef.current) {
                          const index = newMessages.findIndex(msg => msg.id === currentStreamingMessageIdRef.current);
                          if (index !== -1) {
                            // Found existing message - update it immutably
                            newMessages[index] = {
                              ...newMessages[index],
                              content: text,
                            };
                            return newMessages;
                          }
                        }

                        // Check if user message was added before creating agent message
                        if (!userMessageAddedRef.current) {
                          // User message hasn't been added yet, wait for next update
                          return prev;
                        }

                        // No streaming message yet, create new one
                        const newMessageId = `${Date.now()}-${Math.random()}`;
                        currentStreamingMessageIdRef.current = newMessageId; // Sync update!
                        newMessages.push({
                          id: newMessageId,
                          content: text,
                          role: 'agent',
                          label: 'Snowflake Assistant',
                          timestamp: new Date(),
                        });
                        return newMessages;
                      });
                    } else {
                      // Response complete
                      setIsAgentSpeaking(false);
                      setVoiceStatus('');
                      currentStreamingMessageIdRef.current = null; // Clear ref
                      userMessageAddedRef.current = false; // Reset for next interaction
                    }
                  },
                  onToolCall: () => {
                    // Keep tool calls hidden for consistent UX with text input
                    // (text path shows only loading dots, no tool indicators)
                  },
                  onToolResult: () => {
                    // Keep tool calls hidden for consistent UX with text input
                  },
                  onStatusChange: (status) => {
                    if (status === 'listening') {
                      setVoiceStatus('🎤 Listening...');
                    } else if (status === 'processing') {
                      setVoiceStatus('');
                      setIsLoading(true); // Show loading dots during processing
                    }
                  },
                  onError: (error) => {
                    setVoiceStatus('');
                    addMessage(`Voice error: ${error.message}`, 'agent', 'System');
                  },
                });
                await service.connect();
                setVoiceService(service);
                setVoiceConnected(true);
                await service.startRecording();
              } catch (error) {
                addMessage(`Failed to initialize voice: ${error}`, 'agent', 'System');
              }
            } else {
              await voiceService.startRecording();
            }
          }}
          onStopVoiceRecording={() => {
            if (voiceService) {
              voiceService.stopRecording();
            }
          }}
          onMuteVoice={async () => {
            if (voiceService) {
              await voiceService.muteAudioPlayback();
              setIsAgentSpeaking(false);
            }
          }}
          isAgentSpeaking={isAgentSpeaking}
        />
      )}
    </div>
  );
};
