// Official document -> review -> edit -> COI download, with all remote requests blocked.
const {chromium}=require(process.env.FORMFORGE_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const root=path.resolve(__dirname,'..'),base=process.env.FORMFORGE_BASE_URL||'http://127.0.0.1:8765';
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.FORMFORGE_CHROMIUM||chromium.executablePath()});
  const context=await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true,locale:'pl-PL'}),page=await context.newPage(),errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(['http:','https:'].includes(u.protocol)&&u.origin!==new URL(base).origin){external.push(u.href);return r.abort();}return r.continue();});
  const out=path.join(root,'output/qa');await fs.mkdir(out,{recursive:true});
  try{
    await page.goto(base);
    const dir=path.join(root,'reference/coi-official/forms/05'),file=(await fs.readdir(dir)).find(n=>n.toLowerCase().endsWith('.pdf'));
    const response=page.waitForResponse(r=>r.url().includes('/forms/convert'));await page.locator('#file-input').setInputFiles(path.join(dir,file));
    const data=await (await response).json();assert.equal(data.coi_validation.valid,true);assert.equal(data.export.tabs.length,4);
    await page.locator('#results').waitFor({state:'visible'});await page.getByRole('tab',{name:'Zgodność z COI'}).click();
    assert.match(await page.locator('#coi-view').textContent(),/Nieprzeprowadzony/);assert.match(await page.locator('#coi-view').textContent(),/uzupełnień standardu/);
    await page.screenshot({path:path.join(out,'coi-compliance.png'),fullPage:true});
    await page.locator('[data-tab="eform"]').click();
    await page.getByRole('radio',{name:'Swoim',exact:true}).check();
    const company=page.locator('.eform-section').filter({has:page.locator('legend').getByText('Dane podmiotu',{exact:true})});await company.waitFor({state:'hidden'});
    await page.getByRole('radio',{name:'Osoby prawnej lub jednostki organizacyjnej',exact:true}).check();await company.waitFor({state:'visible'});
    const bank=page.getByLabel('Numer rachunku *',{exact:true});await bank.waitFor({state:'hidden'});
    await page.getByRole('radio',{name:'Zwrócić przelewem na rachunek bankowy',exact:true}).check();await bank.waitFor({state:'visible'});
    await page.getByRole('radio',{name:'Zaliczyć na poczet przyszłego zobowiązania podatkowego',exact:true}).check();await bank.waitFor({state:'hidden'});
    assert.equal(await page.locator('input[disabled]').count()>0,true);assert.equal(await page.locator('.eform-field').filter({hasText:'Opłata skarbowa za pełnomocnictwo według'}).locator('input').count(),0);
    await page.screenshot({path:path.join(out,'coi-eform.png'),fullPage:true});
    await page.locator('[data-tab="fields"]').click();const field=page.locator('#fields-body tr').filter({has:page.locator('.label-input[value="Kwota"]')});
    // Locate by current input value (the DOM value property is authoritative).
    const id=data.form.fields.find(f=>f.label==='Kwota').id,row=page.locator(`tr[data-field-id="${id}"]`);await row.locator('summary').click();await row.locator('.confirm-input').check();await row.locator('.label-input').fill('Kwota nadpłaty');
    const edited=page.waitForResponse(r=>r.url().endsWith('/forms/validate'));await page.locator('#apply-fields').click();const updated=await (await edited).json();assert.equal(updated.coi_validation.valid,true);assert.equal(updated.form.fields.find(f=>f.id===id).coi.confirmed,true);
    const downloadPromise=page.waitForEvent('download');await page.locator('#download-json').click();const download=await downloadPromise;assert.equal(download.suggestedFilename(),'formforge-coi.json');await download.saveAs(path.join(out,'official-download.json'));
    const payload=JSON.parse(await fs.readFile(path.join(out,'official-download.json'),'utf8'));assert.deepEqual(Object.keys(payload).sort(),['flow','tabs','title']);assert.ok(JSON.stringify(payload).includes('Kwota nadpłaty'));
    const checked=await context.request.post(base+'/api/v1/forms/coi-validate',{data:payload});assert.equal((await checked.json()).valid,true);
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    const report={status:'passed',checks:['official PDF upload','COI diagnostics','applicant SHOW','refund SHOW','registry readOnly','static text without inputs','property confirmation','edited official JSON download','raw COI validation'],browserErrors:errors,externalRequests:external};await fs.writeFile(path.join(out,'coi-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  }catch(e){await page.screenshot({path:path.join(out,'coi-failure.png'),fullPage:true});console.error({errors,external});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
