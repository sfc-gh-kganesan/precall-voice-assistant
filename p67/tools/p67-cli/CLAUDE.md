---
description: P67 CLI Tool - Built with Commander.js and Bun
globs: "*.ts, *.tsx, *.html, *.css, *.js, *.jsx, package.json"
alwaysApply: false
---

# P67 CLI Tool

A command-line interface tool built with [Commander.js](https://github.com/tj/commander.js) and [Bun](https://bun.sh).

## Project Structure

```
p67-cli/
├── src/
│   ├── index.ts                # Main CLI entry point
│   ├── commands/               # Command modules
│   │   ├── init.ts            # Initialize configuration
│   │   ├── env.ts             # Environment/secrets management
│   │   └── workflow.ts        # Workflow operations
│   ├── config/                # Configuration management
│   │   └── ProjectConfig.ts   # Configuration class with Zod validation
│   └── secrets/               # Secret management utilities
│       └── 1password.ts       # 1Password integration helpers
├── package.json               # Project dependencies and scripts
├── tsconfig.json             # TypeScript configuration
└── CLAUDE.md                 # This file
```

## Technology Stack

- **Runtime**: Bun (fast JavaScript runtime)
- **CLI Framework**: Commander.js 12+ (complete solution for Node.js command-line interfaces)
- **Prompts**: @inquirer/prompts (interactive command-line user interfaces)
- **Validation**: Zod (TypeScript-first schema validation)
- **Language**: TypeScript 5+
- **Module System**: ESNext with bundler resolution

## Commander.js Library

Commander.js is the complete solution for Node.js command-line interfaces. It provides:

### Core Features
- **Command API**: Hierarchical command structure with subcommands
- **Options & Arguments**: Type-safe option parsing with validation
- **Help Generation**: Automatic help documentation
- **Version Management**: Built-in version handling
- **Action Handlers**: Async/sync command execution

### Main API

#### 1. Command API (`commander`)
The foundation of the CLI - handles command definition, parsing, and execution.

**Basic Structure**:
```typescript
import { Command } from 'commander';

const program = new Command();

program
  .name('my-cli')
  .version('1.0.0')
  .description('Description of what this CLI does')
  .option('-f, --flag', 'A boolean flag')
  .option('-v, --value <value>', 'An option with a value')
  .argument('<required>', 'Required argument')
  .argument('[optional]', 'Optional argument')
  .action((required, optional, options) => {
    // Command implementation
  });

program.parse(process.argv);
```

**Key Methods**:
- `.name(name)` - Set command name
- `.version(version)` - Set version (enables --version flag)
- `.description(desc)` - Set command description
- `.option(flags, description, defaultValue?)` - Add option/flag
- `.argument(usage, description)` - Define positional arguments
- `.action(handler)` - Set command handler function
- `.addCommand(command)` - Add subcommand
- `.parse(args)` - Parse and execute

**Creating Subcommands**:
```typescript
import { Command } from 'commander';

// Create subcommand
export const myCommand = new Command('mycommand')
  .description('My subcommand')
  .option('-f, --flag', 'A flag')
  .action((options) => {
    // Implementation
  });

// Add to main program
const program = new Command();
program.addCommand(myCommand);
```

#### 2. Inquirer Prompts (`@inquirer/prompts`)
Interactive prompts for user input.

**Available Prompts**:
```typescript
import { input, select, confirm, checkbox, number } from '@inquirer/prompts';

// Text input
const name = await input({ message: 'Enter name' });

// Selection from list
const choice = await select({
  message: 'Choose option',
  choices: [
    { name: 'Option 1', value: 'opt1' },
    { name: 'Option 2', value: 'opt2' },
  ],
});

// Yes/no confirmation
const confirmed = await confirm({ message: 'Continue?' });

// Number input
const count = await number({ message: 'How many?' });

// Multiple selection
const selected = await checkbox({
  message: 'Select items',
  choices: [
    { name: 'Item 1', value: 'item1' },
    { name: 'Item 2', value: 'item2' },
    { name: 'Item 3', value: 'item3' },
  ],
});
```

## CLI Commands

### Main Command
```bash
bun src/index.ts [command] [options]
```

Shows help when run without arguments.

### Init Command
Initialize a new p67 configuration file.

```bash
# Basic usage
bun src/index.ts init

# With custom directory
bun src/index.ts --cwd /path/to/project init
```

**Implementation**: `src/commands/init.ts`

### Env Command
Print environment configuration for debugging.

```bash
# Show environment
bun src/index.ts env
```

**Implementation**: `src/commands/env.ts`

### Workflow Command
Operate on workflows (placeholder).

```bash
# Run workflow command
bun src/index.ts workflow
```

**Implementation**: `src/commands/workflow.ts`

## Development

### Running the CLI

**Direct execution**:
```bash
bun src/index.ts [command]
```

**Using npm scripts**:
```bash
# Run once
bun run start [command]

# Run tests
bun test
```

### Project Setup

Use Bun instead of Node.js for all operations:

- **Install dependencies**: `pnpm install` (per project conventions)
- **Run CLI**: `bun src/index.ts`
- **Build binary**: `bun run build`
- **Run tests**: `bun test`

### Adding New Commands

1. **Create command file** in `src/commands/`:

```typescript
// src/commands/mycommand.ts
import { Command } from 'commander';

export const myCommand = new Command('mycommand')
  .description('My new command')
  .option('-f, --flag', 'A flag option')
  .action((options) => {
    console.log('Command executed!', options);
  });
```

2. **Register in main CLI** (`src/index.ts`):

```typescript
import { myCommand } from './commands/mycommand.ts';

const program = new Command();

program
  .name('p67')
  // ... existing config
  .addCommand(myCommand);

program.parse(process.argv);
```

### Command Patterns

#### Simple Command
```typescript
export const simpleCommand = new Command('simple')
  .description('A simple command')
  .action(() => {
    console.log('Executed!');
  });
```

#### Command with Options
```typescript
export const optionsCommand = new Command('options')
  .description('Command with options')
  .option('-v, --verbose', 'Enable verbose output')
  .option('-o, --output <path>', 'Output file path')
  .action((options) => {
    if (options.verbose) {
      console.log('Verbose mode enabled');
    }
    console.log('Output:', options.output);
  });
```

#### Command with Arguments
```typescript
export const argsCommand = new Command('args')
  .description('Command with arguments')
  .argument('<input>', 'Input file')
  .argument('[output]', 'Output file (optional)')
  .action((input, output) => {
    console.log('Input:', input);
    console.log('Output:', output || 'default.txt');
  });
```

#### Command with Subcommands
```typescript
import { Command } from 'commander';

const sub1 = new Command('sub1')
  .description('Subcommand 1')
  .action(() => console.log('Sub 1'));

const sub2 = new Command('sub2')
  .description('Subcommand 2')
  .action(() => console.log('Sub 2'));

export const parentCommand = new Command('parent')
  .description('Parent command')
  .addCommand(sub1)
  .addCommand(sub2);
```

#### Interactive Command
```typescript
import { Command } from 'commander';
import { input, confirm } from '@inquirer/prompts';

export const interactiveCommand = new Command('interactive')
  .description('Interactive command')
  .action(async () => {
    const name = await input({ message: 'Your name' });
    const confirmed = await confirm({ 
      message: `Confirm name is ${name}?` 
    });
    
    if (confirmed) {
      console.log(`Welcome, ${name}!`);
    }
  });
```

#### Command with Global Options
```typescript
const program = new Command();

program
  .name('p67')
  .version('0.1.0')
  .option('--cwd <path>', 'Target project directory', process.cwd());

// Access global options in subcommands
export const myCommand = new Command('mycommand')
  .action(() => {
    const options = myCommand.optsWithGlobals();
    console.log('Working directory:', options.cwd);
  });
```

## Code Style

Follow the standard Bun/TypeScript conventions:

- **Semicolons**: Required (enforced by prettier)
- **Quotes**: Single quotes for strings
- **Trailing commas**: Always use in multi-line structures
- **Indentation**: 2 spaces
- **Imports**: Use `.ts` extensions in import paths
- **Async**: Use `async/await` syntax for asynchronous operations

## Testing

Create test files alongside your commands:

```typescript
// src/commands/init.test.ts
import { test, expect } from 'bun:test';
import { initCommand } from './init.ts';

test('init command exists', () => {
  expect(initCommand).toBeDefined();
});
```

Run tests:
```bash
bun test
```

## Bun Runtime

This project uses Bun as specified in the root CLAUDE.md:

- Use `bun <file>` instead of `node <file>` or `ts-node <file>`
- Use `bun test` instead of `jest` or `vitest`
- Use `bun build <file.html|file.ts|file.css>` instead of `webpack` or `esbuild`
- Use `pnpm install` instead of `npm install` or `yarn install` or `bun install`
- Use `bun run <script>` instead of `npm run <script>` or `yarn run <script>` or `pnpm run <script>`
- Use `bunx <package> <command>` instead of `npx <package> <command>`
- Bun automatically loads .env, so don't use dotenv.

## Resources

- **Commander.js Documentation**: https://github.com/tj/commander.js
- **Inquirer Prompts Documentation**: https://github.com/SBoudrias/Inquirer.js
- **Bun Documentation**: https://bun.sh/docs
- **TypeScript**: https://www.typescriptlang.org/
- **Zod Documentation**: https://zod.dev

## Common Commander.js Patterns

### Type-Safe Options with Parsing
```typescript
export const myCommand = new Command('mycommand')
  .option('-p, --port <number>', 'Port number', '3000')
  .option('-h, --host <string>', 'Host address', 'localhost')
  .option('-e, --env <env>', 'Environment (dev|staging|prod)', 'dev')
  .action((options) => {
    const port = parseInt(options.port);
    if (!['dev', 'staging', 'prod'].includes(options.env)) {
      console.error('Invalid environment');
      process.exit(1);
    }
  });
```

### Required Options
```typescript
export const myCommand = new Command('mycommand')
  .requiredOption('-u, --user <name>', 'User name')
  .action((options) => {
    console.log('User:', options.user);
  });
```

### Variadic Arguments
```typescript
export const myCommand = new Command('mycommand')
  .argument('<files...>', 'One or more files')
  .action((files) => {
    files.forEach(file => console.log(file));
  });
```

### Command Aliases
```typescript
export const listCommand = new Command('list')
  .alias('ls')  // Can be called with either 'list' or 'ls'
  .description('List items')
  .action(() => {
    console.log('Listing...');
  });
```

### Help Customization
```typescript
export const myCommand = new Command('mycommand')
  .description('My command description')
  .addHelpText('after', `
Examples:
  $ p67 mycommand --flag
  $ p67 mycommand --value something
  `);
```

### Access Parent Options
```typescript
// In a subcommand, access parent options
export const subCommand = new Command('sub')
  .action(() => {
    const options = subCommand.optsWithGlobals();
    console.log('Global CWD:', options.cwd);
  });
```

For more information, read the Bun API docs in `node_modules/bun-types/docs/**.mdx`.
