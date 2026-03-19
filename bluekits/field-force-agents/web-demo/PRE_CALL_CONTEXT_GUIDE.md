# Pre-Call Context Configuration Guide

## Overview

This application now supports loading pre-call context to help sales reps practice their calls with healthcare providers. The AI agent will role-play as the physician and challenge the rep with realistic objections based on the physician's profile and data.

## How It Works

### 1. Context File Location

The pre-call context is loaded from:
```
backend/pre-call-context.json
```

### 2. What Happens When Context is Loaded

When the backend starts, it automatically:
- Loads the `pre-call-context.json` file
- Parses the physician profile, prescribing data, and strategic insights
- Configures the AI agent with this information
- The AI agent role-plays as the physician during the conversation

### 3. AI Behavior with Context

**With context loaded:**
- AI introduces itself as helping prepare for a call with the specific physician
- AI knows the physician's prescribing patterns, segment, and challenges
- AI can role-play objections based on the physician's profile
- AI provides realistic pushback to help the rep practice

**Without context (default mode):**
- AI acts as a friendly general conversational assistant
- No specific physician context is used

## How to Update the Context

### Option 1: Edit the JSON file directly

1. Open `backend/pre-call-context.json`
2. Update the relevant fields:
   - `hcp_name`: Physician name
   - `rep_name`: Sales rep name
   - `smart_alerts`: Current patient opportunities
   - `objection_handling`: Expected objections and responses
   - Other fields as needed
3. Restart the backend server

### Option 2: Replace with a new context file

1. Create a new JSON file with the same structure
2. Replace `backend/pre-call-context.json` with your new file
3. Restart the backend server

## JSON Structure

The context file includes:

```json
{
  "hcp_id": "Physician ID",
  "hcp_name": "Dr. Name",
  "rep_name": "Rep Name",
  "specialty": "Specialty",
  "segment": "Segment classification",
  "primary_objective": "Main call objective",
  "prescribing_trends": { /* Data */ },
  "smart_alerts": { /* Opportunities */ },
  "objection_handling": [ /* Expected objections */ ],
  "recommended_approach": [ /* Call flow steps */ ],
  "key_commitments": [ /* Desired commitments */ ]
}
```

## Testing the Context

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Start the backend:**
   ```bash
   npm start
   ```

3. **Check the console:**
   You should see: `Pre-call context loaded successfully`

4. **Start a conversation:**
   - The AI should reference the physician's name and context
   - Practice your call approach
   - The AI will challenge you with objections

## Example Conversation Flow

**AI (role-playing as physician):**
> "Hello Manny, I see you're back again. You and Therese have been coming by quite often. What can I do for you today?"

**Rep:**
> "Dr. Chavarria, I appreciate your time. I wanted to discuss the 21 patients you have on ICS/LABA who needed multiple rounds of oral corticosteroids..."

**AI (challenging):**
> "I'm comfortable with my current approach. These patients are doing okay on ICS/LABA plus OCS when needed."

**Rep:**
> [Practices handling the objection using the recommended response from the context]

## Deployment to Render

The `pre-call-context.json` file will be included in your deployment since it's in the `backend/` directory. Make sure to:

1. **Commit the context file:**
   ```bash
   git add backend/pre-call-context.json
   git commit -m "Add pre-call context configuration"
   git push
   ```

2. **Deploy to Render** using the same build/start commands

## Security Note

⚠️ **Important:** The `pre-call-context.json` file may contain sensitive physician and patient data.

**Best practices:**
- Do NOT commit real PHI (Protected Health Information) to public repositories
- Use anonymized or test data for development
- For production, consider loading context from a secure API or encrypted storage
- Add `pre-call-context.json` to `.gitignore` if using real data locally

## Updating Context for Different Calls

To practice calls with different physicians:

1. Save multiple context files: `dr-smith-context.json`, `dr-jones-context.json`, etc.
2. Copy the relevant one to `backend/pre-call-context.json` before starting the server
3. Or modify the backend to accept a context parameter and switch dynamically

## Troubleshooting

**Context not loading:**
- Check console for: `Pre-call context loaded successfully`
- If you see a warning, verify the JSON file exists and is valid JSON
- Verify the file path is correct: `backend/pre-call-context.json`

**AI not using context:**
- Restart the backend server after updating the context file
- Verify the JSON structure matches the expected format
- Check the backend logs for any parsing errors

**Build errors:**
- Run `npm run build` to ensure TypeScript compiles
- Check for syntax errors in the JSON file
