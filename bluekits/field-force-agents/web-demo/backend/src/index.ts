import express from 'express';
import { WebSocketServer, WebSocket } from 'ws';
import dotenv from 'dotenv';
import { IncomingMessage } from 'http';
import path from 'path';
import cors from 'cors';
import fs from 'fs';

dotenv.config();

const app = express();
app.use(cors());
const PORT = process.env.PORT || 3001;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENAI_MODEL = process.env.OPENAI_MODEL || 'gpt-realtime';

if (!OPENAI_API_KEY) {
  console.error('ERROR: OPENAI_API_KEY is not set in environment variables');
  process.exit(1);
}

// Load pre-call context
let preCallContext: any = null;
try {
  const contextPath = path.join(__dirname, '../pre-call-context.json');
  const contextData = fs.readFileSync(contextPath, 'utf-8');
  preCallContext = JSON.parse(contextData);
  console.log('Pre-call context loaded successfully');
} catch (error) {
  console.warn('No pre-call context file found or error loading it:', error);
}

// Serve static files from frontend build
app.use(express.static(path.join(__dirname, '../../frontend/dist')));

// Health check endpoint
app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// Catch-all route to serve index.html for client-side routing
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, '../../frontend/dist/index.html'));
});

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// WebSocket server for client connections
const wss = new WebSocketServer({ server });

interface ClientMessage {
  type: 'start_conversation' | 'audio_data' | 'stop_conversation';
  data?: string;
}

interface OpenAIEvent {
  type: string;
  [key: string]: any;
}

interface UserTranscript {
  id: string;
  content: string;
  timestamp: number;
}

wss.on('connection', (clientWs: WebSocket) => {
  console.log('Client connected');

  let openaiWs: WebSocket | null = null;
  let userTranscripts: UserTranscript[] = [];
  let agentTranscripts: UserTranscript[] = []; // Store agent responses
  let allTranscripts: Array<{type: 'user' | 'agent', content: string, timestamp: number, id: string}> = [];
  let isConnected = false;
  let awaitingConfirmation = false;

  const END_PHRASES = ['i am done', "i'm done", 'goodbye', 'bye', 'thats all', "that's all"];
  const YES_PHRASES = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'alright', 'definitely'];

  // Check if transcript contains end phrase
  const containsEndPhrase = (text: string): boolean => {
    const lowerText = text.toLowerCase().trim();
    return END_PHRASES.some(phrase => lowerText.includes(phrase));
  };

  // Check if transcript contains yes/confirmation
  const containsYesPhrase = (text: string): boolean => {
    const lowerText = text.toLowerCase().trim();
    // More flexible matching - check if the phrase is contained in the text
    return YES_PHRASES.some(phrase => {
      // Exact match
      if (lowerText === phrase) return true;
      // Starts with phrase followed by space
      if (lowerText.startsWith(phrase + ' ')) return true;
      // Ends with space followed by phrase
      if (lowerText.endsWith(' ' + phrase)) return true;
      // Contains phrase surrounded by spaces
      if (lowerText.includes(' ' + phrase + ' ')) return true;
      // For single words, also check if the entire text contains the phrase
      if (phrase.length <= 4 && lowerText.includes(phrase)) return true;
      return false;
    });
  };

  // Connect to OpenAI Realtime API
  const connectToOpenAI = () => {
    const url = `wss://api.openai.com/v1/realtime?model=${OPENAI_MODEL}`;

    openaiWs = new WebSocket(url, {
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`
      }
    });

    openaiWs.on('open', () => {
      console.log('Connected to OpenAI Realtime API');
      isConnected = true;

      // Build instructions with pre-call context
      const instructions = `**Dr. Miller** is a high prescriber of cardiovascular meds but a "low-adopter" of Wegovy, likely viewing it as a cosmetic or secondary treatment rather than a primary tool for survival.

---

## **Sales Leadership Message: The "Weight Loss" Trap**

You are currently Dr. Miller's "GLP-1 update" guy, not his partner in reducing mortality. You've visited his office 10 times in 4 months. He likes you, he takes the lunch, and he agrees that "obesity is a problem." But then he goes back to his desk and treats obesity as a **lifestyle failure** while treating the resulting heart disease as a **medical one.** In 2026, if you are still leading with "pounds lost," you are losing the room. You must pivot from **Aesthetics** to **SELECT Data (Cardiovascular Outcomes)**. You need to stop selling a "thinner patient" and start selling a "protected patient."

### **Key Insights to Address:**

* **The Critical Opportunity:** Dr. Miller has **55 patients** in his panel who have established ASCVD and a BMI $\ge$ 27. These are not "weight loss" patients; they are "high-risk secondary prevention" patients.
* **The Leakage:** He currently has 15 patients on Zepbound and 10 on compounded semaglutide. He is treating weight as a commodity, unaware of the **20% MACE (Major Adverse Cardiovascular Events) reduction** unique to Wegovy's labeled indication.
* **The "Silent" Gap:** He has **30 patients** who have had a previous MI (Heart Attack) or Stroke and are currently on a statin and ACE inhibitor, but their BMI remains over 30. He is "managing" their risk while ignoring the primary driver of their next event.
* **Recent Activity:** He recently switched a patient from Wegovy back to "diet and exercise" because the patient reached a "goal weight." This proves he sees the drug as a **temporary fix**, not a chronic therapy.

---

## **Objection Scenarios**

Dr. Miller's resistance isn't about the drug's efficacy; it's about his **clinical philosophy.** He views Wegovy as an "add-on" rather than a pillar of care like a Beta-Blocker or Statin.

* **The "Cost-Benefit" Bias:** He believes that if a patient isn't "obese enough," the insurance battle isn't worth the cardiovascular benefit. He views the PA (Prior Authorization) as a tax on his staff's time.
* **The "Maintenance" Myth:** He thinks once the weight is off, the medication should stop. He doesn't realize that the CV benefits are tied to the **continuous metabolic shift**, not just the number on the scale.
* **The "Compounding" Distraction:** He is tempted by local compounding pharmacies for "affordability," ignoring the lack of outcome data and the safety risks of non-FDA-approved formulations.

---

## **Build The Approach Plan**

**Goal:** Move him from "Wegovy is for weight loss" to "Wegovy is for Heart Failure and MI prevention."

* **The Pivot:** Don't lead with "Your patients will lose 15% of their body weight." Lead with: **"Doctor, we are leaving 20% of your patients' CV protection on the table."**
* **The Challenge:** "Dr. Miller, we spend hours optimizing statins to get a 10 mg/dL drop in LDL. Yet, for your patients with a high BMI, we have a tool that reduces the risk of a repeat heart attack by 20%—regardless of how much weight they lose. Why is that not a first-line therapy in your post-MI protocol?"
* **The Administrative Bridge:** "We have a dedicated hub to handle the 'SELECT-protocol' PAs. Your staff won't be fighting for a 'diet drug'; they'll be processing a 'cardiovascular preventative.'"

---

## **Questions & Responses For Dr. Miller**

**The Discovery Question:** "Dr. Miller, for your post-MI patients who have a BMI over 30, what is your specific clinical goal for them beyond 'lose weight and take your statin'? If I told you a new ACE inhibitor reduced MACE by 20%, would you wait for the patient to 'try diet and exercise' first before prescribing it?"

**The Response:**
"Exactly. We wouldn't wait for a patient to 'try' to lower their blood pressure naturally if they've already had a stroke. We treat the risk.
Wegovy is no longer just a weight-loss injection; it's a **risk-reduction therapy.** Those 30 patients we identified who are post-MI are currently walking around with a 'metabolic gap' in their protection. By putting them on Wegovy, you aren't just helping them fit into smaller clothes—you are proactively preventing their next visit to the cath lab."

**The "Maintenance" Counter:**
"I noticed you recently discontinued Wegovy for a patient who hit their goal weight. If that patient's LDL hit 70, would you stop their statin? Of course not. The CV protection in the SELECT trial was sustained over years. Stopping therapy is effectively removing the shield we just put in place."

---

## **The Ask**

"I'm not asking you to put every patient who wants to lose ten pounds on Wegovy. I want to focus on your **highest-risk cohort.**

**Identify three patients on your schedule tomorrow who have already had a cardiovascular event and have a BMI over 30.** Instead of telling them to 'watch their calories,' will you commit to starting them on Wegovy as a **standard-of-care cardiovascular preventative**?"
      `;

      // Configure session (GA API format)
      const sessionConfig = {
        type: 'session.update',
        session: {
          type: 'realtime',
          output_modalities: ['audio'],
          instructions: instructions,
          audio: {
            input: {
              format: {
                type: 'audio/pcm',
                rate: 24000
              },
              transcription: {
                model: 'whisper-1'
              },
              turn_detection: {
                type: 'server_vad',
                threshold: 0.7,
                prefix_padding_ms: 300,
                silence_duration_ms: 1000,
                create_response: true
              }
            },
            output: {
              format: {
                type: 'audio/pcm',
                rate: 24000
              },
              voice: 'alloy',
              speed: 1.2
            }
          }
        }
      };

      openaiWs?.send(JSON.stringify(sessionConfig));

      // Trigger initial greeting
      setTimeout(() => {
        const greetingText = preCallContext
          ? 'Start the conversation by saying "Go for Jarvis" and then ask for the rep\'s name.'
          : 'Start by saying "Go for Jarvis" and ask the user for their name.';

        const greetingPrompt = {
          type: 'conversation.item.create',
          item: {
            type: 'message',
            role: 'user',
            content: [
              {
                type: 'input_text',
                text: greetingText
              }
            ]
          }
        };
        openaiWs?.send(JSON.stringify(greetingPrompt));

        const responseCreate = {
          type: 'response.create'
        };
        openaiWs?.send(JSON.stringify(responseCreate));
      }, 250);
    });

    openaiWs.on('message', (data: Buffer) => {
      try {
        const event: OpenAIEvent = JSON.parse(data.toString());

        // Log ALL events when awaiting confirmation to debug
        if (awaitingConfirmation && !event.type.includes('delta')) {
          console.log('📨 Event while awaiting confirmation:', event.type);
          if (event.transcript) {
            console.log('   Transcript in event:', event.transcript);
          }
        }

        // Handle different event types
        switch (event.type) {
          case 'response.audio.delta':
          case 'response.output_audio.delta':
            // Forward audio chunks to client (GA uses response.output_audio.delta)
            clientWs.send(JSON.stringify({
              type: 'audio_delta',
              data: event.delta
            }));
            break;

          case 'response.audio_transcript.delta':
          case 'response.output_audio_transcript.delta':
            // Forward agent transcript deltas (GA uses response.output_audio_transcript.delta)
            clientWs.send(JSON.stringify({
              type: 'agent_transcript_delta',
              delta: event.delta
            }));
            break;

          case 'response.audio_transcript.done':
          case 'response.output_audio_transcript.done':
            // Store and forward complete agent transcript
            const agentTranscript: UserTranscript = {
              id: event.item_id || `agent-${Date.now()}`,
              content: event.transcript,
              timestamp: Date.now()
            };
            agentTranscripts.push(agentTranscript);

            // Add to combined transcript list
            allTranscripts.push({
              type: 'agent',
              content: event.transcript,
              timestamp: Date.now(),
              id: agentTranscript.id
            });

            clientWs.send(JSON.stringify({
              type: 'agent_transcript_done',
              transcript: event.transcript
            }));

            // Check if agent is saying goodbye (as a fallback detection method)
            if (awaitingConfirmation) {
              console.log('🔍 CHECKING AGENT GOODBYE - awaiting confirmation is true');
              console.log('   Agent said:', event.transcript);
              const lowerTranscript = event.transcript.toLowerCase();
              console.log('   Looking for: good luck, you\'ve got this, goodbye');
              console.log('   Contains good luck?', lowerTranscript.includes('good luck'));
              console.log('   Contains you\'ve got this?', lowerTranscript.includes('you\'ve got this'));
              console.log('   Contains goodbye?', lowerTranscript.includes('goodbye'));

              if (lowerTranscript.includes('good luck') || lowerTranscript.includes('you\'ve got this') || lowerTranscript.includes('goodbye')) {
                console.log('🎯 AGENT SAID GOODBYE - Triggering conversation end');
                setTimeout(() => {
                  console.log('Sending conversation_ended event to client');
                  clientWs.send(JSON.stringify({
                    type: 'conversation_ended',
                    transcripts: allTranscripts
                  }));
                }, 2000);
              } else {
                console.log('❌ No goodbye phrase detected in agent response');
              }
            }
            break;

          case 'conversation.item.input_audio_transcription.completed':
            // Store and forward user transcript
            const userTranscript: UserTranscript = {
              id: event.item_id,
              content: event.transcript,
              timestamp: Date.now()
            };
            userTranscripts.push(userTranscript);

            // Add to combined transcript list
            allTranscripts.push({
              type: 'user',
              content: event.transcript,
              timestamp: Date.now(),
              id: event.item_id
            });

            clientWs.send(JSON.stringify({
              type: 'user_transcript',
              transcript: event.transcript,
              item_id: event.item_id
            }));

            // Check for end phrases
            console.log('=== USER TRANSCRIPT EVENT ===');
            console.log('User said:', event.transcript);
            console.log('Awaiting confirmation:', awaitingConfirmation);
            console.log('Transcript lowercase:', event.transcript.toLowerCase());

            if (containsEndPhrase(event.transcript) && !awaitingConfirmation) {
              console.log('✅ END PHRASE DETECTED in transcript:', event.transcript);
              awaitingConfirmation = true;
              clientWs.send(JSON.stringify({
                type: 'end_phrase_detected',
                transcript: event.transcript
              }));
            } else if (awaitingConfirmation) {
              console.log('🔍 CHECKING FOR YES PHRASE');
              console.log('Raw transcript:', event.transcript);
              console.log('Lowercased transcript:', event.transcript.toLowerCase().trim());

              const isYes = containsYesPhrase(event.transcript);
              console.log('✅ Contains yes phrase:', isYes);

              if (isYes) {
                console.log('🎯 USER CONFIRMED ENDING CONVERSATION:', event.transcript);
                console.log('Total user transcripts collected:', userTranscripts.length);
                console.log('Total agent transcripts collected:', agentTranscripts.length);
                console.log('Total combined transcripts:', allTranscripts.length);

                // Wait a moment for the AI to say goodbye, then end the conversation
                setTimeout(() => {
                  console.log('Sending conversation_ended event to client');
                  console.log('All transcripts being sent:', JSON.stringify(allTranscripts, null, 2));

                  clientWs.send(JSON.stringify({
                    type: 'conversation_ended',
                    transcripts: allTranscripts
                  }));

                  // Close OpenAI connection after a brief delay
                  setTimeout(() => {
                    console.log('Closing OpenAI connection');
                    if (openaiWs) {
                      openaiWs.close();
                      openaiWs = null;
                    }
                    awaitingConfirmation = false;
                  }, 1000);
                }, 3000); // Give AI 3 seconds to say goodbye
              }
            }
            break;

          case 'input_audio_buffer.speech_started':
            // User started speaking - this triggers interruption
            console.log('User started speaking (potential interruption)');
            clientWs.send(JSON.stringify({
              type: 'user_speaking_started'
            }));
            break;

          case 'input_audio_buffer.speech_stopped':
            clientWs.send(JSON.stringify({
              type: 'user_speaking_stopped'
            }));
            break;

          case 'response.output_item.done':
            // Response output item completed
            break;

          case 'response.done':
            clientWs.send(JSON.stringify({
              type: 'response_done'
            }));
            break;

          case 'input_audio_buffer.committed':
            // Audio buffer committed after user stops speaking
            console.log('Audio buffer committed - user finished speaking');
            break;

          case 'conversation.item.created':
            // New conversation item created
            break;

          case 'response.created':
            // New response started
            break;

          case 'error':
            console.error('OpenAI error:', event);
            clientWs.send(JSON.stringify({
              type: 'error',
              message: event.error?.message || 'Unknown error from OpenAI'
            }));
            break;
        }
      } catch (error) {
        console.error('Error parsing OpenAI message:', error);
      }
    });

    openaiWs.on('error', (error) => {
      console.error('OpenAI WebSocket error:', error);
      clientWs.send(JSON.stringify({
        type: 'error',
        message: 'Connection error with OpenAI'
      }));
    });

    openaiWs.on('close', () => {
      console.log('OpenAI connection closed');
      isConnected = false;
    });
  };

  // Handle client messages
  clientWs.on('message', (message: Buffer) => {
    try {
      const msg: ClientMessage = JSON.parse(message.toString());

      switch (msg.type) {
        case 'start_conversation':
          if (!isConnected) {
            userTranscripts = [];
            agentTranscripts = [];
            allTranscripts = [];
            connectToOpenAI();
          }
          break;

        case 'audio_data':
          if (openaiWs && isConnected && msg.data) {
            // Forward audio data to OpenAI
            const audioAppend = {
              type: 'input_audio_buffer.append',
              audio: msg.data
            };
            openaiWs.send(JSON.stringify(audioAppend));
          }
          break;

        case 'stop_conversation':
          // Send final transcripts (all - both user and agent)
          console.log('Manual stop - sending all transcripts:', allTranscripts.length);
          clientWs.send(JSON.stringify({
            type: 'final_transcripts',
            transcripts: allTranscripts
          }));

          // Close OpenAI connection
          if (openaiWs) {
            openaiWs.close();
            openaiWs = null;
          }
          break;
      }
    } catch (error) {
      console.error('Error handling client message:', error);
      clientWs.send(JSON.stringify({
        type: 'error',
        message: 'Error processing message'
      }));
    }
  });

  clientWs.on('close', () => {
    console.log('Client disconnected');
    if (openaiWs) {
      openaiWs.close();
      openaiWs = null;
    }
  });

  clientWs.on('error', (error) => {
    console.error('Client WebSocket error:', error);
  });
});

console.log('WebSocket server ready');
