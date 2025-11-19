/**
 * Snowflake Agent Chat Widget v2
 *
 * Enhanced with OpenAI Realtime API voice support (hold-to-talk).
 * Supports streaming text responses, tool call visualization, and voice chat.
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    apiUrl: 'http://localhost:8003',
    conversationId: generateConversationId(),
    maxRetries: 3,
    retryDelay: 1000,
  };

  // State management
  const state = {
    isOpen: false,
    isLoading: false,
    messages: [],
    currentToolCalls: new Set(),
    // Voice state
    voiceAvailable: false,
    voiceEnabled: false,
    voiceSession: null,
    voiceStatus: 'idle', // idle, connecting, connected, listening, processing
    isRecording: false,
  };

  /**
   * Generate a unique conversation ID
   */
  function generateConversationId() {
    return 'web-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
  }

  /**
   * Initialize the chat widget
   */
  function init() {
    injectHTML();
    attachEventListeners();
    showWelcomeMessage();
    checkVoiceAvailability();
    console.log('[Snowflake Chat] Widget initialized with conversation ID:', CONFIG.conversationId);
  }

  /**
   * Check if voice is available from backend
   */
  async function checkVoiceAvailability() {
    try {
      const response = await fetch(`${CONFIG.apiUrl}/api/v1/voice/available`);
      if (response.ok) {
        const data = await response.json();
        state.voiceAvailable = data.available;
        console.log('[Voice] Voice available:', state.voiceAvailable);

        // Show/hide mic button based on availability
        const micButton = document.getElementById('snowflake-chat-mic');
        if (micButton) {
          micButton.style.display = state.voiceAvailable ? 'flex' : 'none';
        }
      }
    } catch (error) {
      console.warn('[Voice] Could not check voice availability:', error);
      state.voiceAvailable = false;
    }
  }

  /**
   * Inject the chat widget HTML into the page
   */
  function injectHTML() {
    const widgetHTML = `
      <div id="snowflake-chat-widget">
        <!-- Chat Bubble Button -->
        <button id="snowflake-chat-bubble" aria-label="Open Snowflake Chat">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
            <path d="M7 9h10v2H7zm0-3h10v2H7zm0 6h7v2H7z"/>
          </svg>
        </button>

        <!-- Chat Window -->
        <div id="snowflake-chat-window">
          <!-- Header -->
          <div id="snowflake-chat-header">
            <h3>
              <span class="status-indicator"></span>
              Snowflake Assistant
            </h3>
            <button id="snowflake-chat-close" aria-label="Close chat">&times;</button>
          </div>

          <!-- Messages Container -->
          <div id="snowflake-chat-messages"></div>

          <!-- Voice Status (hidden by default) -->
          <div id="snowflake-voice-status" class="voice-status hidden">
            <span class="voice-status-text"></span>
          </div>

          <!-- Input Area -->
          <div id="snowflake-chat-input-area">
            <textarea
              id="snowflake-chat-input"
              placeholder="Ask about Snowflake..."
              rows="1"
              aria-label="Message input"
            ></textarea>
            <button id="snowflake-chat-mic" aria-label="Hold to speak" title="Hold to speak" style="display: none;">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
            </button>
            <button id="snowflake-chat-send" aria-label="Send message">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>

          <!-- Resize Handle (Top-Left) -->
          <div id="snowflake-chat-resize-handle-tl" class="chat-resize-handle" title="Drag to resize">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
              <path d="M2 2L6 6M2 6L6 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', widgetHTML);
  }

  /**
   * Attach event listeners to chat elements
   */
  function attachEventListeners() {
    // Toggle chat window
    document.getElementById('snowflake-chat-bubble').addEventListener('click', toggleChat);
    document.getElementById('snowflake-chat-close').addEventListener('click', toggleChat);

    // Send message
    document.getElementById('snowflake-chat-send').addEventListener('click', sendMessage);

    // Handle Enter key in textarea
    const input = document.getElementById('snowflake-chat-input');
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea
    input.addEventListener('input', autoResizeTextarea);

    // Mic button - hold to talk
    const micButton = document.getElementById('snowflake-chat-mic');
    micButton.addEventListener('mousedown', startVoiceRecording);
    micButton.addEventListener('mouseup', stopVoiceRecording);
    micButton.addEventListener('touchstart', (e) => {
      e.preventDefault();
      startVoiceRecording();
    });
    micButton.addEventListener('touchend', (e) => {
      e.preventDefault();
      stopVoiceRecording();
    });

    // Resize handle
    initializeResizeHandle();
  }

  /**
   * Initialize resize handle for manual window resizing from top-left corner
   */
  function initializeResizeHandle() {
    const chatWindow = document.getElementById('snowflake-chat-window');
    const resizeHandle = document.getElementById('snowflake-chat-resize-handle-tl');

    let isResizing = false;
    let startX, startY, startWidth, startHeight;

    resizeHandle.addEventListener('mousedown', (e) => {
      isResizing = true;
      startX = e.clientX;
      startY = e.clientY;
      startWidth = chatWindow.offsetWidth;
      startHeight = chatWindow.offsetHeight;

      chatWindow.classList.add('resizing');
      document.body.style.cursor = 'nesw-resize';
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!isResizing) return;

      const deltaX = startX - e.clientX;
      const deltaY = startY - e.clientY;

      let newWidth = startWidth + deltaX;
      let newHeight = startHeight + deltaY;

      // Apply constraints
      newWidth = Math.max(300, Math.min(800, newWidth));
      newHeight = Math.max(400, Math.min(900, newHeight));

      chatWindow.style.width = newWidth + 'px';
      chatWindow.style.height = newHeight + 'px';
    });

    document.addEventListener('mouseup', () => {
      if (isResizing) {
        isResizing = false;
        chatWindow.classList.remove('resizing');
        document.body.style.cursor = '';
      }
    });
  }

  /**
   * Toggle chat window open/closed
   */
  function toggleChat() {
    state.isOpen = !state.isOpen;
    const chatWindow = document.getElementById('snowflake-chat-window');

    if (state.isOpen) {
      chatWindow.classList.add('open');
      document.getElementById('snowflake-chat-input').focus();
    } else {
      chatWindow.classList.remove('open');
    }
  }

  /**
   * Auto-resize textarea based on content
   */
  function autoResizeTextarea() {
    const textarea = document.getElementById('snowflake-chat-input');
    const minHeight = 44; // 2 lines
    const maxHeight = 120; // ~6 lines

    // Reset height to calculate scrollHeight accurately
    textarea.style.height = 'auto';

    // Calculate new height
    const newHeight = Math.max(minHeight, Math.min(textarea.scrollHeight, maxHeight));
    textarea.style.height = newHeight + 'px';

    // Show scrollbar only when max height is reached
    if (textarea.scrollHeight > maxHeight) {
      textarea.style.overflowY = 'auto';
    } else {
      textarea.style.overflowY = 'hidden';
    }
  }

  /**
   * Show welcome message
   */
  function showWelcomeMessage() {
    const messagesContainer = document.getElementById('snowflake-chat-messages');
    messagesContainer.innerHTML = `
      <div class="welcome-message">
        <h4>👋 Welcome to Snowflake Support</h4>
        <p>I'm here to help you with:</p>
        <p>• Snowflake documentation and features<br>
        • Best practices and troubleshooting<br>
        • General technical questions</p>
        <p style="font-size: 12px; color: #999; margin-top: 16px;">
          💬 Type or 🎤 hold mic to speak
        </p>
      </div>
    `;
  }

  /**
   * Add a message to the chat
   */
  function addMessage(content, sender = 'agent', options = {}) {
    const messagesContainer = document.getElementById('snowflake-chat-messages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;

    let messageHTML = '';

    if (options.label) {
      messageHTML += `<div class="message-label">${options.label}</div>`;
    }

    if (options.isTyping) {
      messageHTML += `
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      `;
    } else {
      // Use markdown for agent messages, plain text for user messages
      if (sender === 'agent') {
        messageHTML += `<div class="message-content markdown-content">${formatMarkdown(content)}</div>`;
      } else {
        messageHTML += `<div class="message-content">${escapeHtml(content)}</div>`;
      }
    }

    messageDiv.innerHTML = messageHTML;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
  }

  /**
   * Add tool call indicator
   */
  function addToolCallIndicator(toolName) {
    const messagesContainer = document.getElementById('snowflake-chat-messages');

    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'chat-message agent';
    indicatorDiv.dataset.toolName = toolName;
    indicatorDiv.innerHTML = `
      <div class="tool-call-indicator">
        <div class="spinner"></div>
        <span>Using tool: ${escapeHtml(toolName)}</span>
      </div>
    `;

    messagesContainer.appendChild(indicatorDiv);
    scrollToBottom();

    state.currentToolCalls.add(toolName);
    return indicatorDiv;
  }

  /**
   * Remove tool call indicator
   */
  function removeToolCallIndicator(toolName) {
    const indicator = document.querySelector(`[data-tool-name="${toolName}"]`);
    if (indicator) {
      indicator.remove();
    }
    state.currentToolCalls.delete(toolName);
  }

  /**
   * Update voice status display
   */
  function updateVoiceStatus(statusText) {
    const statusEl = document.getElementById('snowflake-voice-status');
    const statusTextEl = statusEl.querySelector('.voice-status-text');

    if (statusText) {
      statusTextEl.textContent = statusText;
      statusEl.classList.remove('hidden');
    } else {
      statusEl.classList.add('hidden');
    }
  }

  /**
   * Send a text message to the agent
   */
  async function sendMessage() {
    const input = document.getElementById('snowflake-chat-input');
    const sendButton = document.getElementById('snowflake-chat-send');
    const message = input.value.trim();

    if (!message || state.isLoading) return;

    // Add user message to chat
    addMessage(message, 'user', { label: 'You' });

    // Clear input
    input.value = '';
    autoResizeTextarea();

    // Show typing indicator
    const typingIndicator = addMessage('', 'agent', { isTyping: true });

    // Disable input
    state.isLoading = true;
    input.disabled = true;
    sendButton.disabled = true;

    try {
      await queryAgent(message, typingIndicator);
    } catch (error) {
      console.error('[Snowflake Chat] Error:', error);
      typingIndicator.remove();
      addMessage(
        `Sorry, I encountered an error: ${error.message}. Please try again.`,
        'agent',
        { label: 'Snowflake Assistant' }
      );
    } finally {
      state.isLoading = false;
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
    }
  }

  /**
   * Query the agent API with streaming
   */
  async function queryAgent(message, typingIndicator) {
    let fullResponse = '';
    let agentMessageDiv = null;

    const response = await fetch(`${CONFIG.apiUrl}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        conversation_id: CONFIG.conversationId,
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n\n');

      for (const line of lines) {
        if (!line.trim() || !line.startsWith('event: ')) continue;

        try {
          const [eventLine, dataLine] = line.split('\n');
          const eventType = eventLine.replace('event: ', '').trim();
          const data = JSON.parse(dataLine.replace('data: ', '').trim());

          if (eventType === 'tool_call') {
            // Show tool being called
            addToolCallIndicator(data.tool);

          } else if (eventType === 'tool_result') {
            // Remove tool indicator when done
            removeToolCallIndicator(data.tool);

          } else if (eventType === 'text_delta') {
            // Stream text content
            if (typingIndicator && typingIndicator.parentNode) {
              typingIndicator.remove();
              typingIndicator = null;
            }

            fullResponse += data.content;

            if (!agentMessageDiv) {
              agentMessageDiv = addMessage(fullResponse, 'agent', {
                label: 'Snowflake Assistant'
              });
            } else {
              const contentDiv = agentMessageDiv.querySelector('.message-content');
              if (contentDiv) {
                // Render markdown in real-time
                contentDiv.innerHTML = formatMarkdown(fullResponse);
                scrollToBottom();
              }
            }

          } else if (eventType === 'final') {
            // Final response received
            if (typingIndicator && typingIndicator.parentNode) {
              typingIndicator.remove();
            }

            if (!agentMessageDiv && data.content) {
              addMessage(data.content, 'agent', {
                label: 'Snowflake Assistant'
              });
            }

          } else if (eventType === 'error') {
            throw new Error(data.error);
          }

        } catch (parseError) {
          console.warn('[Snowflake Chat] Failed to parse event:', parseError);
        }
      }
    }

    // Clean up any remaining indicators
    state.currentToolCalls.forEach(toolName => {
      removeToolCallIndicator(toolName);
    });
  }

  // ============================================================================
  // VOICE FUNCTIONALITY
  // ============================================================================

  /**
   * Start voice recording (hold-to-talk)
   */
  async function startVoiceRecording() {
    if (state.isRecording || !state.voiceAvailable) return;

    console.log('[Voice] Starting recording...');
    state.isRecording = true;

    // Visual feedback
    const micButton = document.getElementById('snowflake-chat-mic');
    micButton.classList.add('recording');
    updateVoiceStatus('🎤 Listening...');

    try {
      // Initialize voice session if needed
      if (!state.voiceSession) {
        await initializeVoiceSession();
      }

      // Start recording
      if (state.voiceSession && state.voiceSession.isConnected) {
        state.voiceSession.startRecording();
      }
    } catch (error) {
      console.error('[Voice] Error starting recording:', error);
      updateVoiceStatus('');
      state.isRecording = false;
      micButton.classList.remove('recording');
      addMessage(`Voice error: ${error.message}`, 'agent', { label: 'System' });
    }
  }

  /**
   * Stop voice recording
   */
  function stopVoiceRecording() {
    if (!state.isRecording) return;

    console.log('[Voice] Stopping recording...');
    state.isRecording = false;

    // Visual feedback
    const micButton = document.getElementById('snowflake-chat-mic');
    micButton.classList.remove('recording');
    updateVoiceStatus('Processing...');

    // Stop recording
    if (state.voiceSession && state.voiceSession.isConnected) {
      state.voiceSession.stopRecording();
    }
  }

  /**
   * Initialize OpenAI Realtime voice session
   */
  async function initializeVoiceSession() {
    console.log('[Voice] Initializing session...');
    updateVoiceStatus('Connecting...');

    try {
      // Get ephemeral token from backend
      const tokenResponse = await fetch(`${CONFIG.apiUrl}/api/v1/voice/token`, {
        method: 'POST',
      });

      if (!tokenResponse.ok) {
        throw new Error('Failed to get voice token');
      }

      const { token } = await tokenResponse.json();

      // Create voice session using OpenAI Realtime API
      let voiceResponseMessage = null;  // Track the streaming message element

      state.voiceSession = new VoiceSession(token, {
        onTranscript: (text) => {
          // User speech transcribed
          console.log('[Voice] User said:', text);
          addMessage(text, 'user', { label: 'You (voice)' });
          updateVoiceStatus('');
        },
        onResponse: (text, isStreaming = false) => {
          // Agent responded (streaming or complete)
          console.log('[Voice] Agent said:', text.substring(0, 100) + (text.length > 100 ? '...' : ''));

          if (isStreaming) {
            // Streaming: update existing message or create new one
            if (!voiceResponseMessage) {
              voiceResponseMessage = addMessage(text, 'agent', { label: 'Snowflake Assistant' });
            } else {
              // Update the existing message content
              const contentDiv = voiceResponseMessage.querySelector('.message-content');
              if (contentDiv) {
                contentDiv.innerHTML = formatMarkdown(text);
                scrollToBottom();
              }
            }
          } else {
            // Complete: reset for next response
            voiceResponseMessage = null;
            updateVoiceStatus('');
          }
        },
        onError: (error) => {
          console.error('[Voice] Session error:', error);
          updateVoiceStatus('');
          addMessage(`Voice error: ${error.message}`, 'agent', { label: 'System' });
        },
        onStatusChange: (status) => {
          state.voiceStatus = status;
          if (status === 'connected') {
            updateVoiceStatus('');
          }
        }
      });

      await state.voiceSession.connect();
      console.log('[Voice] Session connected');
      updateVoiceStatus('');

    } catch (error) {
      console.error('[Voice] Failed to initialize session:', error);
      updateVoiceStatus('');
      throw error;
    }
  }

  /**
   * Voice Session class - manages OpenAI Realtime API connection
   */
  class VoiceSession {
    constructor(token, callbacks) {
      this.token = token;
      this.callbacks = callbacks;
      this.ws = null;
      this.isConnected = false;
      this.audioContext = null;
      this.mediaStream = null;
      this.audioWorklet = null;
      this.currentTranscript = '';  // Accumulate streaming transcript
    }

    async connect() {
      // Connect to OpenAI Realtime API via WebSocket (GA version - no beta header)
      this.ws = new WebSocket('wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17', [
        'realtime',
        `openai-insecure-api-key.${this.token}`
      ]);

      return new Promise((resolve, reject) => {
        this.ws.onopen = async () => {
          console.log('[Voice] WebSocket connected');

          // Configure session for push-to-talk (no VAD) - GA API format
          // Reference: https://platform.openai.com/docs/guides/realtime-conversations
          this.ws.send(JSON.stringify({
            type: 'session.update',
            session: {
              type: 'realtime',
              model: 'gpt-realtime',
              instructions: `You are a helpful Snowflake support assistant. When users ask questions about Snowflake:

1. IMMEDIATELY say a brief acknowledgment like "Let me check that for you" or "Looking that up now"
2. Then use the query_support_agent tool to get accurate information
3. After receiving the tool result, provide a clear, conversational answer

Keep responses concise and natural for voice interaction. Always use the tool for Snowflake questions.`,
              tools: [
                {
                  type: 'function',
                  name: 'query_support_agent',
                  description: 'Search Snowflake documentation and internal knowledge base. Use this for ANY question about Snowflake features, syntax, troubleshooting, or best practices.',
                  parameters: {
                    type: 'object',
                    properties: {
                      query: {
                        type: 'string',
                        description: 'The user\'s question or search query'
                      }
                    },
                    required: ['query']
                  }
                }
              ],
              audio: {
                input: {
                  format: {
                    type: 'audio/pcm',
                    rate: 24000
                  },
                  transcription: {
                    model: 'whisper-1'
                  },
                  turn_detection: null  // Disable VAD for push-to-talk
                },
                output: {
                  voice: 'alloy',
                  format: {
                    type: 'audio/pcm',
                    rate: 24000
                  }
                }
              }
            }
          }));

          this.isConnected = true;
          this.callbacks.onStatusChange?.('connected');
          resolve();
        };

        this.ws.onerror = (error) => {
          console.error('[Voice] WebSocket error:', error);
          reject(error);
        };

        this.ws.onmessage = (event) => {
          this.handleServerEvent(JSON.parse(event.data));
        };

        this.ws.onclose = () => {
          console.log('[Voice] WebSocket closed');
          this.isConnected = false;
          this.callbacks.onStatusChange?.('idle');
        };
      });
    }

    async startRecording() {
      // Clear any previous audio
      this.ws.send(JSON.stringify({
        type: 'input_audio_buffer.clear'
      }));

      // Start capturing microphone
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioContext = new AudioContext({ sampleRate: 24000 });
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Use ScriptProcessorNode for simplicity (deprecated but works)
      const processor = this.audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (e) => {
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          const pcm16 = new Int16Array(inputData.length);

          // Convert float32 to int16
          for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]));
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }

          // Send audio to OpenAI
          const base64Audio = btoa(String.fromCharCode.apply(null, new Uint8Array(pcm16.buffer)));
          this.ws.send(JSON.stringify({
            type: 'input_audio_buffer.append',
            audio: base64Audio
          }));
        }
      };

      source.connect(processor);
      processor.connect(this.audioContext.destination);
      this.audioWorklet = processor;
    }

    stopRecording() {
      // Stop microphone
      if (this.audioWorklet) {
        this.audioWorklet.disconnect();
        this.audioWorklet = null;
      }
      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
      }
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }

      // Commit audio and request response
      if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'input_audio_buffer.commit'
        }));
        this.ws.send(JSON.stringify({
          type: 'response.create'
        }));
      }
    }

    handleServerEvent(event) {
      console.log('[Voice] Server event:', event.type);

      // User speech transcription
      if (event.type === 'conversation.item.input_audio_transcription.completed') {
        this.callbacks.onTranscript?.(event.transcript);
      }

      // Agent response transcript (streaming)
      if (event.type === 'response.output_audio_transcript.delta') {
        // Accumulate transcript as it streams
        this.currentTranscript += event.delta || '';
        // Call callback with streaming flag to update UI in real-time
        if (this.currentTranscript) {
          this.callbacks.onResponse?.(this.currentTranscript, true);
        }
      }

      // Agent response transcript (complete)
      if (event.type === 'response.output_audio_transcript.done') {
        // Use accumulated transcript or fallback to event transcript
        const finalTranscript = this.currentTranscript || event.transcript || '';
        if (finalTranscript) {
          // Call with isStreaming=false to mark as complete
          this.callbacks.onResponse?.(finalTranscript, false);
        }
        // Reset for next response
        this.currentTranscript = '';
      }

      // Tool/Function call from agent
      if (event.type === 'response.function_call_arguments.done') {
        this.handleToolCall(event);
      }

      // Play audio response
      if (event.type === 'response.audio.delta' && event.delta) {
        // TODO: Play audio (would need AudioContext playback)
        // For now, we just show transcripts
      }

      // Errors
      if (event.type === 'error') {
        const errorMessage = event.error?.message || 'Unknown error';

        // Ignore "buffer too small" errors - these happen when releasing mic quickly
        // and are not critical (just means user didn't speak long enough)
        if (errorMessage.includes('buffer too small')) {
          console.log('[Voice] Buffer too small (released mic quickly) - ignoring');
          return;
        }

        this.callbacks.onError?.(new Error(errorMessage));
      }
    }

    async handleToolCall(event) {
      const callId = event.call_id;
      const functionName = event.name;
      const args = JSON.parse(event.arguments);

      console.log('[Voice] Tool call:', { functionName, args });

      // Show tool call indicator
      addToolCallIndicator(functionName);

      try {
        let result;

        if (functionName === 'query_support_agent') {
          // Call the backend agent
          console.log('[Voice] Calling backend agent...');
          const response = await fetch(`${CONFIG.apiUrl}/query`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              message: args.query,
              conversation_id: CONFIG.conversationId,
              stream: false,
            }),
          });

          if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
          }

          const data = await response.json();
          result = data.content;
          console.log('[Voice] Got backend response:', result.substring(0, 100));
        } else {
          result = JSON.stringify({ error: `Unknown tool: ${functionName}` });
        }

        // Remove tool call indicator
        removeToolCallIndicator(functionName);

        // Send tool result back to OpenAI
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({
            type: 'conversation.item.create',
            item: {
              type: 'function_call_output',
              call_id: callId,
              output: result,
            },
          }));

          // Request agent to continue with the tool result
          this.ws.send(JSON.stringify({
            type: 'response.create',
          }));

          console.log('[Voice] Tool result sent back to OpenAI');
        }
      } catch (error) {
        console.error('[Voice] Tool call failed:', error);

        // Remove tool call indicator on error too
        removeToolCallIndicator(functionName);

        // Send error back to OpenAI
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({
            type: 'conversation.item.create',
            item: {
              type: 'function_call_output',
              call_id: callId,
              output: JSON.stringify({ error: String(error) }),
            },
          }));
        }
      }
    }

    disconnect() {
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
      this.isConnected = false;
    }
  }

  /**
   * Format markdown content safely
   */
  function formatMarkdown(text) {
    if (typeof marked === 'undefined') {
      return escapeHtml(text);
    }

    marked.setOptions({
      breaks: true,
      gfm: true,
      sanitize: false,
      smartLists: true,
      smartypants: true,
    });

    return marked.parse(text);
  }

  /**
   * Scroll messages container to bottom
   */
  function scrollToBottom() {
    const messagesContainer = document.getElementById('snowflake-chat-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
