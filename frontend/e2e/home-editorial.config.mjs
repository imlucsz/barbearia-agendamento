import base from './home-experience.config.mjs';
export default { ...base, testMatch: 'home-editorial.spec.mjs', outputDir: '../../test-results/home-editorial', projects: base.projects.filter(p => p.name !== 'tablet') };
