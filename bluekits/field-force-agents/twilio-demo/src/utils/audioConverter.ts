/**
 * Audio conversion utilities for Twilio (mulaw 8kHz) <-> OpenAI (PCM16 24kHz)
 */

// Mulaw encoding/decoding tables
const MULAW_BIAS = 33;

// Mulaw segment lookup table
const MULAW_SEG_SHIFT = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07];

/**
 * Decode mulaw to linear PCM16
 * Twilio sends mulaw encoded audio
 */
export function mulawToLinear(mulawByte: number): number {
  mulawByte = ~mulawByte;
  const sign = mulawByte & 0x80;
  const exponent = (mulawByte >> 4) & 0x07;
  const mantissa = mulawByte & 0x0F;

  let sample = mantissa << (exponent + 3);
  sample += MULAW_BIAS << exponent;

  if (sign !== 0) {
    sample = -sample;
  }

  return sample;
}

/**
 * Encode linear PCM16 to mulaw
 * For sending audio back to Twilio
 */
export function linearToMulaw(sample: number): number {
  const CLIP = 32635;
  const sign = (sample >> 8) & 0x80;

  if (sign !== 0) {
    sample = -sample;
  }

  if (sample > CLIP) {
    sample = CLIP;
  }

  sample = sample + MULAW_BIAS;

  let exponent = 7;
  for (let i = 0; i < 8; i++) {
    if (sample <= (0x1FFF >> MULAW_SEG_SHIFT[i])) {
      exponent = i;
      break;
    }
  }

  const mantissa = (sample >> (exponent + 3)) & 0x0F;
  const mulawByte = ~(sign | (exponent << 4) | mantissa);

  return mulawByte & 0xFF;
}

/**
 * Decode mulaw buffer to PCM16 buffer
 */
export function decodeMulaw(mulawBuffer: Buffer): Buffer {
  const pcmBuffer = Buffer.alloc(mulawBuffer.length * 2);

  for (let i = 0; i < mulawBuffer.length; i++) {
    const linear = mulawToLinear(mulawBuffer[i]);
    pcmBuffer.writeInt16LE(linear, i * 2);
  }

  return pcmBuffer;
}

/**
 * Encode PCM16 buffer to mulaw buffer
 */
export function encodeMulaw(pcmBuffer: Buffer): Buffer {
  const mulawBuffer = Buffer.alloc(pcmBuffer.length / 2);

  for (let i = 0; i < pcmBuffer.length; i += 2) {
    const sample = pcmBuffer.readInt16LE(i);
    mulawBuffer[i / 2] = linearToMulaw(sample);
  }

  return mulawBuffer;
}

/**
 * Simple linear resampling (8kHz -> 24kHz)
 * Each input sample becomes 3 output samples
 */
export function upsample8To24(pcm8khz: Buffer): Buffer {
  const outputLength = pcm8khz.length * 3;
  const output = Buffer.alloc(outputLength);

  for (let i = 0; i < pcm8khz.length; i += 2) {
    const sample = pcm8khz.readInt16LE(i);
    const outIndex = (i / 2) * 3 * 2;

    // Simple linear interpolation: repeat sample 3 times
    output.writeInt16LE(sample, outIndex);
    output.writeInt16LE(sample, outIndex + 2);
    output.writeInt16LE(sample, outIndex + 4);
  }

  return output;
}

/**
 * Simple downsampling (24kHz -> 8kHz)
 * Take every 3rd sample
 */
export function downsample24To8(pcm24khz: Buffer): Buffer {
  const outputLength = Math.floor(pcm24khz.length / 3);
  const output = Buffer.alloc(outputLength);

  for (let i = 0; i < outputLength; i += 2) {
    // Take every 3rd sample
    const sourceIndex = (i / 2) * 3 * 2;
    const sample = pcm24khz.readInt16LE(sourceIndex);
    output.writeInt16LE(sample, i);
  }

  return output;
}

/**
 * Convert Twilio mulaw 8kHz to OpenAI PCM16 24kHz
 */
export function twilioToOpenAI(mulawBuffer: Buffer): Buffer {
  // Step 1: Decode mulaw to PCM16
  const pcm8khz = decodeMulaw(mulawBuffer);

  // Step 2: Upsample from 8kHz to 24kHz
  const pcm24khz = upsample8To24(pcm8khz);

  return pcm24khz;
}

/**
 * Convert OpenAI PCM16 24kHz to Twilio mulaw 8kHz
 */
export function openAIToTwilio(pcm24khz: Buffer): Buffer {
  // Step 1: Downsample from 24kHz to 8kHz
  const pcm8khz = downsample24To8(pcm24khz);

  // Step 2: Encode to mulaw
  const mulawBuffer = encodeMulaw(pcm8khz);

  return mulawBuffer;
}

/**
 * Convert Buffer to base64 string
 */
export function bufferToBase64(buffer: Buffer): string {
  return buffer.toString('base64');
}

/**
 * Convert base64 string to Buffer
 */
export function base64ToBuffer(base64: string): Buffer {
  return Buffer.from(base64, 'base64');
}
