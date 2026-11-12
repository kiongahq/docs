import { build } from 'esbuild';
import { mkdir } from 'node:fs/promises';
await mkdir('../docs/javascripts', { recursive: true });
await build({ entryPoints: ['src/index.tsx'], bundle: true, minify: true, format: 'iife', target: 'es2020', outfile: '../docs/javascripts/interface.js', define: { 'process.env.NODE_ENV': '"production"' } });
