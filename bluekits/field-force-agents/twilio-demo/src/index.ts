import express from 'express';
import { createServer } from 'http';
import path from 'path';
import fs from 'fs';
import WebSocket from 'ws';
import { env } from './config/env';
import { logger } from './utils/logger';
import { loadPreCallPlan, buildSystemPrompt } from './services/preCallPlanService';
import { OpenAIRealtimeClient } from './services/openAIRealtimeClient';
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

// Serve React client build in production / container
const clientDistPath = path.join(__dirname, '..', 'test-client-dist');
app.use(express.static(clientDistPath));

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
 * WebSocket server for voice client connections
 */
const wss = new WebSocket.Server({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const pathname = request.url;

  if (pathname === '/test-client') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  } else {
    socket.destroy();
  }
});

wss.on('connection', async (ws: WebSocket) => {
  logger.info('New voice client WebSocket connection');

  try {
    const preCallPlan = loadPreCallPlan();
    const systemPrompt = buildSystemPrompt(preCallPlan);

    logger.info('Pre-call plan loaded, connecting to OpenAI...');

    const openAIClient = new OpenAIRealtimeClient({
      model: env.OPENAI_MODEL,
      apiKey: env.OPENAI_API_KEY,
      systemPrompt,
      voice: 'alloy',
    });

    await openAIClient.connect();

    logger.info('OpenAI connected, creating client handler');

    new TestClientHandler(ws, openAIClient);

    logger.info('Client handler initialized');
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    logger.error('Error setting up voice client:', errorMessage, error);

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'error',
        message: `Failed to connect to OpenAI: ${errorMessage}`,
      }));
    }

    ws.close();
  }
});

wss.on('error', (error) => {
  logger.error('WebSocket server error:', error);
});

/**
 * API info endpoint
 */
app.get('/api', (_req, res) => {
  res.json({
    name: 'Pre-Call Voice Assistant',
    description: 'Voice assistant for pharmaceutical sales rep pre-call preparation',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      voiceClient: '/test-client (WebSocket)',
    },
  });
});

// SPA fallback — serve index.html for any unmatched GET so the React app handles routing
const clientIndex = path.join(clientDistPath, 'index.html');
app.use((req, res, next) => {
  if (req.method === 'GET' && req.accepts('html') && fs.existsSync(clientIndex)) {
    return res.sendFile(clientIndex);
  }
  next();
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
