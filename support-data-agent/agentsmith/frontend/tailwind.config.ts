import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        // Snowflake-inspired color palette
        navy: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#b9e6fe',
          300: '#7cd4fd',
          400: '#36bffa',
          500: '#0ba5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#1e3a5f',
          900: '#1F2937',  // Main dark background
          950: '#111827',  // Darker sections
        },
        // Accent cyan/blue
        cyan: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#29B5E8',  // Primary accent
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
        },
        // Text colors
        text: {
          primary: '#f9fafb',
          secondary: '#d1d5db',
          tertiary: '#9ca3af',
          muted: '#6b7280',
        },
        // Borders
        border: {
          light: '#374151',
          DEFAULT: '#1f2937',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Fira Code', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
export default config
