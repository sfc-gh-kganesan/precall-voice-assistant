/**
 * Voice Service - OpenAI Realtime API with Tool Calling
 *
 * Implements speech-to-speech with backend agent tool integration
 */

import type { VoiceSessionConfig, VoiceStatus, RealtimeSession, RealtimeEvent } from '../types';
import { AgentService } from './AgentService';
import { WavStreamPlayer } from 'wavtools';
import { tracer } from '../instrumentation';
import { SpanStatusCode } from '@opentelemetry/api';

export class VoiceService {
  private ws: WebSocket | null = null;
  private token: string;
  private config: VoiceSessionConfig;
  private agentService: AgentService;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioWorklet: ScriptProcessorNode | null = null;
  private wavStreamPlayer: WavStreamPlayer | null = null;
  private isConnected = false;
  private status: VoiceStatus = 'idle';
  private currentTranscript = '';  // Accumulate streaming transcript
  private isResponseInProgress = false;  // Track if agent is currently responding

  constructor(token: string, config: VoiceSessionConfig) {
    this.token = token;
    this.config = config;
    this.agentService = new AgentService(config.apiUrl);
  }

  /**
   * Connect to OpenAI Realtime API with tool calling configured
   */
  async connect(): Promise<void> {
    return tracer.startActiveSpan('voice.session', async (sessionSpan): Promise<void> => {
      sessionSpan.setAttribute('voice.model', 'gpt-4o-realtime-preview');
      sessionSpan.setAttribute('conversation_id', this.config.conversationId || 'unknown');

      try {
        console.log('[VoiceService] Connecting to OpenAI Realtime API...');
        this.updateStatus('connecting');

        // Connect via WebSocket
        this.ws = new WebSocket(
          'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
          ['realtime', `openai-insecure-api-key.${this.token}`]
        );

        return new Promise((resolve, reject) => {
          if (!this.ws) {
            sessionSpan.setStatus({ code: SpanStatusCode.ERROR, message: 'WebSocket not initialized' });
            sessionSpan.end();
            reject(new Error('WebSocket not initialized'));
            return;
          }

          this.ws.onopen = () => {
            console.log('[VoiceService] WebSocket connected');
            this.configureSession();
            this.isConnected = true;
            this.updateStatus('connected');

            // Initialize audio player
            this.initializeAudioPlayer();

            sessionSpan.setStatus({ code: SpanStatusCode.OK });
            resolve(undefined);
          };

          this.ws.onmessage = (event) => {
            try {
              const data: RealtimeEvent = JSON.parse(event.data);
              this.handleServerEvent(data);
            } catch (error) {
              console.error('[VoiceService] Failed to parse message:', error);
            }
          };

          this.ws.onerror = (error) => {
            console.error('[VoiceService] WebSocket error:', error);
            this.updateStatus('error');
            sessionSpan.recordException(new Error('WebSocket error'));
            sessionSpan.setStatus({ code: SpanStatusCode.ERROR, message: 'WebSocket error' });
            sessionSpan.end();
            reject(error);
          };

          this.ws.onclose = () => {
            console.log('[VoiceService] WebSocket closed');
            this.isConnected = false;
            this.updateStatus('idle');
            sessionSpan.end();
          };
        });
      } catch (error) {
        sessionSpan.recordException(error as Error);
        sessionSpan.setStatus({ code: SpanStatusCode.ERROR, message: (error as Error).message });
        sessionSpan.end();
        throw error;
      }
    });
  }

  /**
   * Initialize WavStreamPlayer for audio playback
   */
  private async initializeAudioPlayer(): Promise<void> {
    try {
      this.wavStreamPlayer = new WavStreamPlayer({ sampleRate: 24000 });
      await this.wavStreamPlayer.connect();
      console.log('[VoiceService] Audio player initialized');
    } catch (error) {
      console.error('[VoiceService] Failed to initialize audio player:', error);
    }
  }

  /**
   * Configure the Realtime session with tools
   */
  private configureSession(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const session: RealtimeSession = {
      type: 'realtime',
      model: 'gpt-realtime',
      instructions: ` You are a helpful Snowflake support assistant. You MUST respond in the EXACT SAME LANGUAGE that the user's question was received. If you are not sure, default to ENGLISH.

When users ask questions about Snowflake:

1. IMMEDIATELY say a brief acknowledgment in their language
2. Then use the query_support_agent tool with a COMPLETE, CONCISE question (not just keywords - pass a full sentence like "How do I check warehouse size?")
3. After receiving the tool result, provide a clear, conversational answer in the same language

NOTE: You must avoid answering detailed question's about a user's specific personal information or account or system.
If user wants you to help with questions about their specific account or their specific queries that are not just general troubleshooting or feature questions
first, try to nudge them towards general best practices and steps to follow.
If they insist on account-specific help, offer to create a support case.

IMPORTANT: Before creating a case, validate the details with the user first. Draft the subject and description using information from the conversation, read them back to the user, and only proceed after they confirm the details are correct.

The tool you have available has a robust knowledge base about Snowflake and can also help with case creation/escalation if absolutely needed

Keep responses extremely brief for voice - users don't want to listen to long responses. Always use the tool for Snowflake questions.

CRITICAL REMINDER: ALWAYS respond in the EXACT SAME LANGUAGE as the user's question. Look at the transcript text to identify the language, then use ONLY that language for your response. If unsure, default to ENGLISH.`,
      tools: [
        {
          type: 'function',
          name: 'query_support_agent',
          description:
            'Search Snowflake documentation and internal knowledge base. Use this for ANY question about Snowflake features, syntax, troubleshooting, or best practices. IMPORTANT: Pass a complete, concise question as a full sentence (e.g., "How do I optimize query performance?" or "What are the best practices for warehouse sizing?"), not just keywords.',
          parameters: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'The user\'s question or search query',
              },
            },
            required: ['query'],
          },
        },
      ],
      audio: {
        input: {
          format: { type: 'audio/pcm', rate: 24000 },
          transcription: { model: 'whisper-1' },
          turn_detection: null, // Push-to-talk
        },
        output: {
          voice: 'alloy',
          format: { type: 'audio/pcm', rate: 24000 },
        },
      },
    };

    this.ws.send(
      JSON.stringify({
        type: 'session.update',
        session,
      })
    );

    console.log('[VoiceService] Session configured with tools');
  }

  /**
   * Handle events from OpenAI Realtime API
   */
  private async handleServerEvent(event: RealtimeEvent): Promise<void> {
    console.log('[VoiceService] Event:', event.type);

    switch (event.type) {
      // User speech transcribed
      case 'conversation.item.input_audio_transcription.completed':
        this.config.onTranscript?.(event.transcript);
        break;

      // Agent wants to call a function/tool
      case 'response.function_call_arguments.done':
        await this.handleToolCall(event);
        break;

      // Response started
      case 'response.created':
        this.isResponseInProgress = true;
        break;

      // Response completed or cancelled
      case 'response.done':
      case 'response.cancelled':
        this.isResponseInProgress = false;
        break;

      // Agent response transcript (streaming)
      case 'response.output_audio_transcript.delta':
        // Accumulate transcript as it streams
        this.currentTranscript += event.delta || '';
        // Call callback with streaming flag to update UI in real-time
        if (this.currentTranscript) {
          this.config.onResponse?.(this.currentTranscript, true);
        }
        break;

      // Agent response transcript (complete)
      case 'response.output_audio_transcript.done':
        // Use accumulated transcript or fallback to event transcript
        const finalTranscript = this.currentTranscript || event.transcript || '';
        if (finalTranscript) {
          // Call with isStreaming=false to mark as complete
          this.config.onResponse?.(finalTranscript, false);
        }
        // Reset for next response
        this.currentTranscript = '';
        break;

      // Audio chunks (for playback)
      case 'response.output_audio.delta':
        if (event.delta && this.wavStreamPlayer) {
          try {
            // Decode base64 audio to Int16Array
            const binaryString = atob(event.delta);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            const pcm16 = new Int16Array(bytes.buffer);

            // Play audio chunk
            this.wavStreamPlayer.add16BitPCM(pcm16, event.item_id || 'audio');
          } catch (error) {
            console.error('[VoiceService] Failed to play audio chunk:', error);
          }
        }
        break;

      // Audio playback complete
      case 'response.output_audio.done':
        console.log('[VoiceService] Audio playback complete');
        break;

      // Errors
      case 'error':
        const errorMessage = event.error?.message || 'Unknown error';
        // Suppress expected errors (buffer too small, cancellation failures)
        if (!errorMessage.includes('buffer too small') &&
            !errorMessage.includes('no active response') &&
            !errorMessage.includes('Cancellation failed')) {
          console.error('[VoiceService] Error:', errorMessage);
          this.config.onError?.(new Error(errorMessage));
        }
        break;
    }
  }

  /**
   * Handle tool/function calls from the agent
   */
  private async handleToolCall(event: RealtimeEvent): Promise<void> {
    return tracer.startActiveSpan('voice.tool_call_to_backend', async (span) => {
      const callId = event.call_id;
      const functionName = event.name;
      const args = JSON.parse(event.arguments);

      span.setAttribute('tool.name', functionName);
      span.setAttribute('tool.call_id', callId);
      span.setAttribute('tool.args', JSON.stringify(args));

      console.log('[VoiceService] Tool call:', { functionName, args });
      this.config.onToolCall?.(functionName);

      try {
        let result: string;

        if (functionName === 'query_support_agent') {
          // Call the backend agent (this will propagate trace context)
          result = await this.agentService.query(args.query, this.config.conversationId);
          span.setAttribute('tool.status', 'success');
          span.setAttribute('backend.response_length', result.length);
        } else {
          result = JSON.stringify({ error: `Unknown tool: ${functionName}` });
          span.setAttribute('tool.status', 'unknown_tool');
        }

        // Send tool result back to OpenAI
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(
            JSON.stringify({
              type: 'conversation.item.create',
              item: {
                type: 'function_call_output',
                call_id: callId,
                output: result,
              },
            })
          );

          // Request agent to continue with the tool result
          this.ws.send(
            JSON.stringify({
              type: 'response.create',
            })
          );

          console.log('[VoiceService] Tool result sent back to OpenAI');
          this.config.onToolResult?.(functionName);
        }

        span.setStatus({ code: SpanStatusCode.OK });
        span.end();
      } catch (error) {
        console.error('[VoiceService] Tool call failed:', error);
        span.recordException(error as Error);
        span.setAttribute('tool.status', 'error');
        span.setStatus({ code: SpanStatusCode.ERROR, message: (error as Error).message });
        span.end();

        // Send error back to OpenAI
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(
            JSON.stringify({
              type: 'conversation.item.create',
              item: {
                type: 'function_call_output',
                call_id: callId,
                output: JSON.stringify({ error: String(error) }),
              },
            })
          );
        }
      }
    });
  }

  /**
   * Start recording audio from microphone
   */
  async startRecording(): Promise<void> {
    console.log('[VoiceService] Starting recording...');
    this.updateStatus('listening');

    // Interrupt any playing audio
    if (this.wavStreamPlayer) {
      try {
        await this.wavStreamPlayer.interrupt();
        console.log('[VoiceService] Interrupted audio playback');
      } catch (error) {
        console.warn('[VoiceService] Failed to interrupt audio:', error);
      }
    }

    // Cancel response only if one is actually in progress
    if (this.isResponseInProgress && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'response.cancel' }));
      console.log('[VoiceService] Cancelled in-progress response');
    }

    // Clear previous audio buffer
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'input_audio_buffer.clear' }));
    }

    // Inject recent conversation history for context
    if (this.config.conversationHistory && this.config.conversationHistory.length > 0 && this.ws) {
      const recentMessages = this.config.conversationHistory.slice(-10); // Last 10 messages
      for (const msg of recentMessages) {
        this.ws.send(JSON.stringify({
          type: 'conversation.item.create',
          item: {
            type: 'message',
            role: msg.role === 'user' ? 'user' : 'assistant',
            content: [{
              // Use correct content type: input_text for user, output_text for assistant
              type: msg.role === 'user' ? 'input_text' : 'output_text',
              text: msg.content
            }]
          }
        }));
      }
      console.log(`[VoiceService] Injected ${recentMessages.length} messages for context`);
    }

    // Get microphone access
    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioContext = new AudioContext({ sampleRate: 24000 });
    const source = this.audioContext.createMediaStreamSource(this.mediaStream);

    // Process audio and send to OpenAI
    this.audioWorklet = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.audioWorklet.onaudioprocess = (e) => {
      if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(inputData.length);

        // Convert float32 to int16
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Send to OpenAI as base64
        const base64Audio = btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(pcm16.buffer))));
        this.ws.send(
          JSON.stringify({
            type: 'input_audio_buffer.append',
            audio: base64Audio,
          })
        );
      }
    };

    source.connect(this.audioWorklet);
    this.audioWorklet.connect(this.audioContext.destination);
  }

  /**
   * Stop recording and commit audio
   */
  stopRecording(): void {
    console.log('[VoiceService] Stopping recording...');
    this.updateStatus('processing');

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
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // Commit audio and request response
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'input_audio_buffer.commit' }));
      this.ws.send(JSON.stringify({ type: 'response.create' }));
    }
  }

  /**
   * Disconnect and cleanup
   */
  disconnect(): void {
    console.log('[VoiceService] Disconnecting...');

    if (this.audioWorklet || this.mediaStream || this.audioContext) {
      this.stopRecording();
    }

    if (this.wavStreamPlayer) {
      this.wavStreamPlayer.interrupt();
      this.wavStreamPlayer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
    this.updateStatus('idle');
  }

  /**
   * Update voice status
   */
  private updateStatus(status: VoiceStatus): void {
    this.status = status;
    this.config.onStatusChange?.(status);
  }

  /**
   * Get current status
   */
  getStatus(): VoiceStatus {
    return this.status;
  }

  /**
   * Mute audio playback without canceling the response
   * Allows text streaming to continue while stopping voice output
   */
  async muteAudioPlayback(): Promise<void> {
    console.log('[VoiceService] Muting audio playback...');

    if (this.wavStreamPlayer) {
      try {
        await this.wavStreamPlayer.interrupt();
        console.log('[VoiceService] Audio playback muted');
      } catch (error) {
        console.warn('[VoiceService] Failed to mute audio:', error);
      }
    }

    // Note: We do NOT disconnect WebSocket or cancel response
    // Text streaming continues via transcript delta events
  }
}
