import path from 'node:path';
import react from '@vitejs/plugin-react';
import stylexPlugin from 'unplugin-stylex/vite';
import { defineConfig } from 'vite';
import { devMockApi } from './dev-mock-plugin';

const apiTarget = process.env.API_TARGET ?? 'http://localhost:3002';
const useMockApi = process.env.MOCK_API === '1';

export default defineConfig({
    plugins: [
        react({
            babel: {
                plugins: [
                    [
                        '@stylexjs/babel-plugin',
                        {
                            dev: process.env.NODE_ENV === 'development',
                            runtimeInjection: false,
                            genConditionalClasses: true,
                            treeshakeCompensation: true,
                            unstable_moduleResolution: {
                                type: 'commonJS',
                                rootDir: process.cwd(),
                            },
                        },
                    ],
                ],
            },
        }),
        stylexPlugin(),
        ...(useMockApi ? [devMockApi()] : []),
    ],
    resolve: {
        extensions: ['.js', '.jsx', '.ts', '.tsx', '.json'],
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    optimizeDeps: {
        exclude: [
            '@snowflake/stellar-components',
            '@snowflake/stellar-data-table',
            '@snowflake/stellar-icons',
            '@snowflake/balto-themes',
        ],
        include: ['react-dom', 'react-dom/server', '@react-aria/interactions'],
    },
    build: {
        target: 'esnext',
        outDir: 'dist',
    },
    server: {
        port: 3001,
        ...(!useMockApi
            ? {
                  proxy: {
                      '/api': {
                          target: apiTarget,
                          changeOrigin: true,
                          secure: true,
                      },
                  },
              }
            : {}),
    },
});
