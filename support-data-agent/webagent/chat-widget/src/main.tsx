/**
 * Enhanced Snowflake Chat Widget with Voice Tool Calling
 *
 * Main entry point - renders React widget
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { ChatWidget } from './components/ChatWidget';
import './styles/widget.css';

// Configuration
const CONFIG = {
  apiUrl: 'http://localhost:8003',
  conversationId: generateConversationId(),
};

function generateConversationId(): string {
  return 'web-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

// Create widget container
function initWidget() {
  const container = document.createElement('div');
  container.id = 'snowflake-chat-widget-root';
  document.body.appendChild(container);

  const root = ReactDOM.createRoot(container);
  root.render(
    <React.StrictMode>
      <ChatWidget apiUrl={CONFIG.apiUrl} conversationId={CONFIG.conversationId} />
    </React.StrictMode>
  );

  console.log('[Widget] Enhanced chat widget initialized with conversation ID:', CONFIG.conversationId);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initWidget);
} else {
  initWidget();
}
