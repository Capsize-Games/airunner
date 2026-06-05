// qa/runner.js
// Usage: node qa/runner.js [--url http://localhost:5173] [--wait 5000]

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const urlFlag  = args.indexOf('--url');
const waitFlag = args.indexOf('--wait');
const BASE_URL  = urlFlag  !== -1 ? args[urlFlag  + 1] : 'http://localhost:5173';
const WAIT_MS   = waitFlag !== -1 ? parseInt(args[waitFlag + 1], 10) : 5000;

const INSTRUMENTATION = fs.readFileSync(
  path.join(__dirname, 'browserInstrumentation.js'), 'utf8'
);

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page    = await context.newPage();

  // Inject instrumentation before any page script runs
  await page.addInitScript(INSTRUMENTATION);

  // Capture browser console output
  const consoleLogs = [];
  page.on('console', msg =>
    consoleLogs.push({ level: msg.type(), text: msg.text(), ts: Date.now() }));

  // Capture failed network requests
  const failedRequests = [];
  page.on('requestfailed', req =>
    failedRequests.push({ url: req.url(), failure: req.failure()?.errorText, ts: Date.now() }));

  console.log(`Navigating to ${BASE_URL} ...`);
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });

  await page.waitForFunction(() => window.__qaReady === true, { timeout: 10000 });
  console.log(`Waiting ${WAIT_MS}ms for WebSocket activity...`);
  await page.waitForTimeout(WAIT_MS);

  const errors   = await page.evaluate(() => window.__errors);
  const wsEvents = await page.evaluate(() => window.__wsEvents);

  const report = {
    url: BASE_URL,
    capturedAt: new Date().toISOString(),
    errors,
    wsEvents,
    consoleLogs: consoleLogs.filter(l => l.level === 'error' || l.level === 'warning'),
    failedRequests
  };

  const outPath = path.join(__dirname, 'last-report.json');
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));

  console.log('\n=== QA REPORT SUMMARY ===');
  console.log(`JS errors:       ${errors.length}`);
  console.log(`WS events:       ${wsEvents.length}`);
  console.log(`Console errors:  ${consoleLogs.filter(l => l.level === 'error').length}`);
  console.log(`Failed requests: ${failedRequests.length}`);

  if (errors.length > 0) {
    console.log('\n--- JS Errors ---');
    errors.forEach((e, i) =>
      console.log(`[${i + 1}] ${e.type}: ${e.message}\n    ${e.stack ?? ''}`));
  }
  if (failedRequests.length > 0) {
    console.log('\n--- Failed Requests ---');
    failedRequests.forEach(r => console.log(`  ${r.url} → ${r.failure}`));
  }
  if (wsEvents.some(e => e.dir === 'error')) {
    console.log('\n--- WS Errors ---');
    wsEvents.filter(e => e.dir === 'error').forEach(e => console.log(`  ${e.url}`));
  }

  console.log(`\nFull report written to: ${outPath}`);
  await browser.close();

  process.exit(errors.length > 0 || failedRequests.length > 0 ? 1 : 0);
})();
