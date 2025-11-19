/**
 * Enhanced Snowflake Chat Widget with Voice Tool Calling
 *
 * This script enhances the existing chat-widget-v2.js by replacing
 * the VoiceSession class with one that supports OpenAI Realtime tool calling.
 */

import { VoiceService } from './services/VoiceService';
import { AgentService } from './services/AgentService';

// Configuration
const CONFIG = {
  apiUrl: 'http://localhost:8003',
  conversationId: generateConversationId(),
};

function generateConversationId(): string {
  return 'web-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

// Export enhanced VoiceSession to global scope
// so the existing chat-widget-v2.js can use it
(window as any).EnhancedVoiceSession = VoiceService;
(window as any).AgentService = AgentService;
(window as any).WIDGET_CONFIG = CONFIG;

console.log('[Widget] Enhanced voice service loaded with tool calling support');
