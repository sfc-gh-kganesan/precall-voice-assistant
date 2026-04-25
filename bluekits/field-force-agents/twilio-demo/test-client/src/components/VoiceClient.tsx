import { useState, useRef, useEffect } from 'react';
import { AudioProcessor, int16ArrayToBase64, base64ToInt16Array } from '../utils/audioProcessor';
import './VoiceClient.css';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

export function VoiceClient() {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioProcessorRef = useRef<AudioProcessor | null>(null);
  const shouldPauseRecordingRef = useRef(false);
  const audioTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  const connect = async () => {
    try {
      setStatus('connecting');

      // Initialize audio processor
      const audioProcessor = new AudioProcessor();
      await audioProcessor.initialize();
      audioProcessorRef.current = audioProcessor;

      // Connect to WebSocket — use same host:port in production (container),
      // fall back to port 3000 during local Vite dev
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = import.meta.env.DEV
        ? `${window.location.hostname}:3000`
        : window.location.host;
      const wsUrl = `${protocol}//${host}/test-client`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setStatus('connected');
        addTranscript('🟢 Connected to Jarvis');

        // Start recording after connection
        startRecording();
      };

      ws.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        handleServerMessage(message);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        addTranscript('❌ Connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        setStatus('disconnected');
        setIsRecording(false);
        addTranscript('⚫ Disconnected');
      };
    } catch (error) {
      console.error('Failed to connect:', error);
      setStatus('disconnected');
      addTranscript(`❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const disconnect = () => {
    // Stop recording
    if (audioProcessorRef.current) {
      audioProcessorRef.current.stopRecording();
      audioProcessorRef.current.cleanup();
      audioProcessorRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsRecording(false);
    setStatus('disconnected');
  };

  const startRecording = async () => {
    if (!audioProcessorRef.current || !wsRef.current) return;

    try {
      await audioProcessorRef.current.startRecording((audioData) => {
        // Don't send audio while Jarvis is speaking to prevent echo
        if (shouldPauseRecordingRef.current) {
          return;
        }

        // Send audio to server
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const audioBase64 = int16ArrayToBase64(audioData);
          wsRef.current.send(JSON.stringify({
            type: 'audio',
            data: audioBase64,
          }));
        }
      });

      setIsRecording(true);
      addTranscript('🎤 Recording started - speak now');
    } catch (error) {
      console.error('Failed to start recording:', error);
      addTranscript(`❌ Microphone error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleServerMessage = async (message: any) => {
    console.log('Received message:', message.type);

    switch (message.type) {
      case 'audio':
        // Pause recording while playing to prevent echo
        if (!shouldPauseRecordingRef.current) {
          shouldPauseRecordingRef.current = true;
          setIsSpeaking(true);
        }

        // Clear any existing timeout
        if (audioTimeoutRef.current) {
          clearTimeout(audioTimeoutRef.current);
        }

        // Play audio from server
        if (audioProcessorRef.current && message.data) {
          const pcm16 = base64ToInt16Array(message.data);
          await audioProcessorRef.current.playAudio(pcm16);
        }

        // Auto-resume after 3 seconds of no audio (failsafe)
        audioTimeoutRef.current = setTimeout(() => {
          console.log('Audio timeout - resuming recording');
          shouldPauseRecordingRef.current = false;
          setIsSpeaking(false);
        }, 3000);
        break;

      case 'response.audio.done':
        // Audio response complete - resume recording
        console.log('Audio done - resuming recording');
        if (audioTimeoutRef.current) {
          clearTimeout(audioTimeoutRef.current);
        }
        shouldPauseRecordingRef.current = false;
        setIsSpeaking(false);
        break;

      case 'transcript':
        addTranscript(`🤖 Jarvis: ${message.text}`);
        break;

      case 'user_transcript':
        addTranscript(`👤 You: ${message.text}`);
        break;

      case 'user_speaking':
        if (message.speaking) {
          // User started speaking - clear audio queue for interruption
          console.log('User started speaking - clearing audio queue');
          if (audioProcessorRef.current) {
            audioProcessorRef.current.clearAudioQueue();
          }
          if (audioTimeoutRef.current) {
            clearTimeout(audioTimeoutRef.current);
          }
          shouldPauseRecordingRef.current = false;
          setIsSpeaking(false);
        }
        break;

      case 'session_created':
        addTranscript('✅ Session created');
        break;

      case 'error':
        addTranscript(`❌ Error: ${message.message}`);
        break;

      default:
        console.log('Unhandled message type:', message.type);
    }
  };

  const addTranscript = (text: string) => {
    setTranscript(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${text}`]);
  };

  const clearTranscript = () => {
    setTranscript([]);
  };

  return (
    <div className="voice-client">
      <div className="header">
        <h1>🎙️ Voice Assistant Test Client</h1>
        <div className={`status-badge ${status}`}>
          {status === 'connected' && '🟢 Connected'}
          {status === 'connecting' && '🟡 Connecting...'}
          {status === 'disconnected' && '⚫ Disconnected'}
        </div>
      </div>

      <div className="controls">
        {status === 'disconnected' ? (
          <button
            className="btn btn-primary"
            onClick={connect}
          >
            📞 Start Call with Jarvis
          </button>
        ) : (
          <button
            className="btn btn-danger"
            onClick={disconnect}
          >
            ⏹️ End Call
          </button>
        )}

        {transcript.length > 0 && (
          <button
            className="btn btn-secondary"
            onClick={clearTranscript}
          >
            🗑️ Clear Transcript
          </button>
        )}
      </div>

      {isRecording && (
        <div className="recording-indicator">
          <div className="pulse"></div>
          <span>Recording...</span>
        </div>
      )}

      {isSpeaking && (
        <div className="speaking-indicator">
          <div className="pulse-blue"></div>
          <span>🔊 Jarvis is speaking...</span>
        </div>
      )}

      <div className="transcript">
        <h2>Conversation Transcript</h2>
        <div className="transcript-content">
          {transcript.length === 0 ? (
            <p className="empty-state">
              Click "Start Call with Jarvis" to begin your conversation
            </p>
          ) : (
            transcript.map((line, index) => (
              <div key={index} className="transcript-line">
                {line}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="instructions">
        <h3>💡 How to Use</h3>
        <ol>
          <li>Click "Start Call with Jarvis" to connect</li>
          <li>Allow microphone access when prompted</li>
          <li>Wait for Jarvis to say "Go for Jarvis"</li>
          <li>Ask questions about the pre-call plan:
            <ul>
              <li>"What's the primary objective?"</li>
              <li>"Tell me about the 21 untapped patients"</li>
              <li>"How should I handle XOLAIR objections?"</li>
              <li>"What resources should I bring?"</li>
            </ul>
          </li>
          <li>Click "End Call" when finished</li>
        </ol>
      </div>
    </div>
  );
}
