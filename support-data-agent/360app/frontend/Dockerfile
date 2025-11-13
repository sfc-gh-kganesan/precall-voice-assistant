FROM node:22-bookworm

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install dependencies in a separate layer
RUN npm ci --no-audit --no-fund

# Copy source code after dependencies are installed
COPY . .

# Set theme - can be overridden with build arg
ARG THEME=gfinance
RUN echo "🎨 Setting theme to: ${THEME}" && \
    npm run theme ${THEME} && \
    echo "✅ Theme set successfully" && \
    ls -la app/themes/active-theme.css

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--port", "3000", "--hostname", "0.0.0.0"]
