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
    outfile: 'dist/bundle.js',
    sourcemap: true,
    minify: false,
    packages: 'bundle', // Bundle all dependencies
    legalComments: 'inline', // Preserve comments in output
  });

  console.log('Bundle completed successfully!');
  console.log('Output: dist/bundle.js');
} catch (error) {
  console.error('Bundle failed:', error);
  process.exit(1);
}
