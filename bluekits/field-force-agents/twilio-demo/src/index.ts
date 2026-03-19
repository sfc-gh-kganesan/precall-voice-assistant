import express from 'express';
import { createServer } from 'http';
import WebSocket from 'ws';
import { env } from './config/env';
import { logger } from './utils/logger';
import { loadPreCallPlan, buildSystemPrompt } from './services/preCallPlanService';
import { OpenAIRealtimeClient } from './services/openAIRealtimeClient';
import { TwilioMediaStreamHandler } from './services/twilioMediaStreamHandler';
import { TestClientHandler } from './services/testClientHandler';

const app = express();
const server = createServer(app);

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// CORS for local development
if (env.NODE_ENV === 'development') {
  app.use((_req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type');
    next();
  });
}

// Request logging middleware
app.use((req, _res, next) => {
  logger.info(`${req.method} ${req.path}`);
  next();
});

/**
 * Health check endpoint
 */
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    environment: env.NODE_ENV,
  });
});

/**
 * Twilio incoming call webhook
 * Returns TwiML to start a Media Stream
 */
const handleIncomingCall = (req: express.Request, res: express.Response) => {
  logger.info('Incoming call', {
    from: req.body?.From,
    to: req.body?.To,
    callSid: req.body?.CallSid,
  });

  const domain = env.DOMAIN || req.get('host');
  const protocol = env.NODE_ENV === 'production' ? 'wss' : 'ws';
  const streamUrl = `${protocol}://${domain}/media-stream`;

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${streamUrl}" />
  </Connect>
</Response>`;

  res.type('text/xml');
  res.send(twiml);
};

app.post('/voice/incoming', handleIncomingCall);
app.post('/incoming-call', handleIncomingCall); // Alias for convenience

/**
 * WebSocket servers with noServer mode for manual upgrade handling
 */
const wss = new WebSocket.Server({ noServer: true });
const testClientWss = new WebSocket.Server({ noServer: true });

// Handle WebSocket upgrades manually
server.on('upgrade', (request, socket, head) => {
  const pathname = request.url;

  if (pathname === '/media-stream') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  } else if (pathname === '/test-client') {
    testClientWss.handleUpgrade(request, socket, head, (ws) => {
      testClientWss.emit('connection', ws, request);
    });
  } else {
    socket.destroy();
  }
});

wss.on('connection', async (ws: WebSocket) => {
  logger.info('New WebSocket connection for media stream');

  try {
    // Load pre-call plan and build system prompt
    const preCallPlan = loadPreCallPlan();
    const systemPrompt = buildSystemPrompt(preCallPlan);

    // Create OpenAI Realtime client
    const openAIClient = new OpenAIRealtimeClient({
      model: env.OPENAI_MODEL,
      apiKey: env.OPENAI_API_KEY,
      systemPrompt,
      voice: 'alloy',
    });

    // Connect to OpenAI
    await openAIClient.connect();

    // Create media stream handler
    new TwilioMediaStreamHandler(ws, openAIClient);

    logger.info('Media stream handler initialized');
  } catch (error) {
    logger.error('Error setting up media stream:', error);
    ws.close();
  }
});

wss.on('error', (error) => {
  logger.error('WebSocket server error:', error);
});

testClientWss.on('connection', async (ws: WebSocket) => {
  logger.info('New test client WebSocket connection');

  try {
    // Load pre-call plan and build system prompt
    const preCallPlan = loadPreCallPlan();
    const systemPrompt = buildSystemPrompt(preCallPlan);

    logger.info('Pre-call plan loaded, connecting to OpenAI...');

    // Create OpenAI Realtime client
    const openAIClient = new OpenAIRealtimeClient({
      model: env.OPENAI_MODEL,
      apiKey: env.OPENAI_API_KEY,
      systemPrompt,
      voice: 'alloy',
    });

    // Connect to OpenAI
    await openAIClient.connect();

    logger.info('OpenAI connected, creating test client handler');

    // Create test client handler
    new TestClientHandler(ws, openAIClient);

    logger.info('Test client handler initialized');
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    logger.error('Error setting up test client:', errorMessage, error);

    // Send error to client before closing
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'error',
        message: `Failed to connect to OpenAI: ${errorMessage}`,
      }));
    }

    ws.close();
  }
});

testClientWss.on('error', (error) => {
  logger.error('Test client WebSocket server error:', error);
});

/**
 * Root endpoint
 */
app.get('/', (_req, res) => {
  res.json({
    name: 'Twilio OpenAI Pre-Call Voice Assistant',
    description: 'Voice assistant for pharmaceutical sales rep pre-call preparation',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      incomingCall: '/voice/incoming',
      mediaStream: '/media-stream (WebSocket - for Twilio)',
      testClient: '/test-client (WebSocket - for browser testing)',
    },
    testClient: {
      info: 'Use the React test client in /test-client directory to test locally',
      url: `http://localhost:${env.PORT}`,
    },
  });
});

/**
 * 404 handler
 */
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    path: req.path,
  });
});

/**
 * Error handler
 */
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: env.NODE_ENV === 'development' ? err.message : undefined,
  });
});

/**
 * Start server
 */
server.listen(env.PORT, () => {
  logger.info(`Server started on port ${env.PORT}`);
  logger.info(`Environment: ${env.NODE_ENV}`);
  logger.info(`Health check: http://localhost:${env.PORT}/health`);
});

/**
 * Graceful shutdown
 */
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
});
