const { test, expect } = require('@playwright/test');
const { injectAxe, checkA11y } = require('@axe-core/playwright');

// compute contrast ratio between two sRGB colors
function relativeLuminance(r, g, b) {
  const srgb = [r, g, b].map(v => v / 255).map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

function contrastRatio(fgRgb, bgRgb) {
  const L1 = relativeLuminance(fgRgb[0], fgRgb[1], fgRgb[2]);
  const L2 = relativeLuminance(bgRgb[0], bgRgb[1], bgRgb[2]);
  const lighter = Math.max(L1, L2);
  const darker = Math.min(L1, L2);
  return (lighter + 0.05) / (darker + 0.05);
}

test('visual + accessibility check for todo app', async ({ page }) => {
  await page.goto('http://localhost:5000');
  await injectAxe(page);
  // Basic accessibility scan (will throw if violations are found by default)
  await checkA11y(page, null, {
    detailedReport: true
  });

  // take a screenshot for visual review
  await page.screenshot({ path: 'tests/todo-screenshot.png', fullPage: true });

  // Check computed contrast ratio for multiple elements
  const samples = await page.evaluate(() => {
    function parseRgb(input){
      const m = input && input.match && input.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
      if(!m) return null;
      return [parseInt(m[1],10), parseInt(m[2],10), parseInt(m[3],10)];
    }

    function resolvedBackground(el){
      let node = el;
      while(node && node !== document.documentElement){
        const style = window.getComputedStyle(node);
        const bg = style.backgroundColor;
        if(bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') return bg;
        node = node.parentElement;
      }
      return window.getComputedStyle(document.documentElement).backgroundColor || 'rgb(255,255,255)';
    }

    const elements = [
      { name: 'title', el: document.querySelector('.title') },
      { name: 'subtitle', el: document.querySelector('.subtitle') },
      { name: 'todo', el: document.querySelector('.todo-text') }
    ];

    return elements.map(item => {
      if(!item.el) return { name: item.name, fg: null, bg: null };
      const cs = window.getComputedStyle(item.el);
      return {
        name: item.name,
        fg: parseRgb(cs.color) || null,
        bg: parseRgb(resolvedBackground(item.el)) || null
      };
    });
  });

  // Ensure we have samples
  expect(samples.length).toBeGreaterThanOrEqual(1);

  // Evaluate ratios and assert thresholds
  for(const s of samples){
    expect(s.fg).not.toBeNull();
    expect(s.bg).not.toBeNull();
    const ratio = contrastRatio(s.fg, s.bg);
    if(s.name === 'title' || s.name === 'todo'){
      // assert WCAG AA for normal text
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      // also assert AAA if possible for extra safety
      expect(ratio).toBeGreaterThanOrEqual(7);
    }else if(s.name === 'subtitle'){
      // subtitle can be smaller/muted; assert at least AA
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    }
  }
});
