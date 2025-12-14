# Controld Service

Control plane service for P67 platform.

## Overview

Controld is a TypeScript-based microservice built with the Fastify web framework. It provides a high-performance API with automatic OpenAPI documentation generation and Swagger UI integration using Zod for type-safe validation.

## Technology Stack

- **Runtime**: Node.js with ESM modules
- **Framework**: Fastify 5.2.0 (fast, low-overhead web framework)
- **API Documentation**: @fastify/swagger, @fastify/swagger-ui
- **Type Provider**: fastify-type-provider-zod
- **Validation**: Zod 4.1.13 for schema validation
- **Language**: TypeScript 5.9.3
- **Target**: ES2022

## Getting Started

### Prerequisites

- Node.js 20+
- pnpm 10.22.0+

### Installation

From the project root:

```bash
pnpm install
```

### Development

Start the development server with hot reload:

```bash
pnpm dev
```

The service will start on `http://localhost:3002` by default.

### Build

Compile TypeScript to JavaScript:

```bash
pnpm build
```

### Production

Run the compiled production build:

```bash
pnpm start
```

## API Documentation

Once the service is running, you can access:

- **Swagger UI**: http://localhost:3002/docs
- **OpenAPI Schema**: http://localhost:3002/docs/json

## Available Endpoints

### Health Check

- **GET** `/api/health` - Returns service health status

```json
{
  "status": "ok",
  "timestamp": "2025-12-13T10:00:00.000Z"
}
```

## Project Structure

```
controld/
├── src/
│   ├── index.ts              # Main Fastify application
│   ├── config.ts             # Service configuration
│   ├── schema.ts             # Zod validation schemas
│   └── routes/
│       ├── api.ts           # Main API plugin
│       └── health.ts        # Health check route
├── dist/                     # Compiled output (generated)
├── package.json             # Dependencies and scripts
├── tsconfig.json            # TypeScript configuration
├── eslint.config.js         # ESLint configuration
└── .gitignore              # Git ignore patterns
```

## Import Paths

This project uses **absolute imports** via TypeScript path aliases for cleaner, more maintainable code.

### Path Alias Configuration

All imports use the `@controld/*` alias pattern, configured in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": "./",
    "paths": {
      "@controld/*": ["src/*"]
    }
  }
}
```

### Import Examples

```typescript
// Instead of relative imports:
import { HealthResponseSchema } from '../schema.js';
import { GoogleOAuthClient } from '../lib/oauth/google-client.js';
import health from './health.js';

// Use absolute imports:
import { HealthResponseSchema } from '@controld/schema.js';
import { GoogleOAuthClient } from '@controld/lib/oauth/google-client.js';
import health from '@controld/routes/health.js';
```

### How It Works

**Development Mode (`pnpm dev`)**
- Uses `tsx` which natively supports TypeScript path aliases
- No transformation needed - imports work directly

**Production Mode (`pnpm build` + `pnpm start`)**
- TypeScript compiler (`tsc`) compiles `.ts` to `.js`
- `tsc-alias` transforms path aliases to relative paths in compiled output
- Node.js runs the transformed code with standard relative imports

**Note**: All imports must include the `.js` extension (ESM requirement), even when importing `.ts` files during development.

### Benefits

- **Cleaner imports**: No need to calculate relative path depth (`../../`)
- **Easy refactoring**: Move files without updating import paths
- **Better IDE support**: Improved autocomplete and navigation
- **Consistent**: All imports follow the same `@controld/*` pattern

## Scripts

- `pnpm dev` - Start development server with hot reload (tsx watch)
- `pnpm build` - Compile TypeScript to JavaScript and transform path aliases
- `pnpm start` - Run production server
- `pnpm lint` - Check code quality with ESLint
- `pnpm lint:fix` - Auto-fix ESLint issues
- `pnpm format` - Format code with Prettier
- `pnpm format:check` - Check code formatting
- `pnpm type:check` - Validate TypeScript types

## Configuration

### Environment Variables

- `PORT` - Server port (default: 3002)
- `NODE_ENV` - Environment mode (default: development)

### Example .env file

```bash
PORT=3002
NODE_ENV=development
```

## Development Workflow

### Adding New Routes

1. Create a new route plugin file in `src/routes/`
2. Define Zod schemas in `src/schema.ts`
3. Use Fastify's plugin pattern with type-safe schemas
4. Register the route in `src/routes/api.ts`

### Example Route Plugin

```typescript
import { FastifyPluginAsync } from 'fastify';
import { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';

const MyResponseSchema = z.object({
  message: z.string(),
});

const myRoute: FastifyPluginAsync = async (server) => {
  const fastify = server.withTypeProvider<ZodTypeProvider>();

  fastify.get(
    '/',
    {
      schema: {
        tags: ['MyTag'],
        summary: 'My endpoint',
        description: 'Description of my endpoint',
        response: {
          200: MyResponseSchema,
        },
      },
    },
    async () => {
      return { message: 'Hello' };
    },
  );
};

export default myRoute;
```

### Adding Request Validation

```typescript
import { FastifyPluginAsync } from 'fastify';
import { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';

const RequestBodySchema = z.object({
  name: z.string(),
  age: z.number(),
});

const ResponseSchema = z.object({
  message: z.string(),
});

const myRoute: FastifyPluginAsync = async (server) => {
  const fastify = server.withTypeProvider<ZodTypeProvider>();

  fastify.post(
    '/',
    {
      schema: {
        tags: ['Users'],
        body: RequestBodySchema,
        response: {
          200: ResponseSchema,
        },
      },
    },
    async (request) => {
      const { name, age } = request.body;
      return { message: `Hello ${name}, you are ${age} years old` };
    },
  );
};

export default myRoute;
```

## Code Quality

This project uses:

- **ESLint** for code linting
- **Prettier** for code formatting
- **TypeScript** strict mode for type safety

Run all checks before committing:

```bash
pnpm lint
pnpm format:check
pnpm type:check
```

## Architecture

### Fastify Features

- **Built-in Logging** - Pino logger integrated by default
- **Type Safety** - Full TypeScript support with Zod schemas
- **Plugin System** - Modular architecture using Fastify plugins
- **CORS** - Cross-origin resource sharing via @fastify/cors
- **Validation** - Automatic request/response validation with Zod
- **Performance** - One of the fastest Node.js web frameworks

### OpenAPI Integration

The service uses `fastify-type-provider-zod` and `@fastify/swagger` for:

- Automatic OpenAPI 3.1.0 schema generation from Zod schemas
- Runtime request/response validation
- TypeScript type inference from schemas
- Interactive Swagger UI documentation

### Error Handling

Fastify provides built-in error handling. Custom error handlers can be added:

```typescript
fastify.setErrorHandler((error, request, reply) => {
  fastify.log.error(error);
  reply.status(500).send({ error: 'Internal Server Error' });
});
```

## Logging

Fastify includes Pino logger by default. Access the logger in routes:

```typescript
fastify.get('/example', async (request, reply) => {
  request.log.info('Processing request');
  return { data: 'example' };
});
```

## Contributing

1. Create a new branch for your feature
2. Make changes following the existing code style
3. Run `pnpm lint:fix` and `pnpm format` before committing
4. Ensure all type checks pass with `pnpm type:check`
5. Test your changes with `pnpm dev`

## Related Services

- **API** (`p67/packages/api`) - Backend service (Fastify-based)
- **Web** (`p67/packages/web`) - React frontend application

## Resources

- [Fastify Documentation](https://fastify.dev/)
- [Fastify Type Provider Zod](https://github.com/turkerdev/fastify-type-provider-zod)
- [Fastify Swagger](https://github.com/fastify/fastify-swagger)
- [Zod Documentation](https://zod.dev/)
