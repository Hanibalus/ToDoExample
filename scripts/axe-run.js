const fs = require("fs");
const { chromium } = require("playwright");
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("http://localhost:5000");

  // inject axe-core script into the page
  const axePath = path.join(__dirname, '..', 'node_modules', '@axe-core', 'playwright', 'node_modules', 'axe-core', 'axe.min.js');
  let axeSource;
  try {
    axeSource = fs.readFileSync(axePath, 'utf8');
  } catch (e) {
    // fallback: attempt to require axe-core package directly
    try { axeSource = require('fs').readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8'); } catch (e2) { throw e; }
  }
  await page.addScriptTag({ content: axeSource });
  const results = await page.evaluate(async () => await axe.run());
  fs.mkdirSync("tests", { recursive: true });
  fs.writeFileSync("tests/axe-report.json", JSON.stringify(results, null, 2));
  await page.screenshot({ path: "tests/todo-screenshot.png", fullPage: true });
  await browser.close();
  console.log("Axe report and screenshot saved.");
})().catch(err => { console.error(err); process.exit(1); });
