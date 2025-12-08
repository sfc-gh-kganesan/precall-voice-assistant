# TypeScript LangGraph Project

A TypeScript project demonstrating a simple LangGraph implementation with esbuild bundling.

## Overview

This project showcases a basic LangGraph workflow with three sequential nodes, built with TypeScript and bundled using esbuild for optimal performance.

## Project Structure

```
tslang/
├── package.json          # Project configuration
├── tsconfig.json         # TypeScript configuration
├── build.js             # esbuild bundling script
├── src/
│   └── index.ts         # LangGraph implementation
└── dist/                # Build output (generated)
    ├── index.js         # Bundled output
    └── index.js.map     # Source map
```

## Prerequisites

- Node.js (v20 or higher recommended)
- npm

## Installation

Install the project dependencies:

```bash
npm install
```

## Usage

### Build the Project

Bundle the TypeScript code into a single JavaScript file:

```bash
npm run build
```

This will create the bundled output in the `dist` directory.

### Run the Application

After building, execute the bundled code:

```bash
node dist/index.js
```

## LangGraph Implementation

The project includes a simple graph with three nodes:

1. **Node 1 (Initialize)**: Starting point of the workflow
2. **Node 2 (Process)**: Middle processing step
3. **Node 3 (Finalize)**: Final step before completion

The nodes execute sequentially, with each node adding a message to the state and updating the current node tracker.

## Dependencies

### Runtime Dependencies
- `@langchain/core`: Core LangChain functionality
- `@langchain/langgraph`: Graph-based workflow orchestration

### Development Dependencies
- `typescript`: TypeScript compiler
- `esbuild`: Fast JavaScript bundler
- `@types/node`: Node.js type definitions

## Build Configuration

The project uses esbuild for bundling with the following configuration:
- Target: Node.js 20
- Format: ESM (ES Modules)
- Output: Single bundled file with source maps
- External packages: Node modules are bundled with output

