# Conversation Start Guide

## Updated Flow: Jarvis Waits for Your Request

### What Changed

**Previously:**
- Jarvis would automatically start the pre-call briefing after you provided your name
- This was too proactive and didn't give you control

**Now:**
- Jarvis greets you and asks what you need
- **Waits for you to explicitly request** help with the pre-call prep
- Gives you control over when the briefing starts

## The New Conversation Start

### Step 1: Jarvis Greets You
```
Jarvis: "Go for Jarvis. What's your name?"
```

### Step 2: You Provide Your Name
```
You: "Manny"
```

### Step 3: Jarvis Asks What You Need
```
Jarvis: "How can I help you today, Manny?"
```

### Step 4: You Request the Briefing
```
You: "Can you help me prep for my call with Dr. Chavarria?"
```

### Step 5: Jarvis Starts the Briefing
```
Jarvis: "Absolutely. Your primary objective is to ADDRESS THE 21
         OCS-DEPENDENT ASTHMA PATIENTS NOT ON DUPIXENT..."
```

## Why This Change?

### 1. **User Control**
- You decide when to start the pre-call briefing
- You can use Jarvis for other things if needed
- No automatic assumptions about what you need

### 2. **Natural Conversation**
- More like a real assistant interaction
- Jarvis asks what you need instead of assuming
- Feels more conversational and less robotic

### 3. **Flexibility**
- You could ask Jarvis other questions first
- You could request specific information only
- You control the flow of the conversation

## Ways to Request the Briefing

Any of these will trigger the pre-call briefing:

### Direct Requests:
- "Can you help me prep for my call with Dr. Chavarria?"
- "I need to prepare for Dr. Chavarria"
- "Help me get ready for my call with Dr. Chavarria"
- "I need pre-call prep for Dr. Chavarria"

### Asking About the Doctor:
- "Tell me about Dr. Chavarria"
- "What do I need to know about Dr. Chavarria?"
- "Give me the briefing on Dr. Chavarria"

### General Requests:
- "Help me prepare for my call"
- "I need to get ready for my sales call"
- "What's my pre-call plan?"

## What If You Don't Request It?

If you ask something else, Jarvis will respond appropriately:

**Example 1: General Question**
```
You: "What's the weather like?"
Jarvis: "I'm not able to check the weather, but I can help you
         prepare for your call with Dr. Chavarria. Would you
         like to go over the pre-call plan?"
```

**Example 2: Different Request**
```
You: "Tell me about DUPIXENT"
Jarvis: "DUPIXENT is a biologic therapy for Type 2 inflammation...
         Would you like me to help you prepare for your call
         with Dr. Chavarria?"
```

## Full Example Conversation

```
🟢 Jarvis: "Go for Jarvis. What's your name?"

🔵 You: "Manny"

🟢 Jarvis: "How can I help you today, Manny?"

🔵 You: "Can you help me prep for my call with Dr. Chavarria?"

🟢 Jarvis: "Absolutely. Your primary objective is to ADDRESS
           THE 21 OCS-DEPENDENT ASTHMA PATIENTS NOT ON DUPIXENT.
           Here's the critical insight: Dr. Chavarria has 21
           patients suffering on ICS/LABA plus multiple rounds of
           oral corticosteroids. These patients are struggling
           with uncontrolled Type 2 inflammation and represent
           the EXACT patient profile that benefits most from
           DUPIXENT. Given his Bio-Hesitant Supporter profile,
           your role is to help him see the clinical imperative
           to intervene earlier with biologics."

🔵 You: [INTERRUPT] "Tell me the recent prescribing patterns"

🟢 Jarvis: "In December 2025, Dr. Chavarria prescribed 4.91 TRX
           of DUPIXENT Asthma, which is right on track with his
           24-month average of 4.78 TRX. However, there's a
           competitive threat: XOLAIR usage spiked to 2.00 TRX
           in December, which is 82% above normal levels..."

🔵 You: "What does the patient journey report show?"

🟢 Jarvis: "The patient journey report shows 21 alerts in the
           past 90 days. Here are the key findings..."

🔵 You: "I'm done"

🟢 Jarvis: "Are you sure you want to end our prep session?"

🔵 You: "Yes"

🟢 Jarvis: "Good luck with Dr. Chavarria, Manny! You've got this!"

[Conversation ends automatically]
[Full transcript displayed]
```

## Benefits of This Approach

### ✅ Natural Flow
- Feels like talking to a real assistant
- Not rushed into the briefing
- More conversational interaction

### ✅ User Agency
- You control when things start
- No assumptions about your needs
- Can pivot to different topics

### ✅ Clear Structure
- Greeting → Name → Request → Briefing
- Easy to understand progression
- Predictable conversation flow

### ✅ Flexibility
- Can ask questions before the briefing
- Can request specific information only
- Don't have to do the full briefing if you don't need it

## What to Expect

### After Providing Your Name:
- Jarvis will ask how it can help
- **Will NOT automatically start the briefing**
- **Waits for your explicit request**

### After Requesting Help:
- Jarvis immediately starts the briefing
- Reads the PRIMARY OBJECTIVE
- Provides key insights
- Ready to answer follow-up questions

### Throughout the Conversation:
- You can interrupt at any time
- Ask specific questions
- Change topics
- Control the flow

## Testing the New Flow

To test:

1. **Start the conversation**
2. **Wait for**: "Go for Jarvis. What's your name?"
3. **Provide your name**: "Manny"
4. **Wait for**: "How can I help you today, Manny?"
5. **Request briefing**: "Can you help me prep for my call with Dr. Chavarria?"
6. **Jarvis starts briefing** immediately

## Troubleshooting

### Issue: Jarvis starts briefing without me asking

This shouldn't happen anymore. If it does:
- Check the backend instructions in `backend/src/index.ts`
- Look for "WAIT for them to explicitly request help"
- Ensure the instructions are clear about not starting automatically

### Issue: Jarvis doesn't recognize my request

**Try these phrases:**
- "Help me prep for Dr. Chavarria"
- "I need to prepare for my call"
- "Can you brief me on Dr. Chavarria?"

If still not working, be more explicit:
- "Start the pre-call briefing"
- "Give me the pre-call plan"

## Summary

The conversation flow is now more natural and user-controlled:

1. **Greeting**: "Go for Jarvis"
2. **Name**: "What's your name?"
3. **Ask what you need**: "How can I help you?"
4. **Wait for your request**: You say what you need
5. **Start briefing**: Only when you ask

This gives you full control over when and how the briefing starts!
