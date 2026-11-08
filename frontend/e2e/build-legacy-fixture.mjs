import { mkdir, copyFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildStaticSite } from '../scripts/build-static.mjs';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = path.join(process.argv[2], 'frontend');
await mkdir(path.join(source, 'pages'), { recursive: true });
await copyFile(path.join(frontend, 'pages/reset.html'), path.join(source, 'pages/reset.html'));
await buildStaticSite({ sourceDir: source, outputDir: path.join(source, 'dist'),
  publicApiUrl: process.argv[3], redirectToApiOrigin: true });
