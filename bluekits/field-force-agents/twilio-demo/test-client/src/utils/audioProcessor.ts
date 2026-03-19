/**
 * Audio processing utilities for browser-based voice assistant testing
 */

export class AudioProcessor {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private audioQueue: Float32Array[] = [];
  private isPlaying: boolean = false;

  async initialize(): Promise<void> {
    this.audioContext = new AudioContext({ sampleRate: 24000 });
  }

  async startRecording(onAudioData: (audioData: Int16Array) => void): Promise<void> {
    if (!this.audioContext) {
      throw new Error('AudioContext not initialized');
    }

    // Get microphone access
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 24000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

    // Create script processor (deprecated but widely supported)
    const bufferSize = 4096;
    const processor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

    processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      const pcm16 = this.floatTo16BitPCM(inputData);
      onAudioData(pcm16);
    };

    this.sourceNode.connect(processor);
    processor.connect(this.audioContext.destination);
  }

  stopRecording(): void {
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
  }

  /**
   * Convert PCM16 Int16Array to Float32Array
   */
  private pcm16ToFloat32(int16Array: Int16Array): Float32Array {
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }
    return float32Array;
  }

  /**
   * Queue audio chunk for playback
   */
  queueAudio(pcm16Data: Int16Array): void {
    const floatData = this.pcm16ToFloat32(pcm16Data);
    this.audioQueue.push(floatData);
    this.playAudioQueue();
  }

  /**
   * Play audio queue - plays next chunk immediately when queue has data
   */
  private playAudioQueue(): void {
    if (!this.audioContext || this.isPlaying || this.audioQueue.length === 0) {
      return;
    }

    this.isPlaying = true;

    const playNext = () => {
      if (this.audioQueue.length === 0) {
        this.isPlaying = false;
        return;
      }

      const audioData = this.audioQueue.shift()!;
      const audioBuffer = this.audioContext!.createBuffer(1, audioData.length, 24000);

      // Get channel data and copy values
      const channelData = audioBuffer.getChannelData(0);
      channelData.set(audioData);

      const source = this.audioContext!.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext!.destination);

      source.onended = () => {
        playNext();
      };

      source.start();
    };

    playNext();
  }

  /**
   * Clear the audio queue and stop playback
   */
  clearAudioQueue(): void {
    this.audioQueue = [];
    this.isPlaying = false;
  }

  /**
   * Play audio (queues for smooth playback)
   */
  async playAudio(pcm16Data: Int16Array): Promise<void> {
    this.queueAudio(pcm16Data);
  }

  private floatTo16BitPCM(float32Array: Float32Array): Int16Array {
    const pcm16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return pcm16;
  }

  cleanup(): void {
    this.stopRecording();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

export function int16ArrayToBase64(int16Array: Int16Array): string {
  const uint8Array = new Uint8Array(int16Array.buffer);
  let binary = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binary += String.fromCharCode(uint8Array[i]);
  }
  return btoa(binary);
}

export function base64ToInt16Array(base64: string): Int16Array {
  const binary = atob(base64);
  const uint8Array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    uint8Array[i] = binary.charCodeAt(i);
  }
  return new Int16Array(uint8Array.buffer);
}
