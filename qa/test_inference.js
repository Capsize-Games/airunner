/**
 * Inference test. LLM may need longer (9B model), art should be quick.
 */
const { chromium } = require('playwright');
const BASE_URL = 'http://localhost:5173';

const waitFor = (page, predicate, timeout) => new Promise(resolve => {
  const start = Date.now();
  const check = async () => {
    if (await predicate()) return resolve(true);
    if (Date.now() - start >= timeout) return resolve(false);
    setTimeout(check, 500);
  };
  check();
});

async function main() {
  console.log('=== INFERENCE TEST ===\n');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = [];
  page.on('console', msg => { if(msg.type()==='error') errors.push(msg.text()); });

  try {
    // ===== LLM =====
    console.log('--- LLM: Qwen3.5-9B ---');
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    await page.locator('select').nth(1).selectOption('Qwen/Qwen3.5-9B');
    await page.waitForTimeout(1000);
    console.log('Model selected, sending message...');
    await page.locator('textarea').first().fill('What is 2+2? Reply with just the number.');
    await page.locator('button').filter({ has: page.locator('svg') }).first().click();
    console.log('Sent. LLM generating (9B model, may take 30-60s)...');

    const llmOk = await waitFor(page, async () => {
      const t = await page.evaluate(() => document.body.innerText);
      return t.includes('4') || t.toLowerCase().includes('paris') || t.includes('capital');
    }, 120000); // 2 min for 9B model

    if (llmOk) {
      console.log('✅ LLM RESPONDED');
      const t = await page.evaluate(() => document.body.innerText);
      console.log(`Response: ${t.substring(0, 300)}`);
    } else {
      console.log('⚠️ No response in 2min');
      const t = await page.evaluate(() => document.body.innerText);
      console.log(`Page: ${t.substring(0, 200)}`);
    }

    // ===== ART =====
    console.log('\n--- ART: Z-Image Turbo ---');
    await page.goto(`${BASE_URL}/art`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    await page.locator('select').first().selectOption('Z-Image Turbo');
    await page.locator('textarea').first().fill('A mountain lake at sunset');
    await page.locator('button:has-text("Generate")').click();
    console.log('Sent. Waiting 30s...');

    const artOk = await waitFor(page, async () => {
      const t = await page.evaluate(() => document.body.innerText);
      return t.includes('data:image/png;base64,') || t.includes('Generation failed');
    }, 30000);

    if (artOk) {
      const t = await page.evaluate(() => document.body.innerText);
      const imgs = await page.locator('img').count();
      console.log(t.includes('data:image') ? '✅ ART COMPLETED' : `⚠️ ${t.substring(0,200)}`);
      console.log(`Images: ${imgs}`);
    } else {
      console.log('⚠️ No result in 30s');
    }

  } catch(e) { console.error('Error:', e.message); }
  finally { await browser.close(); }

  const real = errors.filter(e => !e.includes('children with the same key'));
  console.log(`\nErrors: ${errors.length} (${real.length} real)`);
}

main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
