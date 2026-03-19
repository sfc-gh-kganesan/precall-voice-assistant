# Jarvis Conversation Flow

## Overview

Jarvis is your AI pre-call assistant that helps you prepare for calls with healthcare providers by providing context, data, and strategic guidance.

## Expected Conversation Flow

### 1. **Initial Greeting**

**Jarvis will start with:**
> "Go for Jarvis"

Then ask for your name.

### 2. **Provide Your Name**

**You say:**
> "Manny" (or your name)

**Jarvis responds:**
> "How can I help you today?" or "What do you need?"

### 3. **Request Pre-Call Briefing**

**IMPORTANT:** Jarvis will NOT start the briefing automatically. You must explicitly request it.

**You say something like:**
- "Can you help me prep for my call with Dr. Chavarria?"
- "I need to prepare for Dr. Chavarria"
- "Tell me about Dr. Chavarria"
- "Help me get ready for my call"

### 4. **Jarvis Provides Primary Objective**

Once you request help, Jarvis will read out:
- The **PRIMARY OBJECTIVE** section
- The **critical insight** about the physician
- Key highlights about the opportunity

Example:
> "Your primary objective is to ADDRESS THE 21 OCS-DEPENDENT ASTHMA PATIENTS NOT ON DUPIXENT. Here's the critical insight: Dr. Chavarria has 21 patients suffering on ICS/LABA plus multiple rounds of oral corticosteroids..."

### 5. **Interactive Q&A Session**

You can interrupt Jarvis at any time to ask specific questions:

#### **Question: Recent Prescribing Patterns**
**You:** "Tell me the recent prescribing patterns for this doctor"

**Jarvis will provide:**
- DUPIXENT Asthma performance (December 2025: 4.91 TRX)
- 24-month average (4.78 TRX)
- Control limits and trends
- Peak capacity history
- **XOLAIR competitive threat** (82% spike in December!)
- LABA/ICS baseline volume

#### **Question: Patient Journey Report**
**You:** "What does the patient journey report show?"

**Jarvis will provide:**
- Total alerts in past 90 days (21 alerts)
- Pull-through failures (3 patients with PA approved but not shipped)
- Persistence risk (1 patient without copay card)
- **MASSIVE OPPORTUNITY**: 21 patients on ICS/LABA with ≥2 OCS refills
- COPD expansion opportunity (1 patient)

#### **Question: Objection Handling**
**You:** "This doctor has been telling me biologics are expensive and hard to get approved, how should I approach that?"

**Jarvis will provide:**
- The prepared response from the pre-call plan
- Specific talking points
- Data to counter the objection

**Example response:**
> "That's a valid concern, but the data shows your patients ARE getting approved - you have patients with PA approved right now. The challenge isn't access, it's pull-through. Let me connect you with our reimbursement team to make the process seamless. Plus, with copay assistance, most commercially insured patients pay $0 out of pocket."

#### **Other Questions You Can Ask:**

- "What's my recommended approach?"
- "What commitments should I request from this doctor?"
- "Tell me about the 21 OCS-dependent patients"
- "What resources should I bring?"
- "How do I handle the call fatigue concern?"
- "What are the key 3 messages?"
- "Walk me through the 6-step approach"

### 6. **Continuous Conversation**

You can ask follow-up questions, request clarification, or dive deeper into any topic. Jarvis has the full pre-call plan in context and can answer any question about:
- Prescribing data
- Patient alerts
- Competitive threats
- Objection handling
- Strategic approach
- Recommended commitments
- Resources

### 7. **Ending the Conversation**

**When you're ready to end:**

**You:** "I'm done" or "That's all I need" or "I'm ready for my call"

**Jarvis will:**
- Confirm if you want to end
- Wish you success on your call

## Example Full Conversation

```
Jarvis: "Go for Jarvis. What's your name?"

Rep: "Manny"

Jarvis: "How can I help you today, Manny?"

Rep: "Can you help me prep for my call with Dr. Chavarria?"

Jarvis: "Absolutely. Your primary objective is to ADDRESS THE 21 OCS-DEPENDENT
ASTHMA PATIENTS NOT ON DUPIXENT. Here's the critical insight: Dr. Chavarria
has 21 patients suffering on ICS/LABA plus multiple rounds of oral
corticosteroids. These patients are struggling with uncontrolled Type 2
inflammation and represent the EXACT patient profile that benefits most
from DUPIXENT..."

Rep: [INTERRUPTS] "Tell me the recent prescribing patterns for this doctor"

Jarvis: "In December 2025, Dr. Chavarria prescribed 4.91 TRX of DUPIXENT
Asthma, which is right on track with his 24-month average of 4.78 TRX.
However, there's a competitive threat: XOLAIR usage spiked to 2.00 TRX
in December, which is 82% above normal levels..."

Rep: "What does the patient journey report show?"

Jarvis: "The patient journey report shows 21 alerts in the past 90 days.
Here are the key findings: First, there are 3 pull-through failures -
patients with Prior Authorization approved but DUPIXENT wasn't shipped.
Second, there's 1 patient at persistence risk who had their first fill
but didn't use a copay card. Third, and most importantly, there are
21 patients with asthma on ICS/LABA who received 2 or more refills of
oral corticosteroids WITHOUT ever receiving DUPIXENT..."

Rep: "This doctor has been telling me biologics are expensive and hard
to get approved. How should I approach that?"

Jarvis: "Great question. Here's how to handle that objection: 'That's a
valid concern, but the data shows your patients ARE getting approved -
you have patients with PA approved right now. The challenge isn't access,
it's pull-through. Let me connect you with our reimbursement team to make
the process seamless. Plus, with copay assistance, most commercially
insured patients pay $0 out of pocket.'"

Rep: "Perfect. I think I'm ready."

Jarvis: "Are you sure you want to end our prep session?"

Rep: "Yes"

Jarvis: "Good luck with Dr. Chavarria, Manny. You've got this!"
```

## Tips for Best Results

1. **Be specific with your questions** - The more specific you are, the more targeted Jarvis's response will be
2. **Interrupt when needed** - You can interrupt Jarvis at any time to ask questions
3. **Ask for examples** - If you need clarification, ask Jarvis to explain further
4. **Practice objection handling** - Use Jarvis to rehearse your responses to common objections
5. **Review key data points** - Make sure you understand the prescribing patterns and patient opportunities before your call

## Troubleshooting

**If Jarvis doesn't have the pre-call context:**
- Check that `backend/pre-call-context.json` exists
- Restart the backend server
- Look for "Pre-call context loaded successfully" in the console

**If Jarvis doesn't respond as expected:**
- Make sure you're speaking clearly
- Wait for Jarvis to finish speaking before interrupting
- Rephrase your question if needed

**If you need different context:**
- Update the `backend/pre-call-context.json` file with the new physician's information
- Restart the backend server
