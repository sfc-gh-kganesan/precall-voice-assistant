# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./
COPY packages/ ./packages/

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Build the frontend
RUN npm run build

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

# Install production server dependencies
RUN npm install -g serve http-proxy-middleware express

# Copy built assets
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/server ./server

# Create simple Express server for proxying
RUN echo 'const express = require("express");' > server.js && \
    echo 'const { createProxyMiddleware } = require("http-proxy-middleware");' >> server.js && \
    echo 'const path = require("path");' >> server.js && \
    echo '' >> server.js && \
    echo 'const app = express();' >> server.js && \
    echo 'const PORT = process.env.PORT || 3001;' >> server.js && \
    echo 'const P67_API_URL = process.env.P67_API_URL || "http://controld.ghw6if.svc.spcs.internal:80";' >> server.js && \
    echo '' >> server.js && \
    echo '// Health check endpoint' >> server.js && \
    echo 'app.get("/health", (req, res) => res.json({ status: "healthy" }));' >> server.js && \
    echo '' >> server.js && \
    echo '// Proxy API requests to p67 controld' >> server.js && \
    echo 'app.use("/api", createProxyMiddleware({' >> server.js && \
    echo '  target: P67_API_URL,' >> server.js && \
    echo '  changeOrigin: true,' >> server.js && \
    echo '  pathRewrite: { "^/api": "/api" },' >> server.js && \
    echo '  onProxyReq: (proxyReq, req) => {' >> server.js && \
    echo '    // Forward auth headers' >> server.js && \
    echo '    if (req.headers["sf-context-current-user"]) {' >> server.js && \
    echo '      proxyReq.setHeader("sf-context-current-user", req.headers["sf-context-current-user"]);' >> server.js && \
    echo '    }' >> server.js && \
    echo '  }' >> server.js && \
    echo '}));' >> server.js && \
    echo '' >> server.js && \
    echo '// Serve static files' >> server.js && \
    echo 'app.use(express.static(path.join(__dirname, "dist")));' >> server.js && \
    echo '' >> server.js && \
    echo '// SPA fallback' >> server.js && \
    echo 'app.get("*", (req, res) => {' >> server.js && \
    echo '  res.sendFile(path.join(__dirname, "dist", "index.html"));' >> server.js && \
    echo '});' >> server.js && \
    echo '' >> server.js && \
    echo 'app.listen(PORT, () => console.log(`Dashboard running on port ${PORT}`));' >> server.js

# Install runtime dependencies
RUN npm install express http-proxy-middleware

EXPOSE 3001

CMD ["node", "server.js"]
