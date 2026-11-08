import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, mkdir, copyFile, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { buildStaticSite } from '../scripts/build-static.mjs';

test('approved HOME fonts, licenses and intro survive static packaging without prototype paths', async t => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'home-editorial-build-'));
  t.after(() => rm(temporary, { recursive: true, force: true }));
  const source = path.join(temporary, 'frontend'), output = path.join(source, 'dist');
  const frontend = fileURLToPath(new URL('../', import.meta.url));
  const assets = ['assets/css/home-editorial.css', 'assets/js/home-experience.mjs',
    'assets/js/home-motion/intro.mjs', 'assets/fonts/Fraunces.ttf', 'assets/fonts/SpaceGrotesk.ttf',
    'assets/fonts/Fraunces-OFL.txt', 'assets/fonts/SpaceGrotesk-OFL.txt'];
  for (const asset of ['pages/index.html', ...assets]) {
    await mkdir(path.dirname(path.join(source, asset)), {recursive:true});
    await copyFile(path.join(frontend, asset), path.join(source, asset));
  }
  await buildStaticSite({ sourceDir:source, outputDir:output, publicApiUrl:'https://api.example.test' });
  const html = await readFile(path.join(output, 'pages/index.html'), 'utf8');
  assert.ok(html.includes('../assets/css/home-editorial.css'));
  assert.ok(!html.includes('data-preview'));
  for (const asset of assets) {
    const built = await readFile(path.join(output, asset));
    assert.deepEqual(built, await readFile(path.join(frontend, asset)), asset);
    if (/\.(css|mjs)$/.test(asset)) assert.doesNotMatch(built.toString(), /prototypes\/|\/shared\//);
  }
});
