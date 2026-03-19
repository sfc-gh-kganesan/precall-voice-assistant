import { useState, useRef, useEffect, useCallback } from 'react';

// Use environment variable or default to localhost for development
const getWebSocketUrl = () => {
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL;
  }
  // In production, connect to the same host
  if (window.location.protocol === 'https:') {
    return `wss://${window.location.host}`;
  }
  // In development, use localhost
  return 'ws://localhost:3001';
};

const WEBSOCKET_URL = getWebSocketUrl();
const SAMPLE_RATE = 24000;

interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  isStreaming: boolean;
}

interface FinalTranscript {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: number;
}

interface UseRealtimeConversationReturn {
  isConnected: boolean;
  isConversationActive: boolean;
  isUserSpeaking: boolean;
  isAgentSpeaking: boolean;
  messages: Message[];
  finalTranscripts: FinalTranscript[];
  error: string | null;
  startConversation: () => void;
  stopConversation: () => void;
}

export const useRealtimeConversation = (): UseRealtimeConversationReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConversationActive, setIsConversationActive] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [finalTranscripts, setFinalTranscripts] = useState<FinalTranscript[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const currentAgentMessageIdRef = useRef<string | null>(null);

  // Convert PCM16 base64 to Float32Array for playback
  const base64ToFloat32 = (base64: string): Float32Array => {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    return float32Array;
  };

  // Convert Int16Array to base64
  const int16ToBase64 = (int16Array: Int16Array): string => {
    const uint8Array = new Uint8Array(int16Array.buffer);
    let binaryString = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binaryString += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binaryString);
  };

  // Play audio queue
  const playAudioQueue = useCallback(() => {
    if (!audioContextRef.current || isPlayingRef.current || audioQueueRef.current.length === 0) {
      return;
    }

    isPlayingRef.current = true;
    setIsAgentSpeaking(true);

    const playNext = () => {
      if (audioQueueRef.current.length === 0) {
        isPlayingRef.current = false;
        setIsAgentSpeaking(false);
        return;
      }

      const audioData = audioQueueRef.current.shift()!;
      const audioBuffer = audioContextRef.current!.createBuffer(1, audioData.length, SAMPLE_RATE);
      // Get the channel data directly and copy values
      const channelData = audioBuffer.getChannelData(0);
      channelData.set(audioData);

      const source = audioContextRef.current!.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current!.destination);

      source.onended = () => {
        playNext();
      };

      source.start();
    };

    playNext();
  }, []);

  // Setup WebSocket connection
  const connectWebSocket = useCallback(() => {
    const ws = new WebSocket(WEBSOCKET_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to server');
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case 'audio_delta':
            // Queue audio for playback
            const audioData = base64ToFloat32(message.data);
            audioQueueRef.current.push(audioData);
            playAudioQueue();
            break;

          case 'agent_transcript_delta':
            // Update streaming agent message
            setMessages(prev => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.type === 'agent' && lastMessage.isStreaming) {
                return [
                  ...prev.slice(0, -1),
                  { ...lastMessage, content: lastMessage.content + message.delta }
                ];
              } else {
                const newMessage: Message = {
                  id: currentAgentMessageIdRef.current || `agent-${Date.now()}`,
                  type: 'agent',
                  content: message.delta,
                  isStreaming: true
                };
                currentAgentMessageIdRef.current = newMessage.id;
                return [...prev, newMessage];
              }
            });
            break;

          case 'agent_transcript_done':
            // Finalize agent message
            setMessages(prev => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.type === 'agent' && lastMessage.isStreaming) {
                return [
                  ...prev.slice(0, -1),
                  { ...lastMessage, content: message.transcript, isStreaming: false }
                ];
              }
              return prev;
            });
            currentAgentMessageIdRef.current = null;
            break;

          case 'user_transcript':
            // Add user message
            const userMessage: Message = {
              id: message.item_id,
              type: 'user',
              content: message.transcript,
              isStreaming: false
            };
            setMessages(prev => [...prev, userMessage]);
            break;

          case 'user_speaking_started':
            // User started speaking - enable interruption by clearing audio queue
            console.log('User started speaking - clearing agent audio queue for interruption');
            audioQueueRef.current = [];
            isPlayingRef.current = false;
            setIsAgentSpeaking(false);
            setIsUserSpeaking(true);
            break;

          case 'user_speaking_stopped':
            setIsUserSpeaking(false);
            break;

          case 'final_transcripts':
            setFinalTranscripts(message.transcripts);
            break;

          case 'end_phrase_detected':
            console.log('End phrase detected:', message.transcript);
            break;

          case 'conversation_ended':
            console.log('=== CONVERSATION ENDED EVENT RECEIVED ===');
            console.log('Transcripts received:', message.transcripts);
            console.log('Number of transcripts:', message.transcripts?.length || 0);

            // Set final transcripts FIRST
            if (message.transcripts && message.transcripts.length > 0) {
              console.log('Setting final transcripts:', message.transcripts);
              setFinalTranscripts(message.transcripts);
            } else {
              console.warn('No transcripts in conversation_ended event');
            }

            // Auto-stop the conversation
            console.log('Clearing audio queue and stopping conversation');
            audioQueueRef.current = [];
            isPlayingRef.current = false;

            // Set conversation inactive to trigger UI update
            console.log('Setting isConversationActive to false');
            setIsConversationActive(false);
            setIsUserSpeaking(false);
            setIsAgentSpeaking(false);

            // Stop audio capture
            console.log('Stopping audio capture...');
            if (processorRef.current) {
              processorRef.current.disconnect();
              processorRef.current = null;
              console.log('Processor disconnected');
            }
            if (sourceRef.current) {
              sourceRef.current.disconnect();
              sourceRef.current = null;
              console.log('Source disconnected');
            }
            if (mediaStreamRef.current) {
              mediaStreamRef.current.getTracks().forEach(track => track.stop());
              mediaStreamRef.current = null;
              console.log('Media stream stopped');
            }
            if (audioContextRef.current) {
              audioContextRef.current.close();
              audioContextRef.current = null;
              console.log('Audio context closed');
            }
            console.log('Conversation fully stopped');
            break;

          case 'error':
            console.error('Server error:', message.message);
            setError(message.message);
            break;
        }
      } catch (err) {
        console.error('Error parsing message:', err);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('Connection error');
    };

    ws.onclose = () => {
      console.log('Disconnected from server');
      setIsConnected(false);
    };
  }, [playAudioQueue]);

  // Start audio capture
  const startAudioCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return;
        }

        const inputData = e.inputBuffer.getChannelData(0);
        const int16Array = new Int16Array(inputData.length);

        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        const base64Audio = int16ToBase64(int16Array);

        wsRef.current.send(JSON.stringify({
          type: 'audio_data',
          data: base64Audio
        }));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      console.log('Audio capture started');
    } catch (err) {
      console.error('Error starting audio capture:', err);
      setError('Microphone access denied');
    }
  }, []);

  // Stop audio capture
  const stopAudioCapture = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    console.log('Audio capture stopped');
  }, []);

  // Start conversation
  const startConversation = useCallback(async () => {
    if (isConversationActive || !isConnected) return;

    setMessages([]);
    setFinalTranscripts([]);
    setError(null);
    audioQueueRef.current = [];

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'start_conversation' }));
      await startAudioCapture();
      setIsConversationActive(true);
    }
  }, [isConversationActive, isConnected, startAudioCapture]);

  // Stop conversation
  const stopConversation = useCallback(() => {
    if (!isConversationActive) return;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop_conversation' }));
    }

    stopAudioCapture();
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setIsConversationActive(false);
    setIsUserSpeaking(false);
    setIsAgentSpeaking(false);
  }, [isConversationActive, stopAudioCapture]);

  // Connect on mount
  useEffect(() => {
    connectWebSocket();

    return () => {
      stopAudioCapture();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket, stopAudioCapture]);

  return {
    isConnected,
    isConversationActive,
    isUserSpeaking,
    isAgentSpeaking,
    messages,
    finalTranscripts,
    error,
    startConversation,
    stopConversation
  };
};
