import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { logger } from '../utils/logger';

export interface OpenAIRealtimeConfig {
  apiKey: string;
  model?: string;
  voice?: 'alloy' | 'echo' | 'shimmer';
  systemPrompt: string;
}

export interface SessionConfig {
  modalities: string[];
  instructions: string;
  voice: string;
  speed?: number;
  input_audio_format: string;
  output_audio_format: string;
  input_audio_transcription: {
    model: string;
  };
  turn_detection: {
    type: string;
    threshold: number;
    prefix_padding_ms: number;
    silence_duration_ms: number;
    create_response: boolean;
  };
  temperature?: number;
}

/**
 * OpenAI Realtime API Client
 * Manages WebSocket connection to OpenAI's Realtime API
 */
export class OpenAIRealtimeClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: OpenAIRealtimeConfig;
  private isConnected = false;
  private isResponseActive = false;

  constructor(config: OpenAIRealtimeConfig) {
    super();
    this.config = {
      ...config,
      model: config.model || 'gpt-4o-realtime-preview-2024-12-17',
      voice: config.voice || 'alloy',
    };
  }

  /**
   * Connect to OpenAI Realtime API
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = `wss://api.openai.com/v1/realtime?model=${this.config.model}`;

      this.ws = new WebSocket(url, {
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`,
          'OpenAI-Beta': 'realtime=v1',
        },
      });

      this.ws.on('open', () => {
        logger.info('OpenAI Realtime API connected');
        this.isConnected = true;
        this.sendSessionUpdate();
        resolve();
      });

      this.ws.on('message', (data: WebSocket.Data) => {
        try {
          const dataStr = data.toString();
          const message = JSON.parse(dataStr);
          // Log error events with full raw data using console.log to avoid logger filtering
          if (message.type === 'error') {
            console.log('=== OPENAI ERROR RAW DATA ===');
            console.log(dataStr);
            console.log('=== END ERROR DATA ===');
          }
          this.handleMessage(message);
        } catch (error) {
          console.log('=== PARSE ERROR ===');
          console.log('Error:', error);
          console.log('Raw data:', data.toString().substring(0, 1000));
          console.log('=== END PARSE ERROR ===');
        }
      });

      this.ws.on('error', (error) => {
        logger.error('OpenAI WebSocket error:', error);
        this.emit('error', error);
        reject(error);
      });

      this.ws.on('close', () => {
        logger.info('OpenAI WebSocket closed');
        this.isConnected = false;
        this.emit('close');
      });
    });
  }

  /**
   * Send session update with configuration.
   * Browser client uses pcm16 natively — no conversion needed.
   */
  private sendSessionUpdate(): void {
    const sessionConfig: SessionConfig = {
      modalities: ['text', 'audio'],
      instructions: this.config.systemPrompt,
      voice: this.config.voice || 'alloy',
      speed: 1.2,
      input_audio_format: 'pcm16',
      output_audio_format: 'pcm16',
      input_audio_transcription: {
        model: 'whisper-1',
      },
      turn_detection: {
        type: 'server_vad',
        threshold: 0.7,
        prefix_padding_ms: 300,
        silence_duration_ms: 1000,
        create_response: true,
      },
      temperature: 0.8,
    };

    this.send({
      type: 'session.update',
      session: sessionConfig,
    });
  }

  /**
   * Handle incoming messages from OpenAI (GA API format)
   */
  private handleMessage(message: any): void {
    const { type } = message;

    switch (type) {
      case 'session.created':
        logger.info('OpenAI session created');
        this.emit('session.created', message);
        break;

      case 'session.updated':
        logger.info('OpenAI session updated');
        this.emit('session.updated', message);
        break;

      case 'input_audio_buffer.speech_started':
        logger.debug('User started speaking');
        this.emit('speech.started', message);
        break;

      case 'input_audio_buffer.speech_stopped':
        logger.debug('User stopped speaking');
        this.emit('speech.stopped', message);
        break;

      // GA API uses response.output_audio.delta, legacy uses response.audio.delta
      case 'response.audio.delta':
      case 'response.output_audio.delta':
        // Audio chunk from OpenAI
        this.emit('audio.delta', message.delta);
        break;

      case 'response.audio.done':
      case 'response.output_audio.done':
        logger.debug('Audio response complete');
        this.emit('audio.done', message);
        break;

      case 'response.done':
        logger.debug('Response complete');
        this.isResponseActive = false;
        this.emit('response.done', message);
        break;

      case 'response.text.delta':
        this.emit('text.delta', message.delta);
        break;

      case 'response.text.done':
        logger.debug('Text response complete:', message.text);
        this.emit('text.done', message);
        break;

      // GA API uses response.output_audio_transcript.delta/done
      case 'response.audio_transcript.delta':
      case 'response.output_audio_transcript.delta':
        this.emit('response.audio_transcript.delta', message);
        break;

      case 'response.audio_transcript.done':
      case 'response.output_audio_transcript.done':
        logger.debug('Audio transcript complete:', message.transcript);
        this.emit('response.audio_transcript.done', message);
        break;

      case 'conversation.item.created':
        logger.debug('Conversation item created');
        this.emit('conversation.item.created', message);
        break;

      case 'conversation.item.input_audio_transcription.completed':
        logger.debug('User transcript:', message.transcript);
        this.emit('conversation.item.input_audio_transcription.completed', message);
        break;

      case 'response.output_item.done':
        logger.debug('Response output item done');
        break;

      case 'response.created':
        logger.debug('Response created');
        this.isResponseActive = true;
        break;

      case 'input_audio_buffer.committed':
        logger.debug('Audio buffer committed');
        break;

      case 'response.cancelled':
        logger.info('Response cancelled (interrupted)');
        this.isResponseActive = false;
        this.emit('response.cancelled', message);
        break;

      case 'output_audio_buffer.cleared':
        logger.info('Output audio buffer cleared');
        break;

      case 'error':
        // Log all keys in the message to understand the structure
        logger.error('OpenAI error - keys:', Object.keys(message));
        logger.error('OpenAI error - raw:', message);
        try {
          logger.error('OpenAI error - stringified:', JSON.stringify(message));
        } catch (e) {
          logger.error('OpenAI error - could not stringify');
        }
        this.emit('error', message.error || message);
        break;

      default:
        logger.debug(`Unhandled OpenAI event type: ${type}`);
    }
  }

  /**
   * Send audio data to OpenAI
   * @param audioBase64 - Base64 encoded PCM16 24kHz audio
   */
  sendAudio(audioBase64: string): void {
    if (!this.isConnected) {
      logger.warn('Cannot send audio: not connected to OpenAI');
      return;
    }

    this.send({
      type: 'input_audio_buffer.append',
      audio: audioBase64,
    });
  }

  /**
   * Send a message to OpenAI
   */
  private send(message: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      logger.warn('Cannot send message: WebSocket not open');
      return;
    }

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Commit the audio buffer (forces response)
   */
  commitAudioBuffer(): void {
    this.send({
      type: 'input_audio_buffer.commit',
    });
  }

  /**
   * Create a response (manually trigger)
   */
  createResponse(): void {
    logger.info('Triggering response.create for initial greeting');

    // Send a user message to trigger the greeting
    this.send({
      type: 'conversation.item.create',
      item: {
        type: 'message',
        role: 'user',
        content: [
          {
            type: 'input_text',
            text: 'Start the conversation by saying "Hello! Go for Jarvis." and then wait for the user to respond. Do not continue speaking after that.'
          }
        ]
      }
    });

    // Then trigger the response
    this.send({
      type: 'response.create'
    });
  }

  /**
   * Cancel the current response (for interruptions).
   * Only sends if a response is actually in progress.
   */
  cancelResponse(): void {
    if (!this.isResponseActive) {
      logger.debug('Skipping response.cancel - no active response');
      return;
    }
    logger.info('Canceling current response (user interruption)');
    this.isResponseActive = false;
    this.send({
      type: 'response.cancel',
    });
  }

  /**
   * Interrupt the current response (cancel response only).
   * Only sends if a response is actually in progress.
   */
  interruptResponse(): void {
    if (!this.isResponseActive) {
      logger.debug('Skipping interrupt - no active response');
      return;
    }
    logger.info('Interrupting response: canceling in-progress response');
    this.isResponseActive = false;
    this.send({
      type: 'response.cancel',
    });
  }

  /**
   * Disconnect from OpenAI
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  /**
   * Check if connected
   */
  get connected(): boolean {
    return this.isConnected;
  }
}
