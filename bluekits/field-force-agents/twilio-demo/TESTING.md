# Testing Guide

Complete guide for testing the voice assistant locally and in production.

## Table of Contents

1. [Local Browser Testing](#local-browser-testing)
2. [Production Testing with Twilio](#production-testing-with-twilio)
3. [Sample Conversation Flow](#sample-conversation-flow)
4. [Testing Checklist](#testing-checklist)
5. [Troubleshooting](#troubleshooting)

## Local Browser Testing

### Quick Start (Automated)

Use the provided script to start both servers:

```bash
./start-local-test.sh
```

This will:
- Install dependencies
- Build the backend
- Start backend on `http://localhost:3000`
- Start test client on `http://localhost:5173`

### Manual Start

**Terminal 1 - Backend:**
```bash
npm install
npm run dev
```

**Terminal 2 - Test Client:**
```bash
cd test-client
npm install
npm run dev
```

**Browser:**
Open `http://localhost:5173`

### Testing Steps

1. **Connect**
   - Click "📞 Start Call with Jarvis"
   - Allow microphone access
   - Wait for "🟢 Connected" status

2. **Initial Greeting**
   - Jarvis should say "Go for Jarvis"
   - This confirms the connection is working

3. **Ask Questions**
   - Speak clearly into your microphone
   - Wait for Jarvis to finish speaking before asking next question
   - Use example questions below

4. **Verify Responses**
   - Check that responses match pre-call plan data
   - Verify audio is clear and understandable
   - Confirm transcript updates in real-time

5. **Disconnect**
   - Click "⏹️ End Call"
   - Verify clean disconnection

## Production Testing with Twilio

### Prerequisites

- Deployed to Render (or other hosting)
- Twilio phone number configured
- Webhook URL: `https://your-app.onrender.com/voice/incoming`

### Testing Steps

1. **Call Your Twilio Number**
   - Dial the number from your phone
   - Wait for connection

2. **Listen for Greeting**
   - Jarvis should answer with "Go for Jarvis"
   - If silent, check Render logs

3. **Conduct Test Conversation**
   - Ask questions from the list below
   - Verify accurate responses
   - Test objection handling

4. **End Call**
   - Hang up or let Jarvis complete responses
   - Check Render logs for any errors

## Sample Conversation Flow

### Opening

**You:** "Hello Jarvis"

**Jarvis:** "Go for Jarvis. How can I help you prepare for your call with Dr. Chavarria?"

### Core Questions to Test

#### 1. Primary Objective
**You:** "What's the primary objective for this call?"

**Expected:** Should mention the 21 OCS-dependent asthma patients not on DUPIXENT

#### 2. Patient Data
**You:** "Tell me about the 21 untapped patients"

**Expected:** Should explain they're on ICS/LABA with multiple OCS bursts, ideal DUPIXENT candidates

#### 3. Prescribing Trends
**You:** "What are Dr. Chavarria's current prescribing trends?"

**Expected:** Should mention:
- DUPIXENT: ~5 TRx/month
- Peak of 9.74 in August 2024
- XOLAIR spike (2.00 TRx, 82% above normal)

#### 4. Competitive Threat
**You:** "How should I handle the XOLAIR competitive threat?"

**Expected:** Should discuss:
- XOLAIR is spiking above UCL
- DUPIXENT's MOA (IL-4 and IL-13 blocking)
- Better for OCS-dependent patients with elevated eosinophils

#### 5. Call Fatigue
**You:** "Should I be concerned about call fatigue?"

**Expected:** Should mention:
- 52 calls in past 6 months
- 2 calls per week frequency
- Co-calling with Therese Ogbonna Dodds
- Risk of overwhelming the physician

#### 6. Objection Handling
**You:** "What if he says biologics are too expensive?"

**Expected:** Should provide the objection response about:
- PAs already getting approved
- Copay assistance ($0 for most patients)
- Reimbursement support available

#### 7. Resources
**You:** "What resources should I bring?"

**Expected:** Should list:
- HCP Checklist
- Wall Chart for Type 2 inflammation
- Key 3 messaging
- Co-pay card info
- FRM contact info
- QUEST/VENTURE study materials

#### 8. Action Plan
**You:** "What's my action plan for this call?"

**Expected:** Should cover:
- Focus on 21 OCS-dependent patients
- Position as problem-solver
- Request commitment to evaluate one patient
- Coordinate with Therese on visit frequency

### Edge Cases to Test

**Out of Scope Question:**
**You:** "What's the weather like today?"

**Expected:** "I don't have that in the pre-call plan for Dr. Chavarria."

**Interruption Test:**
Start asking a new question while Jarvis is speaking.

**Expected:** Jarvis should stop and address the new question.

**Complex Medical Terms:**
**You:** "What about eosinophil levels?"

**Expected:** Should pronounce "ee-oh-SIN-oh-fills" correctly and reference ≥150 cells/µL threshold.

## Testing Checklist

### Functionality Tests

- [ ] Connection establishes successfully
- [ ] Initial greeting plays ("Go for Jarvis")
- [ ] Voice input is recognized
- [ ] Audio output is clear
- [ ] Responses are accurate to pre-call plan
- [ ] Handles interruptions gracefully
- [ ] Pronounces medical terms correctly
- [ ] Stays within 30-second response limit
- [ ] Refuses out-of-scope questions politely
- [ ] Disconnection is clean

### Data Accuracy Tests

- [ ] HCP information is correct
- [ ] Prescribing numbers are accurate
- [ ] Alert counts match (21 untapped, 3 pull-through failures, etc.)
- [ ] Objection responses match pre-call plan
- [ ] Recommended approach follows 6 steps
- [ ] Strategic summary points are covered

### Performance Tests

- [ ] Response latency < 2 seconds
- [ ] No audio dropouts or stuttering
- [ ] WebSocket stays connected for 5+ minutes
- [ ] Handles rapid-fire questions
- [ ] Memory usage stays reasonable

### Browser Compatibility (Test Client Only)

- [ ] Chrome
- [ ] Safari
- [ ] Firefox
- [ ] Edge

## Troubleshooting

### Local Testing Issues

**Backend won't start:**
```bash
# Check if port 3000 is already in use
lsof -ti:3000 | xargs kill -9

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

**Test client won't connect:**
- Verify backend is running on port 3000
- Check browser console for WebSocket errors
- Ensure CORS is enabled in backend (development mode)

**No audio output:**
- Check browser's audio permissions
- Verify system audio is not muted
- Try different browser

**Microphone not working:**
- Grant microphone permissions in browser
- Check system microphone settings
- Test microphone in other apps

### Production Issues

**Call connects but silent:**
- Check Render logs for errors
- Verify OpenAI API key is valid
- Ensure Realtime API access is enabled

**Webhook errors:**
- Verify webhook URL is correct
- Check SSL certificate is valid
- Ensure Render service is running

**Audio is garbled:**
- Check audio conversion functions
- Verify sample rate handling (8kHz ↔ 24kHz)
- Review mulaw encoding/decoding

**Connection drops:**
- Check Render logs for timeouts
- Verify WebSocket stays alive
- Monitor Render service health

## Monitoring

### Backend Logs

Watch logs in real-time:
```bash
# Local
npm run dev

# Render
# Check Logs tab in Render dashboard
```

### Key Log Events

- `OpenAI Realtime API connected`
- `Media stream handler initialized`
- `User started speaking`
- `User stopped speaking`
- `OpenAI WebSocket closed`

### Health Check

```bash
# Local
curl http://localhost:3000/health

# Production
curl https://your-app.onrender.com/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2026-01-19T...",
  "environment": "production"
}
```

## Performance Benchmarks

### Expected Metrics

- **Connection time:** < 2 seconds
- **First response:** < 3 seconds from speech end
- **Response latency:** < 2 seconds
- **Audio quality:** Clear, no distortion
- **Uptime:** 99%+

### Load Testing

For production, test with:
- Multiple concurrent calls
- Long conversation duration (10+ minutes)
- Rapid question sequences
- Various audio quality conditions

## Test Data Updates

To test with different pre-call plans:

1. Modify `pre-call-context.json`
2. Restart backend server
3. Verify new data appears in responses

Example: Change HCP name and verify Jarvis uses new name in responses.

## Feedback Collection

When testing, note:
- Response accuracy
- Audio quality issues
- Latency problems
- Unexpected behaviors
- Feature requests

Create issues on GitHub with detailed descriptions and steps to reproduce.

## Next Steps

After successful testing:

1. ✅ Verify all checklist items pass
2. ✅ Test in production environment
3. ✅ Conduct user acceptance testing
4. ✅ Document any customizations
5. ✅ Set up monitoring and alerts
6. ✅ Train users on how to use the system

## Support

For issues during testing:
- Check [README.md](README.md) for setup help
- Review [test-client/README.md](test-client/README.md) for browser testing
- Check Render logs for production errors
- Open GitHub issue with details
