# Theme System for Docker

## Quick Start

### Method 1: Using Helper Script (Easiest)

```bash
# Build and run with Google Finance theme (default)
./run-with-theme.sh gfinance

# Build and run with Hacker News theme
./run-with-theme.sh hackernews

# Build and run with Snowflake theme
./run-with-theme.sh snowflake
```

### Method 2: Using Environment Variable

```bash
# Set theme and build
THEME=gfinance docker compose up --build

# Or with different theme
THEME=hackernews docker compose up --build
THEME=snowflake docker compose up --build
```

### Method 3: Using .env File

Create a `.env` file (or `.env.theme`):
```
THEME=gfinance
```

Then build normally:
```bash
docker compose up --build
```

## Available Themes

- `gfinance` - Google Finance (default): Dark header, Google Blue, Roboto font
- `hackernews` - Hacker News: Orange header, beige background, Verdana font
- `snowflake` - Snowflake: Dark mode, Snowflake Blue, Inter font

## How It Works

1. The `THEME` environment variable is read by docker-compose.yml
2. It's passed as a build argument to the Dockerfile
3. During build, `npm run theme ${THEME}` sets the active theme
4. The theme is baked into the Docker image

## Changing Themes

Since the theme is baked into the Docker image during build, you need to **rebuild** when changing themes:

```bash
# Change theme
THEME=hackernews docker compose up --build

# Or use the helper script
./run-with-theme.sh hackernews
```

## Tips

- **Default theme**: If you don't specify THEME, it defaults to `gfinance`
- **Rebuild required**: Theme changes require `--build` flag
- **Persistent setting**: Use `.env` file to avoid typing THEME every time

## Examples

```bash
# Quick test of all themes
./run-with-theme.sh gfinance     # Google Finance
# Ctrl+C, then:
./run-with-theme.sh hackernews   # Hacker News
# Ctrl+C, then:
./run-with-theme.sh snowflake    # Snowflake

# Set default theme for your project
echo "THEME=snowflake" > .env
docker compose up --build
```

## Troubleshooting

**Theme not changing?**
- Make sure you used `--build` flag
- Check that THEME environment variable is set correctly
- Verify the theme name is correct (gfinance, hackernews, or snowflake)

**Want to change theme without rebuilding?**
- Not possible - themes are baked into the Docker image
- For development without Docker, use: `npm run theme <name>` in frontend/
