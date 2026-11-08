import base from './home-experience.config.mjs';

// The reusable runner owns its desktop/mobile contexts; run it once.
export default {
  ...base,
  testMatch: 'product-editorial.spec.mjs',
  outputDir: '../../test-results/product-editorial',
  timeout: 90000,
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
};
