// Simple Express server that:
// 1. Serves the static React build
// 2. Proxies API requests to the backend using internal SPCS networking

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Backend URL - uses internal SPCS DNS when in SPCS, falls back to env var or localhost
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend.ivzu.svc.spcs.internal:8001';

console.log(`🔧 Backend URL: ${BACKEND_URL}`);

// API proxy - forwards /api/* requests to backend
app.use(
  '/api',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathRewrite: {
      '^/api': '', // Remove /api prefix when forwarding to backend
    },
    onProxyReq: (proxyReq, req, res) => {
      console.log(`[Proxy] ${req.method} ${req.path} -> ${BACKEND_URL}${req.path}`);
    },
    onError: (err, req, res) => {
      console.error(`[Proxy Error] ${err.message}`);
      res.status(500).json({
        error: 'Backend communication error',
        message: err.message,
      });
    },
  })
);

// Serve static files from build directory
app.use(express.static(path.join(__dirname, 'build')));

// SPA fallback - serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Server running on http://0.0.0.0:${PORT}`);
  console.log(`📡 Proxying /api/* requests to ${BACKEND_URL}`);
});
