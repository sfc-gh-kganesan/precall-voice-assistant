import * as esbuild from 'esbuild';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync, mkdirSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const distDir = join(__dirname, 'dist');

if (!existsSync(distDir)) {
    mkdirSync(distDir, { recursive: true });
}

try {
    await esbuild.build({
        entryPoints: ['src/index.ts'],
        bundle: true,
        platform: 'node',
        target: 'node20',
        format: 'esm',
        outfile: 'dist/index.js',
        sourcemap: true,
    });

    console.log('Build completed successfully!');
    console.log('Output: dist/index.js');
} catch (error) {
    console.error('Build failed:', error);
    process.exit(1);
}
