import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env.NODE_ENV': JSON.stringify('production')
  },
  build: {
    lib: {
      entry: resolve(__dirname, 'src/main.tsx'),
      name: 'SnowflakeChatWidget',
      fileName: 'chat-widget',
      formats: ['iife']
    },
    outDir: 'dist',
    rollupOptions: {
      output: {
        inlineDynamicImports: true
      }
    }
  },
  server: {
    port: 8080,
    open: '../demos/snowflake.html'
  }
})
