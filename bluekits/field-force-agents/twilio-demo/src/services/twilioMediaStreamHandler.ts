import WebSocket from 'ws';
import { OpenAIRealtimeClient } from './openAIRealtimeClient';
import { logger } from '../utils/logger';

/**
 * Handles a single Twilio Media Stream connection
 */
export class TwilioMediaStreamHandler {
  private twilioWs: WebSocket;
  private openAIClient: OpenAIRealtimeClient;
  private streamSid: string | null = null;
  private callSid: string | null = null;
  private audioChunkCount: number = 0;

  constructor(twilioWs: WebSocket, openAIClient: OpenAIRealtimeClient) {
    logger.info('🚀 TwilioMediaStreamHandler constructor called - latest version with streamSid extraction');
    this.twilioWs = twilioWs;
    this.openAIClient = openAIClient;

    this.setupTwilioListeners();
    this.setupOpenAIListeners();
    logger.info('✅ TwilioMediaStreamHandler initialized, listeners set up');
  }

  /**
   * Set up Twilio WebSocket event listeners
   */
  private setupTwilioListeners(): void {
    this.twilioWs.on('message', (data: WebSocket.Data) => {
      try {
        const message = JSON.parse(data.toString());
        // Only log non-media events (media events are too noisy)
        if (message.event !== 'media') {
          const eventType = message.event;
          const sid = message.start?.streamSid || message.streamSid;
          logger.info(`Twilio event: ${eventType}, streamSid: ${sid || 'none'}`);
        }
        this.handleTwilioMessage(message);
      } catch (error) {
        logger.error('Error parsing Twilio message:', error);
      }
    });

    this.twilioWs.on('close', () => {
      logger.info('Twilio WebSocket closed');
      this.cleanup();
    });

    this.twilioWs.on('error', (error) => {
      logger.error('Twilio WebSocket error:', error);
      this.cleanup();
    });
  }

  /**
   * Set up OpenAI client event listeners
   */
  private setupOpenAIListeners(): void {
    // Handle audio from OpenAI and send to Twilio
    this.openAIClient.on('audio.delta', (audioBase64: string) => {
      this.audioChunkCount++;
      // Only log first chunk and every 10th chunk to reduce noise
      if (this.audioChunkCount === 1 || this.audioChunkCount % 10 === 0) {
        logger.info(`🔊 Received audio delta #${this.audioChunkCount} (${audioBase64.length} bytes), streamSid: ${this.streamSid || 'MISSING'}`);
      }
      this.sendAudioToTwilio(audioBase64);
    });

    // Log when session is created
    this.openAIClient.on('session.created', () => {
      logger.info('✅ OpenAI session created');
    });

    // Trigger initial greeting when session is updated
    this.openAIClient.on('session.updated', () => {
      logger.info('⚙️ OpenAI session updated - will send initial greeting once');
      // Small delay to ensure Twilio stream is ready
      setTimeout(() => {
        if (this.streamSid) {
          logger.info(`✅ Stream SID available (${this.streamSid}), triggering greeting`);
          this.openAIClient.createResponse();
        } else {
          logger.warn('⚠️ Stream SID not yet available when session.updated received, will retry');
          setTimeout(() => {
            if (this.streamSid) {
              logger.info(`✅ Stream SID now available (${this.streamSid}), triggering greeting`);
              this.openAIClient.createResponse();
            } else {
              logger.error('❌ Stream SID still not available - greeting may not play');
            }
          }, 500);
        }
      }, 300);
    });

    // Log when audio response completes
    this.openAIClient.on('audio.done', () => {
      logger.info(`🎵 Audio response complete - received ${this.audioChunkCount} total chunks`);
      this.audioChunkCount = 0; // Reset for next response
    });

    // Log when entire response completes
    this.openAIClient.on('response.done', (response) => {
      logger.info('✅ Response complete', {
        usage: response?.response?.usage
      });
    });

    this.openAIClient.on('error', (error) => {
      logger.error('❌ OpenAI client error:', error);
    });

    this.openAIClient.on('close', () => {
      logger.info('🔌 OpenAI connection closed');
      this.cleanup();
    });

    // Handle user interruption - manually cancel when user starts speaking
    this.openAIClient.on('speech.started', () => {
      logger.info('🎤 User started speaking - interrupting AI');

      // 1. Clear Twilio's audio buffer to stop any queued audio immediately
      this.clearTwilioAudioBuffer();

      // 2. Cancel OpenAI's response
      this.openAIClient.cancelResponse();
    });

    this.openAIClient.on('speech.stopped', () => {
      logger.info('🔇 User stopped speaking');
    });

    // Log transcripts to see what OpenAI is actually saying
    this.openAIClient.on('response.audio_transcript.done', (event: any) => {
      logger.info(`📝 AI Transcript: "${event.transcript}"`);
    });
  }

  /**
   * Handle incoming messages from Twilio
   */
  private handleTwilioMessage(message: any): void {
    const { event } = message;

    // Extract streamSid from media packets if we don't have it yet
    if (!this.streamSid && message.streamSid) {
      this.streamSid = message.streamSid;
      logger.info(`📡 Extracted streamSid from ${event} event: ${this.streamSid}`);
    }

    switch (event) {
      case 'connected':
        logger.info('✅ Twilio Media Stream CONNECTED');
        break;

      case 'start':
        logger.info('🎬 Twilio START event received');
        this.handleStart(message);
        break;

      case 'media':
        // Don't log every media packet (too noisy)
        this.handleMedia(message);
        break;

      case 'stop':
        logger.info('🛑 Twilio STOP event received');
        this.handleStop(message);
        break;

      default:
        logger.info(`❓ Unhandled Twilio event: ${event}`);
    }
  }

  /**
   * Handle stream start event
   */
  private handleStart(message: any): void {
    this.streamSid = message.start.streamSid;
    this.callSid = message.start.callSid;

    logger.info(`📡 Media stream started - streamSid: ${this.streamSid}, callSid: ${this.callSid}`);
  }

  /**
   * Handle incoming audio media from Twilio
   */
  private handleMedia(message: any): void {
    const { media } = message;

    if (!media || !media.payload) {
      return;
    }

    try {
      // OpenAI now accepts g711_ulaw directly - no conversion needed!
      this.openAIClient.sendAudio(media.payload);
    } catch (error) {
      logger.error('Error processing media:', error);
    }
  }

  /**
   * Handle stream stop event
   */
  private handleStop(_message: any): void {
    logger.info('Media stream stopped', {
      streamSid: this.streamSid,
    });
    this.cleanup();
  }

  /**
   * Clear Twilio's audio buffer (used for interruptions)
   */
  private clearTwilioAudioBuffer(): void {
    if (!this.streamSid) {
      logger.warn('Cannot clear buffer: no stream SID');
      return;
    }

    logger.info('🗑️ Clearing Twilio audio buffer');

    const clearMessage = {
      event: 'clear',
      streamSid: this.streamSid,
    };

    if (this.twilioWs.readyState === WebSocket.OPEN) {
      this.twilioWs.send(JSON.stringify(clearMessage));
    }
  }

  /**
   * Send audio from OpenAI to Twilio
   */
  private sendAudioToTwilio(audioBase64: string): void {
    if (!this.streamSid) {
      logger.warn('Cannot send audio: no stream SID');
      return;
    }

    try {
      // OpenAI sends g711_ulaw directly - send to Twilio as-is!
      if (this.audioChunkCount === 1) {
        logger.info(`🔊 Sending audio directly (no conversion): ${audioBase64.length} bytes`);
      }

      const message = {
        event: 'media',
        streamSid: this.streamSid,
        media: {
          payload: audioBase64,
        },
      };

      if (this.twilioWs.readyState === WebSocket.OPEN) {
        this.twilioWs.send(JSON.stringify(message));
      } else {
        logger.warn(`⚠️ Cannot send audio: Twilio WebSocket not open (state=${this.twilioWs.readyState})`);
      }
    } catch (error) {
      logger.error('Error sending audio to Twilio:', error);
    }
  }

  /**
   * Clean up resources
   */
  private cleanup(): void {
    logger.info('Cleaning up media stream handler');

    // Disconnect OpenAI if still connected
    if (this.openAIClient.connected) {
      this.openAIClient.disconnect();
    }

    // Close Twilio WebSocket if still open
    if (this.twilioWs.readyState === WebSocket.OPEN) {
      this.twilioWs.close();
    }
  }
}
