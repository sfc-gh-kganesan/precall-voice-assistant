# Legacy Files

This directory contains old/unused versions of the chat widget that have been replaced by the TypeScript/React implementation in `../src/`.

## Files

- **chat-widget.js** (14KB) - Original vanilla JavaScript implementation
- **chat-widget-v2.js** (30KB) - Second version with voice support (vanilla JS)
- **chat-widget.css** (11KB) - Old stylesheet (replaced by `../src/styles/widget.css`)
- **wavtools.min.js** (21KB) - Standalone wavtools library (now imported from npm package)

## Current Implementation

The active widget is built from:
- **Source**: `../src/` (TypeScript + React components)
- **Built to**: `../dist/chat-widget.iife.js` + `../dist/style.css`
- **Used by**: `../../demos/snowflake.html`

These legacy files are kept for reference but are **not used** by the current implementation.
