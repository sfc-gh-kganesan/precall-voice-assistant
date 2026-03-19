# Quick Start Guide

Get your Pre-Call Voice Assistant running in 10 minutes.

## Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

## Step 2: Deploy to Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Render auto-detects `render.yaml` ✅
5. Add environment variables:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
   - `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
6. Click **Create Web Service**
7. Wait for deployment to complete

## Step 3: Get Your Webhook URL

After deployment, copy your Render URL:
```
https://your-service-name.onrender.com
```

## Step 4: Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Click your phone number
3. Under "Voice Configuration":
   - A CALL COMES IN: **Webhook**
   - URL: `https://your-service-name.onrender.com/voice/incoming`
   - HTTP: **POST**
4. Click **Save**

## Step 5: Test It!

Call your Twilio phone number and say:

> "Go for Jarvis"

Then ask questions like:
- "What's the primary objective?"
- "Tell me about the 21 patients not on DUPIXENT"
- "How do I handle objections about biologics being expensive?"

## Verify Deployment

Check your app is running:
```bash
curl https://your-service-name.onrender.com/health
```

Should return:
```json
{
  "status": "ok",
  "timestamp": "2026-01-19T...",
  "environment": "production"
}
```

## Optional: Run Locally for Development

If you want to test locally before deploying:

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Add your credentials to `.env`:
   ```env
   OPENAI_API_KEY=sk-...
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   ```

4. Run in development mode:
   ```bash
   npm run dev
   ```

## Troubleshooting

**Render deployment fails?**
- Check environment variables are set correctly
- Review build logs in Render dashboard
- Ensure all required variables are added (OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

**Call connects but no audio?**
- Verify webhook URL is correct and uses HTTPS
- Check Render logs: Dashboard → Logs tab
- Ensure your Render service is running (not sleeping)

**OpenAI connection fails?**
- Verify your OpenAI API key is valid
- Ensure you have Realtime API access (may need to request beta access)
- Check Render logs for OpenAI error messages

**Twilio webhook errors?**
- Make sure webhook URL includes `/voice/incoming`
- Verify HTTP method is set to POST
- Check that Render service is deployed and healthy

**Need help?**
- Check [README.md](README.md) for detailed documentation
- Review Render logs in the dashboard
- Verify health endpoint: `https://your-service-name.onrender.com/health`

## Next Steps

- Customize `pre-call-context.json` with your own data
- Modify the system prompt in `src/services/preCallPlanService.ts`
- Adjust voice settings (alloy, echo, shimmer) in `src/index.ts`
- Add authentication for production security

Happy calling! 📞
