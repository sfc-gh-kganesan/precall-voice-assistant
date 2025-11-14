#!/usr/bin/env node

/**
 * Theme Switcher Script
 *
 * Usage:
 *   npm run theme gfinance
 *   npm run theme hackernews
 *   npm run theme snowflake
 */

/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs');
const path = require('path');

const themeConfig = require('./theme-config.js');

const THEMES_DIR = __dirname;
const ACTIVE_THEME_FILE = path.join(THEMES_DIR, 'active-theme.css');

// Get theme from command line argument or environment variable
const requestedTheme = process.argv[2] || process.env.THEME || themeConfig.defaultTheme;

if (!themeConfig.themes[requestedTheme]) {
    console.error(`❌ Error: Theme '${requestedTheme}' not found.`);
    console.log('\n🎨 Available themes:');
    Object.keys(themeConfig.themes).forEach((key) => {
        const theme = themeConfig.themes[key];
        console.log(`  - ${key}: ${theme.name}`);
        console.log(`    ${theme.description}`);
    });
    process.exit(1);
}

const theme = themeConfig.themes[requestedTheme];
const themeFilePath = path.join(THEMES_DIR, theme.file);

if (!fs.existsSync(themeFilePath)) {
    console.error(`❌ Error: Theme file '${theme.file}' not found.`);
    process.exit(1);
}

// Copy theme file to active-theme.css
try {
    const themeContent = fs.readFileSync(themeFilePath, 'utf8');
    fs.writeFileSync(ACTIVE_THEME_FILE, themeContent);

    console.log(`✅ Successfully activated theme: ${theme.name}`);
    console.log(`   ${theme.description}`);
    console.log('\n🎨 Features:');
    theme.features.forEach((feature) => {
        console.log(`   • ${feature}`);
    });
    console.log('\n🔄 Restart your development server to see changes.');
} catch (error) {
    console.error(`❌ Error switching theme: ${error.message}`);
    process.exit(1);
}
