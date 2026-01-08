const { test, expect } = require('@playwright/test');
const { injectAxe, checkA11y } = require('@axe-core/playwright');

test('visual + accessibility check for todo app', async ({ page }) => {
  await page.goto('http://localhost:5000');
  await injectAxe(page);
  // Basic accessibility scan
  await checkA11y(page, null, {
    detailedReport: true
  });
  // take a screenshot for visual review
  await page.screenshot({ path: 'tests/todo-screenshot.png', fullPage: true });
});
