import WebSocket from 'ws';
import { OpenAIRealtimeClient } from './openAIRealtimeClient';
import { logger } from '../utils/logger';

/**
 * Handles WebSocket connections from browser test clients
 * Unlike Twilio, browsers use PCM16 24kHz directly (no mulaw conversion needed)
 */
export class TestClientHandler {
  private clientWs: WebSocket;
  private openAIClient: OpenAIRealtimeClient;

  constructor(clientWs: WebSocket, openAIClient: OpenAIRealtimeClient) {
    this.clientWs = clientWs;
    this.openAIClient = openAIClient;

    this.setupClientListeners();
    this.setupOpenAIListeners();
  }

  /**
   * Set up browser client WebSocket listeners
   */
  private setupClientListeners(): void {
    this.clientWs.on('message', (data: WebSocket.Data) => {
      try {
        const message = JSON.parse(data.toString());
        this.handleClientMessage(message);
      } catch (error) {
        logger.error('Error parsing client message:', error);
      }
    });

    this.clientWs.on('close', () => {
      logger.info('Test client WebSocket closed');
      this.cleanup();
    });

    this.clientWs.on('error', (error) => {
      logger.error('Test client WebSocket error:', error);
      this.cleanup();
    });
  }

  /**
   * Set up OpenAI client event listeners
   */
  private setupOpenAIListeners(): void {
    // Send audio from OpenAI to browser client
    this.openAIClient.on('audio.delta', (audioBase64: string) => {
      logger.debug(`Received audio delta, length: ${audioBase64.length}`);
      this.sendToClient({
        type: 'audio',
        data: audioBase64,
      });
    });

    // Send transcripts to client for display
    this.openAIClient.on('text.done', (message) => {
      this.sendToClient({
        type: 'transcript',
        text: message.text,
      });
    });

    // Notify client when audio response is complete
    this.openAIClient.on('audio.done', () => {
      logger.debug('Audio response complete');
      this.sendToClient({
        type: 'response.audio.done',
      });
    });

    // Notify client of session creation and trigger initial greeting
    this.openAIClient.on('session.created', () => {
      this.sendToClient({
        type: 'session_created',
      });

      // Trigger Jarvis to say the initial greeting
      logger.info('Session created, triggering initial greeting');
      this.openAIClient.createResponse();
    });

    this.openAIClient.on('error', (error) => {
      logger.error('OpenAI client error:', error);
      this.sendToClient({
        type: 'error',
        message: error.message || 'OpenAI error',
      });
    });

    this.openAIClient.on('close', () => {
      logger.info('OpenAI connection closed');
      this.cleanup();
    });

    // Handle user interruption - manually cancel when user starts speaking
    this.openAIClient.on('speech.started', () => {
      logger.info('User started speaking - manually canceling response');
      this.openAIClient.cancelResponse();
      this.sendToClient({
        type: 'user_speaking',
        speaking: true,
      });
    });

    this.openAIClient.on('speech.stopped', () => {
      logger.info('User stopped speaking');
      this.sendToClient({
        type: 'user_speaking',
        speaking: false,
      });
    });
  }

  /**
   * Handle incoming messages from browser client
   */
  private handleClientMessage(message: any): void {
    switch (message.type) {
      case 'audio':
        // Browser sends PCM16 24kHz audio (already in correct format)
        this.openAIClient.sendAudio(message.data);
        break;

      default:
        logger.debug(`Unhandled client message type: ${message.type}`);
    }
  }

  /**
   * Send message to browser client
   */
  private sendToClient(message: any): void {
    if (this.clientWs.readyState === WebSocket.OPEN) {
      this.clientWs.send(JSON.stringify(message));
    }
  }

  /**
   * Clean up resources
   */
  private cleanup(): void {
    logger.info('Cleaning up test client handler');

    // Disconnect OpenAI if still connected
    if (this.openAIClient.connected) {
      this.openAIClient.disconnect();
    }

    // Close client WebSocket if still open
    if (this.clientWs.readyState === WebSocket.OPEN) {
      this.clientWs.close();
    }
  }
}
