// Actual oversized-image upload, isolated worker timeout, and source-offset contract.
const {chromium}=require(process.env.FORMFORGE_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const root=path.resolve(__dirname,'..'),base=process.env.FORMFORGE_BASE_URL||'http://127.0.0.1:8765';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.FORMFORGE_CHROMIUM||chromium.executablePath()});
 const context=await browser.newContext({viewport:{width:1600,height:1100}}),page=await context.newPage(),errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 await context.route('**/*',r=>{const u=new URL(r.request().url());if(['http:','https:'].includes(u.protocol)&&u.origin!==new URL(base).origin){external.push(u.href);return r.abort();}return r.continue();});
 try{
  await page.goto(base);const dir=path.join(root,'reference/coi-official/forms/09'),file=(await fs.readdir(dir)).find(n=>n.toLowerCase().endsWith('.png'));
  const start=Date.now(),converted=page.waitForResponse(r=>r.url().includes('/forms/convert'),{timeout:100000});
  await page.locator('#file-input').setInputFiles(path.join(dir,file));const response=await converted;assert.equal(response.status(),200);const data=await response.json();
  assert.equal(data.coi_validation.valid,true);assert.equal(data.quality.completeness_verified,false);assert.ok(data.form.fields.length>50);assert.ok(data.document.analysis.image_tiles.length>10);
  await page.locator('#results').waitFor({state:'visible'});await page.locator('[data-tab="document"]').click();await page.waitForFunction(()=>document.querySelector('.source-tiled')?.naturalHeight>30000);
  const field=data.form.fields.find(f=>f.source_reference.page>=4&&f.source_reference.bbox),tile=data.document.analysis.image_tiles.find(t=>t.page===field.source_reference.page),box=field.source_reference.input_bbox||field.source_reference.bbox;
  await page.locator(`[data-source-field="${field.id}"]`).click();const top=parseFloat(await page.locator('.source-region').evaluate(n=>n.style.top));const height=await page.locator('.source-tiled').evaluate(n=>n.naturalHeight);
  assert.ok(Math.abs(top-(box[1]+tile.source_bbox[1])/height*100)<.001);
  assert.equal(await page.locator('.source-tiled').evaluate(n=>getComputedStyle(n).maxHeight),'none');await page.waitForFunction(()=>{const r=document.querySelector('.source-region')?.getBoundingClientRect(),p=document.querySelector('.review-original')?.getBoundingClientRect();return r&&p&&r.top>=p.top-2&&r.bottom<=p.bottom+2&&document.querySelector('.review-original').scrollTop>0;});assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const out=path.join(root,'output/qa');await fs.mkdir(out,{recursive:true});await page.screenshot({path:path.join(out,'large-image-source.png')});
  const report={status:'passed',seconds:(Date.now()-start)/1000,fields:data.form.fields.length,tiles:data.document.analysis.image_tiles.length,quality:data.quality.status,checks:['actual 61.9MP image upload','HTTP worker completes within deadline','valid official COI','quality disclosure','source tile offset on original image','readable source scaling'],browserErrors:errors,externalRequests:external};await fs.writeFile(path.join(out,'large-image-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
