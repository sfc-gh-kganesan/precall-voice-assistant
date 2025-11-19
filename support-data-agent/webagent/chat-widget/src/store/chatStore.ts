/**
 * Simple state store for chat widget
 */

import type { Message } from '../types';

interface ChatState {
  isOpen: boolean;
  isLoading: boolean;
  messages: Message[];
  currentToolCalls: Set<string>;
  voiceStatus: string;
}

class ChatStore {
  private state: ChatState = {
    isOpen: false,
    isLoading: false,
    messages: [],
    currentToolCalls: new Set(),
    voiceStatus: '',
  };

  private listeners: Set<() => void> = new Set();

  getState(): ChatState {
    return this.state;
  }

  setState(updates: Partial<ChatState>): void {
    this.state = { ...this.state, ...updates };
    this.notify();
  }

  addMessage(message: Message): void {
    this.state.messages.push(message);
    this.notify();
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    this.listeners.forEach((listener) => listener());
  }
}

export const chatStore = new ChatStore();
