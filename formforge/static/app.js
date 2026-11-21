(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const typeLabels={text:'Tekst',textarea:'Dłuższy tekst',number:'Liczba',date:'Data',email:'E-mail',phone:'Telefon',pesel:'PESEL',nip:'NIP',regon:'REGON',postal_code:'Kod pocztowy',checkbox:'Checkbox',radio:'Jednokrotny wybór',select:'Lista wyboru',address:'Adres',attachment:'Załącznik',information:'Informacja',consent:'Sekcja zgody'};
  const stageLabels={file_validation:'Plik',extraction:'Odczyt',layout:'Układ',field_detection:'Wykrycie pól',structure:'Struktura',validation:'Walidacja',json_mapping:'JSON'};
  let result=null,sourceFile=null,sourceUrl=null,busy=false,exportData=null,toastTimer;
  function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3000);}
  const authHeaders=()=>{const token=$('jwt-token')?.value.trim();return token?{Authorization:'Bearer '+token}:{};};
  async function request(url,options={}) {
    const response=await fetch(url,{...options,headers:{...authHeaders(),...options.headers}});
    const data=await response.json();
    if (!response.ok) throw new Error(data.error?.message||data.detail||'Wystąpił błąd serwera.');
    return data;
  }
  window.FormForgeValidate=async(form,values)=>(await request('/api/v1/forms/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({form,values})})).value_issues;
  function error(message){$('error-banner').textContent=message;$('error-banner').hidden=false;}
  function setBusy(value){busy=value;document.querySelectorAll('.demo-card,#choose-file').forEach(n=>n.disabled=value);$('dropzone').setAttribute('aria-disabled',String(value));}
  function showStages(stages){$('stages').replaceChildren(...Object.entries(stageLabels).map(([key,label],i)=>{const stage=stages?.find(s=>s.stage===key);return make('span','stage '+(stage?'completed':i===1?'active':''),(stage?'✓ ':'')+label+(stage?.duration_ms?` · ${Math.round(stage.duration_ms)} ms`:''));}));}
  async function convert(file){
    if(busy)return;
    if(!file)return;
    if(file.size>Number(document.querySelector('.card-title .small').textContent.match(/[0-9]+/)[0])*1024*1024){error('Plik przekracza maksymalny rozmiar.');return;}
    setBusy(true);$('error-banner').hidden=true;$('results').hidden=true;$('welcome').hidden=true;$('upload-card').hidden=true;$('process-card').hidden=false;
    $('process-title').textContent='Przetwarzanie dokumentu';$('process-file').textContent=file.name;
    const spinner=$('process-card').querySelector('.spinner');spinner.classList.remove('done');spinner.textContent='';showStages();
    try{
      const body=new FormData();body.append('file',file);
      result=await request('/api/v1/forms/convert?analysis_mode='+($('analysis-mode')?.value||'deterministic'),{method:'POST',body});sourceFile=file;
      if(sourceUrl)URL.revokeObjectURL(sourceUrl);sourceUrl=URL.createObjectURL(file);
      exportData=result.export;showStages(result.stages);spinner.classList.add('done');spinner.textContent='✓';
      $('process-title').textContent=result.quality?.status==='no_fields'?'Nie rozpoznano pól — sprawdź źródło':result.quality?.status==='partial'?'Analiza częściowa — sprawdź ostrzeżenia':'Analiza zakończona — wynik wymaga przeglądu';$('process-note').textContent='Oryginalny plik został usunięty z serwera. Podgląd źródła korzysta z pliku w tej karcie.';
      render();selectTab('document');$('results').hidden=false;
      $('results').scrollIntoView({behavior:'smooth',block:'start'});
    }catch(e){error(e.message);$('upload-card').hidden=false;$('welcome').hidden=false;$('process-card').hidden=true;}
    finally{setBusy(false);$('file-input').value='';}
  }
  function render(){
    const form=result.form;
    $('result-title').textContent=form.title;$('result-file').textContent=`${sourceFile.name} · ${(sourceFile.size/1024).toFixed(1)} KB · ${result.document.format.toUpperCase()}`;
    $('stat-pages').textContent=form.pages.length;$('stat-fields').textContent=form.fields.length;$('stat-sections').textContent=form.sections.length;
    $('stat-review').textContent=Object.values(result.coi_validation?.provenance||{}).filter(p=>p.requires_confirmation).length;
    $('field-count').textContent=form.fields.length;$('issue-count').textContent=result.issues.length;
    renderSource();renderFields();renderStructure();renderJSON();renderIssues();window.FormForgeCompatibility($('coi-view'),result);window.FormForgeRender($('eform-view'),form);
    $('download-json').disabled=!result.coi_validation?.valid;
  }
  function renderSource(){
    const view=$('source-view');view.replaceChildren();const ext=result.document.format;
    if(['png','jpg','jpeg','jpe'].includes(ext)){const img=make('img','source-image'+(result.document.analysis?.image_tiles?.length?' source-tiled':''));img.src=sourceUrl;img.alt='Przesłany dokument';view.append(img);$('source-caption').textContent='Oryginał · tylko w pamięci przeglądarki';}
    else if(ext==='pdf'){const iframe=make('iframe','source-pdf');iframe.src=sourceUrl;iframe.title='Oryginalny dokument PDF';view.append(iframe);$('source-caption').textContent='Oryginalny PDF · lokalny podgląd przeglądarki';}
    else{
      $('source-caption').textContent='Odtworzony tekst i tabele · bez składu Word / Excel';
      const fieldBlocks=new Set(result.form.fields.map(f=>f.source_reference.block_id));
      for(const page of result.document.pages){const sheet=make('article','source-document');sheet.append(make('div','source-page-header',`${page.title} / ${result.document.format.toUpperCase()}`));for(const block of result.document.blocks.filter(b=>b.page===page.id)){const para=make('p','source-block'+(block.kind==='heading'?' heading':'')+(fieldBlocks.has(block.id)?' field':''),block.text);para.dataset.blockId=block.id;if(block.metadata.cell)para.title=block.metadata.cell;sheet.append(para);}view.append(sheet);}
    }
    window.FormForgeSource.attach(view,result,sourceUrl);
  }
  function renderFields(){
    const body=$('fields-body');body.replaceChildren();
    for(const field of result.form.fields){
      const row=make('tr');row.dataset.fieldId=field.id;
      const labelCell=make('td'),input=make('input');input.type='text';input.value=field.label;input.className='label-input';input.setAttribute('aria-label','Etykieta pola');labelCell.append(input,make('div','source-snippet',field.source_reference.text));
      const typeCell=make('td'),select=make('select');select.className='type-input';select.setAttribute('aria-label','Typ pola');for(const [value,title]of Object.entries(typeLabels)){const option=make('option','',title);option.value=value;select.append(option);}select.value=field.field_type;typeCell.append(select);
      const options=make('input','options-editor');options.type='text';options.value=field.options.join(' | ');options.placeholder='Opcje oddzielone |';options.setAttribute('aria-label','Opcje wyboru oddzielone pionową kreską');options.hidden=!['radio','select'].includes(field.field_type);typeCell.append(options);select.addEventListener('change',()=>options.hidden=!['radio','select'].includes(select.value));
      const reqCell=make('td'),required=make('input');required.type='checkbox';required.className='required-input';required.checked=field.required;required.setAttribute('aria-label','Pole wymagane');reqCell.append(required);
      const source=make('td'),ref=field.source_reference;source.append(make('span','field-source',field.coi?.origin==='standard_policy'?'Dodane według standardu COI':`Str. ${ref.page}${ref.cell?' · '+ref.cell:''}`),make('span','field-source',field.detection_method));
      const confidence=make('td');confidence.append(make('span','field-confidence'+(field.confidence<.8?' low':''),field.confidence.toFixed(2)+' score'));
      row.append(labelCell,typeCell,reqCell,source,confidence);body.append(row);window.FormForgeEditor.decorate(row,field,result.form);
    }
    if(!result.form.fields.length){const row=make('tr'),cell=make('td','empty-state','Brak rozpoznanych pól. Sprawdź dokument i ostrzeżenia.');cell.colSpan=5;row.append(cell);body.append(row);}
    window.FormForgeEditor.mount(result.form,body,renderFields);
  }
  function renderStructure(){const view=$('structure-view');view.replaceChildren();if(exportData?.tabs){for(const tab of exportData.tabs){const p=make('div','structure-page');p.append(make('h3','',tab.title+' · '+tab.type));for(const question of tab.questions){const field=question.field,s=make('div','structure-section');s.append(make('strong','',field.title||field.type));for(const child of field.repeatingSectionGrid||[]){const f=make('div','structure-field');f.append(make('span','',child.field.title||child.field.description),make('span','',child.field.type));s.append(f);}p.append(s);}view.append(p);}return;}for(const page of result.form.pages){const p=make('div','structure-page');p.append(make('h3','',`${page.id.toString().padStart(2,'0')} · ${page.title}`));for(const section of result.form.sections.filter(s=>s.page===page.id)){const s=make('div','structure-section');s.append(make('strong','',section.title));section.instructions.forEach(text=>s.append(make('p','structure-instruction',text)));for(const field of result.form.fields.filter(f=>f.section===section.id)){const f=make('div','structure-field');f.append(make('span','',field.label+(field.required?' *':'')),make('span','',typeLabels[field.field_type]));s.append(f);}p.append(s);}view.append(p);}}
  function renderJSON(){$('json-view').textContent=JSON.stringify(exportData,null,2);}
  function renderIssues(){const view=$('validation-view');view.replaceChildren();for(const issue of result.issues){const row=make('div','issue '+issue.severity),icon=make('span','issue-icon',issue.severity==='error'?'×':'!'),content=make('div');content.append(make('strong','',issue.message));if(issue.field_id){const field=result.form.fields.find(f=>f.id===issue.field_id);content.append(make('p','',field?.label||issue.field_id));}row.append(icon,content);view.append(row);}}
  function selectTab(name){document.querySelectorAll('[data-tab]').forEach(button=>{const selected=button.dataset.tab===name;button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;});document.querySelectorAll('[role=tabpanel]').forEach(panel=>panel.hidden=panel.id!=='panel-'+name);}
  async function applyEdits(){
    const next=structuredClone(result.form);
    try{Object.assign(next,window.FormForgeEditor.read(next,$('fields-body')));}catch(e){error('Niepoprawna edycja: '+e.message);return;}
    $('apply-fields').disabled=true;
    try{const checked=await request('/api/v1/forms/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({form:next})});result.form=next;result.issues=checked.issues;result.coi_validation=checked.coi_validation;exportData=checked.export;result.export=checked.export;$('error-banner').hidden=true;render();$('save-status').textContent='Zapisano zmiany w pamięci karty. JSON i podgląd zostały odświeżone.';toast('Zaktualizowano formularz i JSON');}catch(e){error(e.message);}finally{$('apply-fields').disabled=false;}
  }
  function reset(){if(busy)return;if(sourceUrl)URL.revokeObjectURL(sourceUrl);sourceUrl=null;result=null;sourceFile=null;exportData=null;$('results').hidden=true;$('process-card').hidden=true;$('upload-card').hidden=false;$('welcome').hidden=false;$('error-banner').hidden=true;$('save-status').textContent='';$('source-view').replaceChildren();$('eform-view').replaceChildren();window.scrollTo({top:0,behavior:'smooth'});}
  $('choose-file').addEventListener('click',event=>{event.stopPropagation();if(!busy)$('file-input').click();});$('dropzone').addEventListener('click',()=>{if(!busy)$('file-input').click();});$('dropzone').addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();if(!busy)$('file-input').click();}});$('file-input').addEventListener('change',event=>convert(event.target.files[0]));
  for(const name of ['dragenter','dragover'])$('dropzone').addEventListener(name,event=>{event.preventDefault();$('dropzone').classList.add('dragover');});for(const name of ['dragleave','drop'])$('dropzone').addEventListener(name,event=>{event.preventDefault();$('dropzone').classList.remove('dragover');});$('dropzone').addEventListener('drop',event=>{if(event.dataTransfer.files.length!==1)error('Prześlij jeden dokument naraz.');else convert(event.dataTransfer.files[0]);});
  document.querySelectorAll('[data-demo]').forEach(button=>button.addEventListener('click',async()=>{if(busy)return;try{const response=await fetch('/demo_samples/'+button.dataset.demo);if(!response.ok)throw new Error('Brak pliku demo. Uruchom generator przykładów.');const blob=await response.blob();await convert(new File([blob],button.dataset.demo,{type:blob.type}));}catch(e){error(e.message);}}));
  document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>selectTab(button.dataset.tab)));
  document.querySelector('.tabs').addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight'].includes(event.key))return;const buttons=[...document.querySelectorAll('[data-tab]')],index=buttons.findIndex(b=>b.getAttribute('aria-selected')==='true'),next=buttons[(index+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length];event.preventDefault();selectTab(next.dataset.tab);next.focus();});
  $('apply-fields').addEventListener('click',applyEdits);$('reset-file').addEventListener('click',reset);$('new-document').addEventListener('click',reset);
  $('download-json').addEventListener('click',()=>{if(!exportData)return;const blob=new Blob([JSON.stringify(exportData,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=make('a');link.href=url;link.download='formforge-coi.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Pobrano oficjalny JSON COI');});
  $('copy-json').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(JSON.stringify(exportData,null,2));toast('Skopiowano JSON');}catch{toast('Użyj przycisku Pobierz JSON');}});
  request('/api/health').then(data=>{$('server-status').textContent='';$('server-status').append(make('i'),document.createTextNode('Serwer lokalny · online'));$('server-status').title=`Python ${data.python} · OCR: ${data.ocr.available?data.ocr.languages.join(', '):'niedostępny'}`;}).catch(()=>{$('server-status').textContent='Serwer niedostępny';$('server-status').classList.add('off');});
})();
