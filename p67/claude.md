# P67 Project - Claude Code Instructions

This document provides guidance for Claude Code when working with the P67 monorepo project.

## Project Overview

P67 is a modern full-stack TypeScript monorepo containing:
- **@p67/api**: Fastify-based backend API service
- **@p67/web**: React-based frontend application

## Technology Stack

### Backend (@p67/api)
- **Runtime**: Node.js with ESM modules
- **Framework**: Fastify 5.2.0 (fast, low-overhead web framework)
- **Language**: TypeScript 5.9.3 targeting ES2022
- **Dev Tools**: tsx for development with watch mode
- **CORS**: @fastify/cors for cross-origin requests
- **Server**: Runs on port 3001 (configurable via PORT env var)

### Frontend (@p67/web)
- **Framework**: React 19.2.0 (latest version)
- **Build Tool**: Vite 7.2.2 (next-generation frontend tooling)
- **Language**: TypeScript 5.9.3
- **UI Library**: Mantine UI (component library)
- **Styling**: PostCSS with postcss-preset-mantine
- **Dev Server**: Runs on port 5173
- **Plugins**: @vitejs/plugin-react for Fast Refresh and JSX

### Development Tools
- **Package Manager**: pnpm 10.22.0 (workspace-enabled)
- **Linting**: ESLint 9 with TypeScript support (typescript-eslint)
- **Formatting**: Prettier 3.3.0
- **Type Checking**: TypeScript strict mode enabled across all packages
- **Version Control**: Git

## Project Structure

```
p67/
├── packages/
│   ├── api/                    # Backend service
│   │   ├── src/
│   │   │   └── index.ts        # Main Fastify server
│   │   ├── dist/               # Compiled output
│   │   ├── eslint.config.js    # ESLint configuration
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── web/                    # Frontend application
│       ├── src/
│       │   ├── main.tsx        # React entry point
│       │   ├── App.tsx         # Main component
│       │   ├── App.css
│       │   └── index.css
│       ├── public/             # Static assets
│       ├── index.html
│       ├── eslint.config.js    # ESLint configuration
│       ├── vite.config.ts
│       ├── package.json
│       └── tsconfig*.json
├── .prettierrc                 # Prettier configuration
├── .prettierignore             # Prettier ignore patterns
├── package.json                # Root workspace config
├── pnpm-workspace.yaml         # Workspace definition
└── pnpm-lock.yaml              # Dependency lock file
```

## UI Component Library

### Mantine UI

The project uses Mantine v8 as the UI component library. Please refer to the documentation here: https://mantine.dev/llms.txt for full usage information. Mantine provides a comprehensive set of accessible, customizable React components.

#### Setup
- **Provider**: MantineProvider wraps the app in `main.tsx`
- **Styles**: `@mantine/core/styles.css` imported at the top of `main.tsx`
- **PostCSS**: Configured via `postcss.config.cjs` with `postcss-preset-mantine`

#### Available Packages
- `@mantine/core` - Core components (Button, TextInput, Select, Modal, etc.)
- `@mantine/hooks` - Utility hooks (useMediaQuery, useClickOutside, etc.)

#### Usage Example
```typescript
import { Button, TextInput, Stack, Paper } from '@mantine/core';

function MyComponent() {
  return (
    <Paper p="md" shadow="sm">
      <Stack gap="md">
        <TextInput label="Name" placeholder="Enter your name" />
        <Button variant="filled" color="blue">
          Submit
        </Button>
      </Stack>
    </Paper>
  );
}
```

#### Best Practices
- Import only the components you need
- Use Mantine's spacing system (`p`, `m`, `gap` props) for consistency
- Leverage Mantine hooks for common functionality
- Use Mantine's color system for theming
- Refer to [Mantine documentation](https://mantine.dev) for component APIs

## Code Style Guidelines

### TypeScript Style
- **Always use semicolons**: All statements must end with semicolons
- **Quote style**: Use single quotes for strings
- **Trailing commas**: Always include trailing commas in multi-line structures
- **Arrow functions**: Always use parentheses around parameters
- **Indentation**: 2 spaces (no tabs)
- **Line width**: Maximum 100 characters
- **Import organization**: Imports are automatically sorted alphabetically

### Example:
```typescript
import cors from '@fastify/cors';
import Fastify from 'fastify';

const fastify = Fastify({
  logger: true,
});

await fastify.register(cors, {
  origin: true,
});

const start = async () => {
  try {
    const port = Number.parseInt(process.env.PORT) || 3001;
    await fastify.listen({ port, host: '0.0.0.0' });
    console.log(`Server listening on port ${port}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
```

### React/JSX Style
- **Component naming**: Use PascalCase for components
- **Props**: Use TypeScript interfaces for prop types
- **Hooks**: Follow React hooks rules and conventions
- **Button elements**: Always specify explicit `type` attribute
- **External links**: Use `rel="noreferrer"` with `target="_blank"`
- **Null assertions**: Avoid using non-null assertions (`!`), prefer proper null checks

## Available Scripts

### Root Level
- `pnpm dev` - Run both API and web in parallel
- `pnpm dev:api` - Run API service only
- `pnpm dev:web` - Run web app only
- `pnpm build` - Build all packages
- `pnpm build:api` - Build API package
- `pnpm build:web` - Build web package
- `pnpm lint` - Lint all packages
- `pnpm lint:fix` - Auto-fix linting issues across all packages
- `pnpm format` - Format code across all packages
- `pnpm format:check` - Check if any code is not formatted correctly
- `pnpm type:check` - Type-check all packages

### API Package (`packages/api/`)
- `pnpm dev` - Start dev server with hot reload (tsx watch)
- `pnpm build` - Compile TypeScript to JavaScript
- `pnpm start` - Run production build
- `pnpm lint` - Check code quality
- `pnpm lint:fix` - Auto-fix issues
- `pnpm format` - Format code
- `pnpm format:check` - Check if any code is not formatted correctly
- `pnpm type:check` - Validate TypeScript

### Web Package (`packages/web/`)
- `pnpm dev` - Start Vite dev server
- `pnpm build` - Build for production
- `pnpm preview` - Preview production build
- `pnpm lint` - Check code quality
- `pnpm lint:fix` - Auto-fix issues
- `pnpm format` - Format code
- `pnpm format:check` - Check if any code is not formatted correctly
- `pnpm type:check` - Validate TypeScript

## Development Workflow

### Starting Development
1. Install dependencies: `pnpm install`
2. Start both services: `pnpm dev`
   - API will run on http://localhost:3001
   - Web will run on http://localhost:5173

### Code Quality Workflow
1. Before committing, run: `pnpm lint:fix` to auto-fix ESLint issues
2. Run `pnpm format` to ensure consistent Prettier formatting
3. Run `pnpm type:check` to validate TypeScript
4. ESLint will check code quality and TypeScript-specific rules
5. Prettier will format code according to the project style

### Adding New Features
1. Determine which package(s) need changes
2. Make changes following the code style guidelines
3. Run `pnpm lint:fix` in the affected package
4. Test locally with `pnpm dev`
5. Run `pnpm build` to ensure production build works
6. Commit changes

## API Endpoints

Current API endpoints (all prefixed with `/api/`):
- `GET /api/health` - Health check endpoint
  - Returns: `{ status: 'ok', timestamp: ISO8601 }`
- `GET /api/hello` - Sample greeting endpoint
  - Returns: `{ message: 'Hello from Fastify!' }`

## ESLint and Prettier Configuration

The project uses ESLint for linting and Prettier for formatting.

### ESLint Configuration

Each package has its own `eslint.config.js` using the new flat config format.

**Web Package (@p67/web):**
- Extends recommended configs from ESLint and TypeScript ESLint
- React-specific plugins: `react`, `react-hooks`, `react-refresh`
- Browser globals enabled
- JSX support enabled
- React hooks rules enforced

**API Package (@p67/api):**
- Extends recommended configs from ESLint and TypeScript ESLint
- Node.js globals enabled
- Relaxed rules for backend development
- Allows unused parameters with `_` prefix

### Prettier Configuration (`.prettierrc`)

Shared configuration at the root level:
- **Semicolons**: Always required
- **Quotes**: Single quotes
- **Trailing commas**: All (arrays, objects, parameters)
- **Arrow parens**: Always use parentheses
- **Tab width**: 2 spaces
- **Print width**: 100 characters
- **Use tabs**: false (spaces only)

### Ignored Patterns (`.prettierignore`)
- `node_modules/`
- `dist/`, `build/`, `.next/`
- `coverage/`
- Lock files (`pnpm-lock.yaml`, `package-lock.json`)
- Minified files (`*.min.js`, `*.min.css`)

## TypeScript Configuration

### Compiler Options (Shared)
- Target: ES2022
- Module: ESNext
- Strict mode: enabled
- Module resolution: bundler (web) / node (api)
- Source maps: enabled
- Declaration maps: enabled (api)

### Type Safety
- Strict null checks enabled
- No implicit any
- Unused locals/parameters checked
- No fallthrough cases in switch statements

## Best Practices for Claude Code

### When Making Changes
1. **Always run formatting after changes**: Use `pnpm lint:fix` and `pnpm format`
2. **Maintain semicolons**: Ensure all statements end with semicolons (enforced by Prettier)
3. **Run ESLint**: Check for code quality issues with `pnpm lint`
4. **Type safety**: Avoid `any` types, use proper TypeScript types (enforced by ESLint)
5. **Test locally**: Run `pnpm dev` to verify changes work
6. **Format before committing**: Run `pnpm format` to ensure consistent code style

### Code Organization
- Keep API routes organized in logical groups
- Follow React component best practices
- Use async/await for asynchronous operations
- Prefer functional components and hooks in React
- Use proper error handling with try/catch

### Monorepo Considerations
- Changes to shared types should be reflected in both packages
- When adding dependencies, add to the specific package, not root
- Use `pnpm --filter @p67/api` or `pnpm --filter @p67/web` for package-specific commands
- Root scripts run across all packages with `-r` flag

## Common Tasks

### Adding a New API Endpoint
1. Edit `packages/api/src/index.ts`
2. Add route with proper TypeScript types
3. Test with `pnpm --filter @p67/api dev`
4. Run `pnpm lint:fix` to format

### Adding a New React Component
1. Create component file in `packages/web/src/`
2. Use TypeScript and proper prop types
3. Import and use in App.tsx or other components
4. Test with `pnpm --filter @p67/web dev`
5. Run `pnpm lint:fix` to format

### Adding a Dependency
```bash
# Add to API package
pnpm --filter @p67/api add <package-name>

# Add to Web package
pnpm --filter @p67/web add <package-name>

# Add as dev dependency
pnpm --filter @p67/api add -D <package-name>
```

### Updating Dependencies
```bash
# Update all dependencies
pnpm up -r

# Update specific package
pnpm up <package-name>
```

## Debugging

### API Debugging
- Fastify logger is enabled by default
- Check console output for request logs
- Use `console.log` for debugging (will appear in terminal)

### Web Debugging
- Use browser DevTools
- Vite provides HMR (Hot Module Replacement)
- React DevTools extension recommended

## Environment Variables

### API
- `PORT`: Server port (default: 3001)
- `NODE_ENV`: Environment (development/production)

### Web
- Vite environment variables should be prefixed with `VITE_`
- See Vite documentation for more details

## Git Integration

ESLint and Prettier work well with Git:
- Use `.gitignore` to exclude generated files
- ESLint respects ignore patterns in `eslint.config.js`
- Prettier respects patterns in `.prettierignore`
- Consider using git hooks (husky) for pre-commit linting/formatting

## Important Notes

1. **Module System**: Both packages use ESM (`"type": "module"`)
2. **Node Version**: Ensure compatible Node.js version (18+)
3. **Package Manager**: Must use pnpm, not npm or yarn
4. **Port Conflicts**: Ensure ports 3001 and 5173 are available
5. **Semicolons**: Always include semicolons in TypeScript/JavaScript code

## Resources

- Fastify Documentation: https://fastify.dev
- React Documentation: https://react.dev
- Vite Documentation: https://vite.dev
- Mantine UI Documentation: https://mantine.dev
- ESLint Documentation: https://eslint.org
- TypeScript ESLint: https://typescript-eslint.io
- Prettier Documentation: https://prettier.io
- TypeScript Documentation: https://www.typescriptlang.org
- pnpm Documentation: https://pnpm.io
