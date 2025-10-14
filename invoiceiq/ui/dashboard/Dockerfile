# Dockerfile for InvoiceIQ Frontend
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Copy server file
COPY server.js ./

# Expose port
EXPOSE 3000

# Start production server with proxy
CMD ["node", "server.js"]
