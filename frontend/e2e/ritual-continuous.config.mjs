import base from './home-experience.config.mjs';
const sizes = [[1440,900],[1366,768],[1440,640],[1366,640],[1280,600],
  [820,1180],[390,844],[375,812],[360,800],[320,568],[844,390]];
export default {
  ...base, timeout: 60000, outputDir: '../../test-results/ritual-continuous',
  grep: /Ritual universal/,
  projects: [...['chrome','msedge'].flatMap(channel => sizes.map(([width,height]) => ({
    name: `${channel}-${width}x${height}`,
    use: { channel, viewport:{width,height}, hasTouch:width<1000, isMobile:width<1000 }
  }))), ...['firefox','webkit'].flatMap(browserName => [[1440,900],[390,844]].map(([width,height]) => ({
    name:`${browserName}-${width}x${height}`, use:{browserName,viewport:{width,height}}
  })))]
};
