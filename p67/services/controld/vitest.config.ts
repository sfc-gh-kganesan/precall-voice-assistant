import { defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        include: ['dist/**/*.test.js'],
        exclude: ['src/**/*.test.ts', 'node_modules/**/*'],
    },
});
