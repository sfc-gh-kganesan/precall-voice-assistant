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
        // Dark mode strategy game palette with more variety
        parchment: {
          50: '#faf8f3',
          100: '#f5f1e8',
          200: '#ebe3d1',
          300: '#d4c4a8',
        },
        slate: {
          700: '#374151',
          800: '#1f2937',
          850: '#1a1f2e',
          900: '#111827',
          950: '#0a0d14',
        },
        strategic: {
          500: '#6b8caf',
          600: '#4a5f7f',
          700: '#3d4f6a',
        },
        bronze: {
          400: '#e8a75f',
          500: '#cd7f32',
          600: '#b8860b',
        },
        teal: {
          500: '#3d8b8f',
          600: '#2d6f73',
          700: '#2d5f6f',
        },
        amber: {
          500: '#f59e0b',
          600: '#d97706',
        },
      },
      fontFamily: {
        'serif': ['Cinzel', 'serif'],
        'body': ['Alegreya', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
export default config
