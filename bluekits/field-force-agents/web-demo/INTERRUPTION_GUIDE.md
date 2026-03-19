# Interruption Guide

## How Interruption Works

Your pre-call assistant "Jarvis" now supports **seamless interruption** - you can speak at any time while Jarvis is talking, and the system will stop Jarvis and listen to your new question or topic change.

## Technical Implementation

### Server-Side Voice Activity Detection (VAD)

The system uses OpenAI's Realtime API with server-side VAD, which:
- Continuously monitors your microphone for speech
- Detects when you start speaking
- Automatically interrupts the AI's response
- Processes your new input immediately

### What Happens During an Interruption

1. **You start speaking** → VAD detects your voice
2. **Audio queue is cleared** → Any remaining audio from Jarvis is stopped
3. **Jarvis stops talking** → The AI response is cancelled
4. **Your speech is captured** → The system listens to your complete question
5. **New response generated** → Jarvis responds to your new question

## How to Interrupt

### Simple - Just Start Speaking!

You don't need to press any button or say a wake word. Just start talking while Jarvis is speaking.

**Example:**

```
Jarvis: "Your primary objective is to address the 21 OCS-dependent
         asthma patients not on DUPIXENT. Here's the critical insight:
         Dr. Chavarria has 21 patients suffering on ICS/LABA plus—"

You: [START SPEAKING] "Tell me the recent prescribing patterns"

Jarvis: [STOPS IMMEDIATELY and listens to your question]

Jarvis: "In December 2025, Dr. Chavarria prescribed 4.91 TRX of
         DUPIXENT Asthma..."
```

## Use Cases for Interruption

### 1. **Topic Change**
When Jarvis is providing information you already know, interrupt to move to a different topic:

```
Jarvis: "The physician is a Bio-Hesitant Supporter who—"
You: "Skip that, what does the patient journey report show?"
```

### 2. **Drill Down on Specific Data**
When Jarvis mentions something interesting, interrupt to get more details:

```
Jarvis: "There's a competitive threat from XOLAIR—"
You: "How big is the XOLAIR threat? Give me the numbers"
```

### 3. **Get to What You Need Faster**
When you're short on time, interrupt to get directly to what matters:

```
Jarvis: "Let me walk you through the six-step approach—"
You: "No time. Just tell me the key objections and responses"
```

### 4. **Practice Natural Conversation Flow**
Interruptions make the practice session feel more like a real conversation:

```
Jarvis: "You should mention that these patients are eosinophilic—"
You: "Wait, what if the doctor asks about cost?"
Jarvis: "Great question! Here's how to handle that..."
```

## VAD Configuration

The system is configured with balanced settings for interruption:

```typescript
turn_detection: {
  type: 'server_vad',
  threshold: 0.5,              // Sensitivity (0.0 - 1.0)
  prefix_padding_ms: 300,      // Audio captured before speech detected
  silence_duration_ms: 500,    // Silence duration before considering speech ended
  create_response: true        // Auto-create response after speech ends
}
```

### What These Settings Mean

- **threshold (0.5)**: Balanced sensitivity - not too sensitive (picks up background noise) or too insensitive (misses soft speech)
- **prefix_padding_ms (300ms)**: Captures 300ms of audio before you start speaking, so your first syllable isn't cut off
- **silence_duration_ms (500ms)**: Waits 500ms of silence before deciding you're done speaking
- **create_response (true)**: Automatically generates a response when you stop speaking

## Tips for Best Interruption Experience

### 1. **Speak Clearly**
The VAD works best when you speak clearly and at a normal volume.

### 2. **Don't Hesitate**
When you want to interrupt, just start talking. The system will catch your speech immediately.

### 3. **Complete Your Thought**
After interrupting, complete your question or statement. The system waits 500ms of silence before processing.

### 4. **Background Noise**
Minimize background noise for best results. The VAD is tuned to distinguish speech from ambient sounds, but very loud environments may cause issues.

### 5. **Natural Pauses**
If you pause for more than 500ms while speaking, the system may think you're done. Try to keep your questions flowing naturally.

## Troubleshooting

### "Jarvis doesn't stop when I interrupt"

**Possible causes:**
- Your microphone volume is too low
- There's significant background noise
- Your speech is too soft

**Solutions:**
- Check your microphone settings and ensure it's not muted
- Move to a quieter environment
- Speak at a normal conversational volume

### "Jarvis stops too early (before I finish)"

**Possible causes:**
- You're pausing too long between words (>500ms)
- Background noise is being interpreted as speech ending

**Solutions:**
- Speak more continuously without long pauses
- Reduce background noise
- If this persists, we can adjust the `silence_duration_ms` setting

### "Jarvis responds to background sounds"

**Possible causes:**
- VAD threshold is too sensitive
- Background sounds resemble speech patterns

**Solutions:**
- Use a better microphone with noise cancellation
- Move to a quieter location
- Close to microphone or use headphones

### "Interruption creates a weird echo or overlap"

**Possible causes:**
- Audio playback and microphone are creating a feedback loop

**Solutions:**
- Use headphones instead of speakers
- Ensure your browser's audio settings are configured properly

## Advanced: Adjusting VAD Sensitivity

If you need to adjust the interruption sensitivity, you can modify the `turn_detection` settings in `backend/src/index.ts`:

### More Sensitive (easier to interrupt, more false positives):
```typescript
threshold: 0.3,
silence_duration_ms: 300
```

### Less Sensitive (harder to interrupt, fewer false positives):
```typescript
threshold: 0.7,
silence_duration_ms: 700
```

After changing settings, rebuild and restart:
```bash
npm run build
npm start
```

## Testing Interruption

To test that interruption is working:

1. **Start a conversation** with Jarvis
2. **Ask for a long answer**: "Can you help me prep for my call with Dr. Chavarria?"
3. **Let Jarvis start speaking** for a few seconds
4. **Interrupt mid-sentence**: Start speaking while Jarvis is talking
5. **Verify**: Jarvis should stop immediately and wait for you to finish

You should see in the console:
```
User started speaking (potential interruption)
User started speaking - clearing agent audio queue for interruption
```

## Summary

The interruption feature makes your practice sessions with Jarvis feel natural and conversational. You can:
- ✅ Interrupt at any time
- ✅ Change topics on the fly
- ✅ Drill down into specific data points
- ✅ Control the flow of information
- ✅ Practice realistic conversation dynamics

Just speak naturally, and Jarvis will respond intelligently to your interruptions!
