// Simple WebSocket test client
const WebSocket = require('ws');

console.log('Testing WebSocket connection to ws://localhost:3000/test-client...');

const ws = new WebSocket('ws://localhost:3000/test-client');

ws.on('open', () => {
  console.log('✅ WebSocket connected successfully!');
});

ws.on('message', (data) => {
  console.log('📩 Received:', data.toString());
});

ws.on('error', (error) => {
  console.error('❌ WebSocket error:', error.message);
});

ws.on('close', (code, reason) => {
  console.log('⚫ WebSocket closed:', code, reason.toString());
  process.exit(0);
});

// Close after 5 seconds
setTimeout(() => {
  console.log('Closing connection...');
  ws.close();
}, 5000);
