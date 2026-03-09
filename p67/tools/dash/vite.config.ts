import path from 'node:path';
import react from '@vitejs/plugin-react';
import stylexPlugin from 'unplugin-stylex/vite';
import { defineConfig } from 'vite';

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
        proxy: {
            '/api': {
                target: 'http://controld.ghw6if.svc.spcs.internal:80',
                changeOrigin: true,
            },
        },
    },
});
