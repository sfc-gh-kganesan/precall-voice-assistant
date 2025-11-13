# Theme System Guide

## Overview

The application supports multiple visual themes that can be switched via command line.

## Available Themes

1. **gfinance** - Google Finance (Default): Dark header, Google Blue, Roboto font
2. **hackernews** - Hacker News: Orange header, beige background, Verdana font
3. **snowflake** - Snowflake: Dark mode, Snowflake Blue, Inter font
4. **anthropic** - Anthropic: Warm cream background, coral accent, system fonts

## Usage

```bash
npm run theme gfinance
npm run theme hackernews
npm run theme snowflake
npm run theme anthropic
```

Then restart your dev server.

## Files

- `frontend/app/themes/` - Theme CSS files
- `frontend/app/themes/active-theme.css` - Currently active (auto-generated)
- `frontend/app/design-system.css` - Imports active theme

## Creating Themes

Copy a theme file, modify CSS variables, add to `theme-config.js`, then use it!
