/**
 * Theme Configuration
 *
 * This file defines available themes and their metadata.
 * To switch themes, use the theme switcher script or set THEME environment variable.
 */

module.exports = {
  // Default theme (used if no theme is specified)
  defaultTheme: 'snowflake',

  // Available themes
  themes: {
    gfinance: {
      name: 'Google Finance',
      description: 'Professional, clean design inspired by Google Finance',
      file: 'gfinance.css',
      features: [
        'Dark header with Material Design shadows',
        'Google Blue (#1a73e8) primary color',
        'Roboto font family',
        'White backgrounds with subtle shadows',
      ],
      font: 'Roboto',
      fontWeights: ['400', '500', '700'],
    },
    hackernews: {
      name: 'Hacker News',
      description: 'Minimal, classic design inspired by Hacker News',
      file: 'hackernews.css',
      features: [
        'Orange header bar (#ff6600)',
        'Beige background (#f6f6ef)',
        'Verdana font family',
        'Simple, flat design with minimal shadows',
      ],
      font: 'Verdana',
      fontWeights: [],
    },
    snowflake: {
      name: 'Snowflake',
      description: 'Modern, professional design with Snowflake branding',
      file: 'snowflake.css',
      features: [
        'Dark backgrounds with depth',
        'Snowflake Blue (#29B5E8) primary color',
        'Inter font family',
        'Modern rounded corners and shadows',
      ],
      font: 'Inter',
      fontWeights: [],
    },
    anthropic: {
      name: 'Anthropic',
      description: 'Clean, minimal design inspired by Anthropic\'s brand',
      file: 'anthropic.css',
      features: [
        'Warm cream background (#F7F5F2)',
        'Anthropic coral accent (#CC7F66)',
        'System font stack',
        'Minimal, sophisticated design',
      ],
      font: 'System',
      fontWeights: [],
    },
  },
}
