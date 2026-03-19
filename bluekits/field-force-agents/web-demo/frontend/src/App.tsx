import { useEffect, useRef } from 'react';
import { useRealtimeConversation } from './hooks/useRealtimeConversation';

function App() {
  const {
    isConnected,
    isConversationActive,
    isUserSpeaking,
    isAgentSpeaking,
    messages,
    finalTranscripts,
    error,
    startConversation,
    stopConversation
  } = useRealtimeConversation();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getStatusText = () => {
    if (!isConnected) return 'Connecting...';
    if (!isConversationActive) return 'Ready';
    if (isAgentSpeaking) return 'Speaking';
    if (isUserSpeaking) return 'Listening';
    return 'Active';
  };

  const getStatusColor = () => {
    if (!isConnected) return '#ef4444';
    if (!isConversationActive) return '#6366f1';
    if (isAgentSpeaking) return '#10b981';
    if (isUserSpeaking) return '#f59e0b';
    return '#6366f1';
  };

  const handleButtonClick = () => {
    if (isConversationActive) {
      stopConversation();
    } else {
      startConversation();
    }
  };

  return (
    <div className="app">
      <div className="background-gradient"></div>

      <div className="container">
        <header className="header">
          <h1 className="title">Real-time Voice Conversation</h1>
          <div className="status-indicator" style={{ backgroundColor: getStatusColor() }}>
            {getStatusText()}
          </div>
        </header>

        <div className="main-content">
          {/* Control Button */}
          <div className="button-container">
            <button
              className={`conversation-button ${isConversationActive ? 'active' : ''}`}
              onClick={handleButtonClick}
              disabled={!isConnected && !isConversationActive}
            >
              <div className="button-inner">
                {isConversationActive ? (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className="button-icon"
                  >
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                  </svg>
                ) : (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className="button-icon"
                  >
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2h2v2a5 5 0 0 0 10 0v-2h2Z" />
                    <path d="M11 19.93V22h2v-2.07a7.001 7.001 0 0 1-2 0Z" />
                  </svg>
                )}
              </div>
              <span className="button-text">
                {isConversationActive ? 'Stop' : 'Start'}
              </span>
            </button>
          </div>

          {/* Error Display */}
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {/* Debug Info - Remove in production */}
          {!isConnected && !error && (
            <div style={{ color: '#a5b4fc', fontSize: '0.875rem', textAlign: 'center' }}>
              Connecting to server...
            </div>
          )}

          {/* Live Transcript */}
          {isConversationActive && messages.length > 0 && (
            <div className="transcript-panel">
              <h2 className="panel-title">Conversation</h2>
              <div className="messages-container">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`message ${message.type}`}
                  >
                    <div className="message-label">
                      {message.type === 'user' ? 'You' : 'AI Assistant'}
                    </div>
                    <div className="message-content">
                      {message.content}
                      {message.isStreaming && (
                        <span className="typing-indicator">
                          <span></span>
                          <span></span>
                          <span></span>
                        </span>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>
          )}

          {/* Final Transcripts */}
          {!isConversationActive && finalTranscripts.length > 0 && (
            <div className="final-transcripts-panel">
              <h2 className="panel-title">Conversation Transcript</h2>
              <div className="final-transcripts-container">
                {finalTranscripts.map((transcript) => (
                  <div key={transcript.id} className={`final-transcript ${transcript.type}`}>
                    <div className="transcript-header">
                      <div className="transcript-label">
                        {transcript.type === 'user' ? 'You' : 'Jarvis'}
                      </div>
                      <div className="transcript-time">
                        {new Date(transcript.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                    <div className="transcript-text">{transcript.content}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Instructions */}
          {!isConversationActive && finalTranscripts.length === 0 && (
            <div className="instructions">
              <p>Click the button to start a conversation with the AI assistant.</p>
              <p>Say "I am done" when you want to end the conversation.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
