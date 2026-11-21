// Extended editor/source-mapping regression. No recognition tuning or remote assets.
const {chromium}=require(process.env.FORMFORGE_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');const fs=require('node:fs/promises');const path=require('node:path');
const root=path.resolve(__dirname,'..'),base=process.env.FORMFORGE_BASE_URL||'http://127.0.0.1:8765';
(async()=>{
  const out=path.join(root,'output/qa');await fs.mkdir(out,{recursive:true});
  const browser=await chromium.launch({headless:true,executablePath:process.env.FORMFORGE_CHROMIUM||chromium.executablePath()});
  const context=await browser.newContext({viewport:{width:1600,height:1100},locale:'pl-PL'}),page=await context.newPage();const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(['http:','https:'].includes(u.protocol)&&u.origin!==new URL(base).origin){external.push(u.href);return r.abort();}return r.continue();});
  try{
    await page.goto(base);await page.locator('#analysis-mode').selectOption('local-ai-assisted');
    const converted=page.waitForResponse(r=>r.url().includes('/forms/convert'));await page.locator('[data-demo="zezwolenie.docx"]').click();const response=await converted;assert.equal(response.status(),200);const data=await response.json();assert.ok(data.document.analysis.local_ai);
    await page.locator('#results').waitFor({state:'visible'});await page.locator('[data-tab="document"]').click();await page.locator('.source-field-item').first().click();assert.match(await page.locator('.source-location').textContent(),/Źródło/);
    await page.getByRole('button',{name:'Podgląd e-formularza →',exact:true}).click();assert.ok(await page.frameLocator('.comparison-eform').locator('form').count());
    await page.screenshot({path:path.join(out,'original-to-eform.png'),fullPage:true});
    await page.locator('[data-tab="fields"]').click();const rows=page.locator('#fields-body tr[data-field-id]');
    for(let i=0;i<2;i++){await rows.nth(i).locator('summary').click();await rows.nth(i).locator('.group-input').fill('Dane wspólne');await rows.nth(i).locator('.section-input').selectOption(data.form.sections[1].id);}
    await rows.first().locator('.validation-input').fill('[{"kind":"max_length","value":90}]');await rows.first().locator('.order-input').fill('99');
    await page.locator('#add-field').click();await rows.last().locator('.label-input').fill('Tryb zgłoszenia');
    await page.locator('.editor-section-rules summary').click();await page.locator('.dictionary-title').fill('Tryb zgłoszenia');await page.locator('.dictionary-values').fill('Standardowy | Pilny');await page.getByRole('button',{name:'Dodaj proponowany słownik'}).click();
    await rows.last().locator('summary').click();await rows.last().locator('.type-input').selectOption('select');await rows.last().locator('.dictionary-input').selectOption({label:'Tryb zgłoszenia · proponowany'});
    const deleted=await rows.nth(3).getAttribute('data-field-id');await rows.nth(3).locator('summary').click();await rows.nth(3).locator('.delete-field').click();
    const edited=page.waitForResponse(r=>r.url().endsWith('/forms/validate'));await page.locator('#apply-fields').click();const checked=await edited;assert.equal(checked.status(),200);const actual=(await checked.json()).form;
    assert.ok(actual.fields.some(f=>f.label==='Tryb zgłoszenia'&&f.field_type==='select'&&f.options.length===2));assert.ok(!actual.fields.some(f=>f.id===deleted));assert.ok(actual.groups.some(g=>actual.fields.filter(f=>f.group_id===g.id).length>=2));assert.deepEqual(actual.fields.map(f=>f.order),actual.fields.map((_,i)=>i));assert.ok(actual.fields.some(f=>f.validation.some(r=>r.kind==='max_length'&&r.value===90)));
    await rows.first().locator('summary').click();await rows.first().locator('.group-input').fill('');const splitResponse=page.waitForResponse(r=>r.url().endsWith('/forms/validate'));await page.locator('#apply-fields').click();const split=await splitResponse;assert.equal(split.status(),200);assert.equal((await split.json()).form.fields[0].group_id,null);
    await page.locator('[data-tab="eform"]').click();await page.getByLabel('Tryb zgłoszenia',{exact:true}).selectOption('Pilny');
    await page.locator('#reset-file').click();const imageResponse=page.waitForResponse(r=>r.url().includes('/forms/convert'));await page.locator('#file-input').setInputFiles(path.join(root,'demo_samples/checkbox.png'));assert.equal((await imageResponse).status(),200);await page.locator('#results').waitFor({state:'visible'});await page.locator('[data-tab="document"]').click();await page.locator('.source-field-item').first().click();await page.locator('.source-region').waitFor({state:'visible'});await page.screenshot({path:path.join(out,'source-highlight.png'),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);const report={status:'passed',checks:['local classifier mode','source navigation','original-to-eForm comparison','validation editing','section assignment','group merge and split','field addition','dictionary creation and assignment','field deletion','order normalization','updated JSON','updated eForm','image source overlay'],browserErrors:errors,externalRequests:external};await fs.writeFile(path.join(out,'review-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  }catch(error){await page.screenshot({path:path.join(out,'review-failure.png'),fullPage:true});console.error({errors,external});throw error;}finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
