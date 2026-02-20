# P67 New Feature

Guide for adding end-to-end features to the P67 platform. Features typically touch multiple layers.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (p67-cli)                           │
│                    tools/p67-cli/src/commands/                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API (controld)                             │
│              services/controld/src/routes/                      │
│              services/controld/src/schema.ts                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database (Prisma)                          │
│              packages/db/prisma/schema.prisma                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      SDK (TS + Python)                          │
│              packages/workflow-sdk/src/index.ts                 │
│              packages/workflow-sdk-python/p67_sdk/sdk.py        │
│              services/controld/src/lib/sdk-impl.ts              │
└─────────────────────────────────────────────────────────────────┘
```

## Key Files by Layer

| Layer | Path | Purpose |
|-------|------|---------|
| Database | `packages/db/prisma/schema.prisma` | Data models |
| API Schema | `services/controld/src/schema.ts` | Zod request/response schemas |
| Routes | `services/controld/src/routes/` | API endpoints |
| Services | `services/controld/src/services/` | Business logic |
| CLI | `tools/p67-cli/src/commands/` | CLI commands |
| CLI Client | `tools/p67-cli/src/clients/ControldClient.ts` | API client |
| SDK (TS) | `packages/workflow-sdk/src/index.ts` | TypeScript SDK |
| SDK (Python) | `packages/workflow-sdk-python/p67_sdk/sdk.py` | Python SDK |
| SDK Impl | `services/controld/src/lib/sdk-impl.ts` | SDK implementation |

## Workflow: Adding a New Feature

### Step 1: Database Schema (if needed)

Edit `packages/db/prisma/schema.prisma`:

```prisma
model YourModel {
    id          String   @id @default(uuid())
    createdAt   DateTime @default(now())
    updatedAt   DateTime @updatedAt
    // your fields
    
    // Relations
    userId      String
    user        User     @relation(fields: [userId], references: [id])
    
    @@index([userId])
}
```

Then regenerate the client:

```bash
cd packages/db && pnpm prisma generate
```

For schema changes in production:

```bash
cd packages/db && pnpm prisma migrate dev --name your_migration_name
```

### Step 2: API Schema

Add Zod schemas in `services/controld/src/schema.ts`:

```typescript
// Request params (URL parameters)
export const YourFeatureParamsSchema = z.object({
    id: z.string().uuid(),
});
export type YourFeatureParams = z.infer<typeof YourFeatureParamsSchema>;

// Request body
export const YourFeatureBodySchema = z.object({
    name: z.string(),
    enabled: z.boolean().optional().default(true),
});
export type YourFeatureBody = z.infer<typeof YourFeatureBodySchema>;

// Response
export const YourFeatureResponseSchema = z.object({
    id: z.string(),
    name: z.string(),
    createdAt: z.string(),
});
export type YourFeatureResponse = z.infer<typeof YourFeatureResponseSchema>;
```

### Step 3: API Route

Create route file `services/controld/src/routes/yourfeature/create.ts`:

```typescript
import {
    ErrorResponseSchema,
    YourFeatureBodySchema,
    YourFeatureResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerYourFeatureCreateRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.post(
        '/yourfeature',
        {
            schema: {
                description: 'Create a new feature',
                tags: ['YourFeature'],
                body: YourFeatureBodySchema,
                response: {
                    200: YourFeatureResponseSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const body = request.body;
                const userId = request.user.id;

                const result = await fastify.db.yourModel.create({
                    data: {
                        ...body,
                        userId,
                    },
                });

                return reply.code(200).send({
                    id: result.id,
                    name: result.name,
                    createdAt: result.createdAt.toISOString(),
                });
            } catch (error) {
                return reply.code(500).send({
                    error: 'Internal server error',
                    message: error instanceof Error ? error.message : 'Unknown error',
                });
            }
        },
    );
}
```

Create index file `services/controld/src/routes/yourfeature/index.ts`:

```typescript
import type { FastifyInstance } from 'fastify';
import { registerYourFeatureCreateRoute } from './create.js';
import { registerYourFeatureListRoute } from './list.js';

export function registerYourFeatureRoutes(server: FastifyInstance) {
    registerYourFeatureCreateRoute(server);
    registerYourFeatureListRoute(server);
}
```

Register in `services/controld/src/routes/api.ts`:

```typescript
import { registerYourFeatureRoutes } from './yourfeature/index.js';

// In the function:
registerYourFeatureRoutes(server);
```

### Step 4: CLI Client Method

Add to `tools/p67-cli/src/clients/ControldClient.ts`:

```typescript
async createYourFeature(body: { name: string; enabled?: boolean }) {
    return this.request<YourFeatureResponse>('/yourfeature', {
        method: 'POST',
        body: JSON.stringify(body),
    });
}

async listYourFeatures() {
    return this.request<YourFeatureResponse[]>('/yourfeature');
}
```

### Step 5: CLI Command

Create `tools/p67-cli/src/commands/yourfeature/index.ts`:

```typescript
import { Command } from 'commander';

export const yourfeatureCommand = new Command('yourfeature')
    .description('Manage your features');
```

Create `tools/p67-cli/src/commands/yourfeature/create.ts`:

```typescript
import { Command } from 'commander';
import type { CLIContext } from '../../context.js';

export function createYourFeatureCreateCommand(ctx: CLIContext) {
    return new Command('create')
        .description('Create a new feature')
        .argument('<name>', 'Feature name')
        .option('--disabled', 'Create in disabled state')
        .action(async (name: string, options: { disabled?: boolean }) => {
            const client = ctx.getControldClient();
            
            const result = await client.createYourFeature({
                name,
                enabled: !options.disabled,
            });

            console.log(`Created feature: ${result.id}`);
        });
}
```

Register in `tools/p67-cli/src/program.ts`:

```typescript
import { yourfeatureCommand } from './commands/yourfeature/index.js';
import { createYourFeatureCreateCommand } from './commands/yourfeature/create.js';

// In setup:
yourfeatureCommand.addCommand(createYourFeatureCreateCommand(ctx));
program.addCommand(yourfeatureCommand);
```

### Step 6: SDK (if workflow-callable)

See `SKILL_sdk_sync.md` for detailed SDK sync workflow.

Quick summary:
1. Add interface method to `packages/workflow-sdk/src/index.ts`
2. Implement in `services/controld/src/lib/sdk-impl.ts`
3. Add Python equivalent in `packages/workflow-sdk-python/p67_sdk/sdk.py`

## Feature Checklist

### Database Layer
- [ ] Model added to `schema.prisma`
- [ ] Appropriate indexes defined
- [ ] Relations configured
- [ ] Migration created and applied
- [ ] Prisma client regenerated

### API Layer
- [ ] Zod schemas defined in `schema.ts`
- [ ] Route files created in `routes/yourfeature/`
- [ ] Routes registered in `api.ts`
- [ ] Error handling consistent with other routes
- [ ] Auth/RBAC applied (`request.user.id`)

### CLI Layer
- [ ] Client method added to `ControldClient.ts`
- [ ] Command files created in `commands/yourfeature/`
- [ ] Commands registered in `program.ts`
- [ ] Help text and descriptions added
- [ ] Options use consistent patterns

### SDK Layer (if applicable)
- [ ] TypeScript interface updated
- [ ] TypeScript implementation added
- [ ] Python SDK updated
- [ ] Types added to both languages
- [ ] Docstrings match

### Testing
- [ ] API routes tested manually or via tests
- [ ] CLI commands tested
- [ ] SDK methods tested in sample workflow

## Common Patterns

### Authentication
All routes have access to the authenticated user:
```typescript
const userId = request.user.id;
```

### Error Responses
Use consistent error format:
```typescript
return reply.code(400).send({
    error: 'Invalid request',
    message: 'Specific error message',
});
```

### Database Queries with RBAC
Always filter by user for user-owned resources:
```typescript
const items = await fastify.db.yourModel.findMany({
    where: { userId: request.user.id },
});
```

### CLI Output
Use consistent output patterns:
```typescript
// Success
console.log(`Created: ${result.id}`);

// Lists (consider table format)
for (const item of items) {
    console.log(`${item.id}\t${item.name}`);
}

// Errors
console.error(`Error: ${error.message}`);
process.exit(1);
```

## Quick Commands

```bash
# Regenerate Prisma client after schema changes
cd packages/db && pnpm prisma generate

# Create migration
cd packages/db && pnpm prisma migrate dev --name add_your_feature

# Build CLI
cd tools/p67-cli && pnpm build

# Build controld
cd services/controld && pnpm build

# Run controld locally
cd services/controld && pnpm dev

# Test CLI locally
cd tools/p67-cli && pnpm dev yourfeature create "test"
```

## Related Skills

- `SKILL_sdk_sync.md` - For SDK parity between TypeScript and Python
