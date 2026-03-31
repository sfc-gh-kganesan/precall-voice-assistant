import * as esbuild from 'esbuild';

await esbuild.build({
    entryPoints: ['src/index.ts'],
    bundle: true,
    platform: 'node',
    target: 'node20',
    format: 'esm',
    outfile: 'build/index.js',
    sourcemap: true,
    minify: false,
});

console.log('Build complete: build/index.js');
