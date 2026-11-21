// Optional browser QA. Playwright is a development tool, not a runtime dependency.
const { chromium } = require(process.env.FORMFORGE_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const root = path.resolve(__dirname, '..');
const base = process.env.FORMFORGE_BASE_URL || 'http://127.0.0.1:8765';

(async () => {
  const output = path.join(root, 'output', 'qa');
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.FORMFORGE_CHROMIUM || chromium.executablePath() });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, acceptDownloads: true, locale: 'pl-PL' });
  const page = await context.newPage();
  const errors = [], external = [];
  page.on('pageerror', error => errors.push(error.message));
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (['http:', 'https:'].includes(url.protocol) && url.origin !== new URL(base).origin) {
      external.push(url.href); return route.abort();
    }
    return route.continue();
  });
  try {
    await page.goto(base);
    await page.getByText('Serwer lokalny · online').waitFor();
    await page.screenshot({ path: path.join(output, 'welcome-desktop.png'), fullPage: true });
    const converted = page.waitForResponse(r => r.url().includes('/api/v1/forms/convert'));
    await page.locator('[data-demo="zezwolenie.docx"]').click();
    assert.equal((await converted).status(), 200);
    await page.locator('#results').waitFor({ state: 'visible' });
    await page.locator('[data-tab="fields"]').click();
    assert.ok(await page.locator('#fields-body tr[data-field-id]').count() >= 10);
    await page.locator('#fields-body .label-input').first().fill('Nazwa wnioskodawcy po korekcie');
    await page.locator('#fields-body .type-input').first().selectOption('text');
    await page.locator('#fields-body .required-input').first().check();
    const edited = page.waitForResponse(r => r.url().endsWith('/api/v1/forms/validate'));
    await page.locator('#apply-fields').click();
    assert.equal((await edited).status(), 200);
    await page.getByText('Zapisano zmiany w pamięci karty.', { exact: false }).waitFor();
    await page.screenshot({ path: path.join(output, 'detected-fields.png'), fullPage: true });
    await page.locator('[data-tab="json"]').click();
    assert.match(await page.locator('#json-view').textContent(), /Nazwa wnioskodawcy po korekcie/);
    const downloaded = page.waitForEvent('download');
    await page.locator('#download-json').click();
    const download = await downloaded;
    await download.saveAs(path.join(output, 'download-coi.json'));
    const json = JSON.parse(await fs.readFile(path.join(output, 'download-coi.json'), 'utf8'));
    assert.deepEqual(Object.keys(json).sort(),['flow','tabs','title']);
    assert.ok(JSON.stringify(json).includes('Nazwa wnioskodawcy po korekcie'));
    await page.locator('#toast').waitFor({ state: 'hidden' });
    await page.locator('[data-tab="eform"]').click();
    await page.getByRole('button', { name: 'Sprawdź formularz' }).click();
    await page.getByText('Popraw oznaczone pola.', { exact: true }).waitFor();
    await page.getByLabel('Nazwa wnioskodawcy po korekcie *', { exact: true }).fill('Jan Testowy');
    await page.getByLabel('PESEL *', { exact: true }).fill('44051401458');
    const validated = page.waitForResponse(r => r.url().endsWith('/api/v1/forms/validate'));
    await page.getByRole('button', { name: 'Sprawdź formularz' }).click();
    assert.equal((await validated).status(), 200);
    await page.getByText('Dane są poprawne.', { exact: false }).waitFor();
    await page.screenshot({ path: path.join(output, 'eform-desktop.png'), fullPage: true });
    for (const tab of ['structure', 'validation', 'document']) await page.locator(`[data-tab="${tab}"]`).click();
    await page.locator('#reset-file').click();
    const multiResponse = page.waitForResponse(r => r.url().includes('/api/v1/forms/convert'));
    await page.locator('#file-input').setInputFiles(path.join(root, 'demo_samples', 'wielostronicowy.pdf'));
    assert.equal((await multiResponse).status(), 200);
    await page.locator('#results').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#stat-pages').textContent(), '3');
    await page.locator('[data-tab="eform"]').click();
    await page.getByLabel('NIP', { exact: true }).waitFor({ state: 'hidden' });
    await page.getByRole('radio', { name: 'Firma', exact: true }).check();
    await page.getByLabel('NIP', { exact: true }).waitFor({ state: 'visible' });
    await page.getByRole('radio', { name: 'Osoba fizyczna', exact: true }).check();
    await page.getByLabel('NIP', { exact: true }).waitFor({ state: 'hidden' });
    await page.locator('#reset-file').click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'welcome-mobile.png'), fullPage: true });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.setViewportSize({ width: 1440, height: 1050 });
    await page.goto(base + '/docs');
    await page.locator('.swagger-ui .opblock').first().waitFor();
    await page.screenshot({ path: path.join(output, 'swagger-offline.png'), fullPage: true });
    assert.deepEqual(external, [], 'Browser requested external assets');
    assert.deepEqual(errors, [], 'Uncaught browser errors');
    console.log(JSON.stringify({ status: 'passed', scenarios: ['upload', 'demo', 'field editing', 'JSON download', 'native required validation', 'server validation', 'conditional visibility', 'responsive mobile layout', 'offline Swagger'], externalRequests: external, browserErrors: errors }, null, 2));
  } catch (error) {
    await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true });
    console.error(JSON.stringify({ browserErrors: errors, externalRequests: external, url: page.url(), body: (await page.locator('body').innerText()).slice(0,2000) }, null, 2));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
