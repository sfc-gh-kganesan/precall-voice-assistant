#!/bin/bash

# Start Local Test Environment
# Runs both backend and test client in parallel

echo "🚀 Starting Voice Assistant Local Test Environment"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with required variables:"
    echo "  - OPENAI_API_KEY"
    echo "  - TWILIO_ACCOUNT_SID"
    echo "  - TWILIO_AUTH_TOKEN"
    echo ""
    echo "Run: cp .env.example .env"
    exit 1
fi

# Install backend dependencies if needed
if [ ! -d node_modules ]; then
    echo "📦 Installing backend dependencies..."
    npm install
fi

# Install test client dependencies if needed
if [ ! -d test-client/node_modules ]; then
    echo "📦 Installing test client dependencies..."
    cd test-client
    npm install
    cd ..
fi

# Build backend
echo "🔨 Building backend..."
npm run build

echo ""
echo "✅ Setup complete!"
echo ""
echo "Starting servers..."
echo "  - Backend:     http://localhost:3000"
echo "  - Test Client: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start both servers in parallel
npm run dev &
BACKEND_PID=$!

cd test-client
npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
