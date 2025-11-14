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
    optimizeDeps: {
        exclude: [
            '@snowflake/stellar-components',
            '@snowflake/stellar-charts',
            '@snowflake/stellar-data-table',
            '@snowflake/stellar-data-tools',
            '@snowflake/stellar-icons',
            '@snowflake/balto-themes',
        ],
    },
});
