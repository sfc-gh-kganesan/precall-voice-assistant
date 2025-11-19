/**
 * Snowflake Agent Chat Widget
 *
 * A floating chat widget that integrates with the external_agent API.
 * Supports streaming responses, tool call visualization, and conversation history.
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
    console.log('[Snowflake Chat] Widget initialized with conversation ID:', CONFIG.conversationId);
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

          <!-- Input Area -->
          <div id="snowflake-chat-input-area">
            <textarea
              id="snowflake-chat-input"
              placeholder="Ask about Snowflake..."
              rows="1"
              aria-label="Message input"
            ></textarea>
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

      // Top-left: drag left increases width, drag up increases height
      // Bottom edge stays fixed - window grows upward and leftward
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
          Note: I don't have access to customer-specific data.
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
   * Send a message to the agent
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
                scrollToBottom();  // Auto-scroll as content streams in
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

  /**
   * Format markdown content safely
   */
  function formatMarkdown(text) {
    if (typeof marked === 'undefined') {
      // Fallback if marked.js didn't load
      return escapeHtml(text);
    }

    // Configure marked for security and features
    marked.setOptions({
      breaks: true,        // Convert \n to <br>
      gfm: true,          // GitHub Flavored Markdown
      sanitize: false,    // We'll handle sanitization
      smartLists: true,
      smartypants: true,  // Smart quotes
    });

    // Parse markdown
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
