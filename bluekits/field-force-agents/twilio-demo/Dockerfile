# ── Stage 1: Build React test-client ──────────────────────────────
FROM node:20-alpine AS client-build

WORKDIR /app/test-client
COPY test-client/package.json test-client/package-lock.json ./
RUN npm ci
COPY test-client/ ./
RUN npm run build

# ── Stage 2: Build backend TypeScript ─────────────────────────────
FROM node:20-alpine AS server-build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

# ── Stage 3: Production image ────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

# Install production dependencies only
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Compiled backend
COPY --from=server-build /app/dist ./dist

# Pre-built React client served by Express
COPY --from=client-build /app/test-client/dist ./test-client-dist

# Runtime data files
COPY pre-call-context.json ./

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "dist/index.js"]
