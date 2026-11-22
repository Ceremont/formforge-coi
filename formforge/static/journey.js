/* Smart Workspace. One canonical editor/model; mode changes only reparent DOM. */
(() => {
  'use strict';
  const W=window.FormForgeWorkspace, $=id=>document.getElementById(id);
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const button=(text,action)=>{const n=el('button','text-button',text);n.type='button';n.addEventListener('click',action);return n;};
  let step=1,expert=false,loadedFile=null,selected=null,reviewed=false,visitedPreview=false,processing=false,resizing=false;
  const preview=$('panel-eform'),previewAnchor=document.createComment('expert preview position');preview.before(previewAnchor);
  const analysis=document.querySelector('.expert-options'),analysisAnchor=document.createComment('expert analysis position');analysis.before(analysisAnchor);
  const homeExpert=el('div');homeExpert.id='home-expert-slot';$('upload-card').before(homeExpert);
  const counted=(n,one,few,many)=>n+' '+(n===1?one:[2,3,4].includes(n%10)&&![12,13,14].includes(n%100)?few:many);
  const data=()=>W.get().result;
  const row=id=>$('fields-body').querySelector('tr[data-field-id="'+CSS.escape(id||'')+'"]');
  const field=id=>data()?.form.fields.find(f=>f.id===id);
  const internal=id=>field(id)?.id||data()?.coi_validation?.provenance?.[id]?.internal_field_id;
  const pending=f=>!f.coi?.confirmed&&(f.requires_review||f.confidence<.8||f.coi?.origin==='standard_policy');
  const diagnostics=()=>data()?.quality_review?.diagnostics||[];
  const blocking=()=>diagnostics().filter(i=>(i.severity||'').toUpperCase()==='ERROR');
  const dirty=()=>window.FormForgeUX?.isDirty()||$('apply-fields').disabled;
  const visibleFields=()=>data()?.form.fields.filter(f=>row(f.id)&&!row(f.id).dataset.deleted)||[];
  function mount(){
    const original=window.FormForgeSource.original?.()||$('source-view').querySelector('.review-original')||$('review-source-slot').querySelector('.review-original');
    if(original){if(expert){const split=$('source-view').querySelector('.source-comparison');if(split&&original.parentElement!==split)split.prepend(original);}else if(original.parentElement!==$('review-source-slot'))$('review-source-slot').replaceChildren(original);}
    if(expert){if(preview.parentNode!==previewAnchor.parentNode)previewAnchor.after(preview);}else{if(preview.parentElement!==$('citizen-preview-slot'))$('citizen-preview-slot').append(preview);preview.hidden=false;}
    if(expert&&!data())homeExpert.append(analysis);else if(analysis.parentNode!==analysisAnchor.parentNode)analysisAnchor.after(analysis);
    homeExpert.hidden=!expert||!!data();
  }
  function show(focus=false){
    const has=!!data();document.body.classList.toggle('user-mode',!expert);document.body.classList.toggle('expert-mode',expert);
    $('expert-mode').setAttribute('aria-pressed',String(expert));$('expert-mode').textContent=expert?'Wróć do trybu prostego':'Tryb ekspercki';
    $('home-screen').hidden=processing||(has&&(expert||step!==1));$('results').hidden=!has||processing||(!expert&&step===1);
    $('expert-area').hidden=!expert;$('flow-screens').hidden=expert;
    for(const [id,n]of [['step-review',2],['step-preview',3],['step-export',4]])$(id).hidden=step!==n;
    $('result-step-label').textContent=expert?'NARZĘDZIA EKSPERCKIE':'KROK '+step+' Z 4';
    for(const n of document.querySelectorAll('[data-step]')){const value=Number(n.dataset.step);n.disabled=processing||value>1&&!has;n.classList.toggle('done',value===1&&has||value===2&&reviewed||value===3&&visitedPreview);if(value===step)n.setAttribute('aria-current','step');else n.removeAttribute('aria-current');}
    mount();requestAnimationFrame(fitWorkspace);
    if(focus){window.scrollTo({top:0,behavior:'instant'});requestAnimationFrame(()=>$(step===2?'review-title':step===3?'preview-title':step===4?'export-title':'home-title').focus({preventScroll:true}));}
  }
  function fitWorkspace(){if(expert||step!==2||innerWidth<=900)return;const n=document.querySelector('.review-workspace');if(n.getBoundingClientRect().height)n.style.height=Math.max(330,innerHeight-n.getBoundingClientRect().top-92)+'px';}
  window.addEventListener('resize',fitWorkspace);
  function go(value,focus=true){if(value>1&&!data()||processing)return;step=value;show(focus);stateChanged();}
  async function navigate(value){
    if(value>=3&&dirty()&&!await window.FormForgeUX.flush()){W.error('Popraw niezastosowane zmiany przed otwarciem podglądu lub eksportu.');return;}
    setExpert(false);go(value);
  }
  function setExpert(value){expert=value;show();if(!expert&&data()){renderList();renderProperties();}if(expert&&data())W.selectTab(step===3?'eform':step===4?'json':'fields');}
  function routeTab(name){if(expert)return false;if(['fields','document'].includes(name)){go(2,false);return true;}if(name==='eform'){go(3,false);return true;}setExpert(true);return false;}
  function edit(id){setExpert(false);go(2,false);select(internal(id)||id,true);$('review-label').focus({preventScroll:true});}
  function select(id,source=true){if(!field(id))return;if(selected!==id)$('field-properties').scrollTop=0;selected=id;renderList();renderProperties();if(source)window.FormForgeSource.focus(id);}
  function renderList(){
    const root=$('review-field-list'),scroll=root.scrollTop,focused=document.activeElement?.dataset.reviewField,term=$('review-search').value.toLocaleLowerCase('pl'),filter=$('review-filter').value;
    const errors=new Set(blocking().map(i=>internal(i.field_id))),fields=visibleFields();root.replaceChildren();let count=0;
    for(const f of fields){const r=row(f.id),label=r.querySelector('.label-input').value,type=r.querySelector('.type-input').value,section=data().form.sections.find(s=>s.id===f.section)?.title;
      if(!label.toLocaleLowerCase('pl').includes(term)||filter==='pending'&&!pending(f)||filter==='errors'&&!errors.has(f.id))continue;
      count++;const n=el('button','review-choice');n.type='button';n.dataset.reviewField=f.id;n.tabIndex=f.id===selected?0:-1;n.setAttribute('aria-pressed',String(f.id===selected));n.append(el('strong','',label||'Pole bez nazwy'),el('span','',(W.typeLabels[type]||type)+(section?' · '+section:'')));
      if(errors.has(f.id))n.append(el('span','error-mark','Wymaga poprawy'));else if(pending(f))n.append(el('span','pending-mark','Do potwierdzenia'));else if(f.coi?.confirmed)n.append(el('span','','Potwierdzone przez Ciebie'));
      n.addEventListener('click',()=>select(f.id));root.append(n);
    }
    if(!root.querySelector('button[tabindex="0"]'))root.querySelector('button')?.setAttribute('tabindex','0');if(focused)root.querySelector('[data-review-field="'+CSS.escape(focused)+'"]')?.focus({preventScroll:true});
    root.scrollTop=scroll;$('review-list-count').textContent='Pokazano '+count+' z '+fields.length+' pól';
  }
  function renderProperties(){
    const f=field(selected),r=row(selected),exists=!!f&&!!r&&!r.dataset.deleted;$('field-properties').hidden=!exists;$('review-empty').hidden=exists;
    if(!exists)return;
    $('review-position').textContent='POLE '+(visibleFields().findIndex(x=>x.id===selected)+1)+' Z '+visibleFields().length+' · '+(data().form.sections.find(s=>s.id===f.section)?.title||'');
    $('review-field-heading').textContent=r.querySelector('.label-input').value||'Pole bez nazwy';
    const origin=$('review-origin');origin.classList.toggle('standard',f.coi?.origin==='standard_policy');
    origin.textContent=f.coi?.origin==='standard_policy'?'Pole dodane na podstawie standardu COI, a nie bezpośrednio odczytane z dokumentu.':f.coi?.origin==='manual'?'Pole dodane lub skonfigurowane ręcznie. Sprawdź jego zgodność ze źródłem.':'Pole rozpoznane w dokumencie. Porównaj etykietę i rodzaj odpowiedzi ze źródłem.';
    for(const [id,cls]of [['review-label','label-input'],['review-type','type-input'],['review-options','options-editor']]){
      const input=$(id),actual=r.querySelector('.'+cls);if(id==='review-type'&&!input.options.length)for(const option of actual.options)input.append(option.cloneNode(true));
      if(document.activeElement!==input)input.value=actual.value;
    }
    $('review-required').checked=r.querySelector('.required-input').checked;$('review-confirm').checked=r.querySelector('.confirm-input').checked;
    $('review-confirm').closest('label').classList.toggle('confirmed',!!f.coi?.confirmed&&!dirty());
    const choice=['radio','select'].includes(r.querySelector('.type-input').value);$('review-options').hidden=!choice;$('review-options-label').hidden=!choice;
    const ref=f.source_reference,source=f.coi?.origin==='standard_policy'?'Uzupełnienie standardu: porównaj jego sens z formularzem. Nie przypisujemy mu bezpośrednio odczytanego fragmentu.':ref.block_id==='manual'?'Dodane ręcznie — wskaż i sprawdź odpowiednie miejsce w oryginale.':'Strona '+ref.page+(ref.cell?' · komórka '+ref.cell:'')+' · '+ref.text;
    $('review-source-description').textContent=source;$('review-source').disabled=ref.block_id==='manual';
    const problems=$('review-problems');problems.replaceChildren();const items=diagnostics().filter(i=>internal(i.field_id)===f.id&&i.code!=='requires_review'&&(i.severity||'').toUpperCase()!=='INFO');
    for(const i of items){const n=el('div','field-problem'+((i.severity||'').toUpperCase()==='ERROR'?' blocking':''));n.append(el('strong','',i.message),el('p','',i.recommendation||'Porównaj ze źródłem i popraw właściwości.'));problems.append(n);}
    if(pending(f)&&!items.length){const n=el('div','field-problem');n.append(el('strong','','Sprawdź właściwości tego pola'),el('p','',f.coi?.origin==='standard_policy'?'Potwierdź, czy to uzupełnienie jest potrzebne. Popraw je lub usuń, jeżeli nie pasuje do formularza.':'Automatyczne rozpoznanie wymaga przeglądu. Porównaj nazwę, typ i obowiązkowość z dokumentem.'));problems.append(n);}
  }
  function proxy(id,selector,kind){$(id).addEventListener(kind||'input',()=>{const r=row(selected);if(!r)return;const actual=r.querySelector(selector);if(actual.type==='checkbox')actual.checked=$(id).checked;else actual.value=$(id).value;actual.dispatchEvent(new Event(kind||'input',{bubbles:true}));renderList();renderProperties();});}
  function groupedMessages(){
    const result=data(),groups={errors:new Map(),confirm:new Map(),info:new Map()};
    const add=(bucket,key,record)=>{if(!groups[bucket].has(key))groups[bucket].set(key,[]);groups[bucket].get(key).push(record);};
    for(const issue of diagnostics()){
      const f=field(internal(issue.field_id));
      if(issue.code==='requires_review'&&f&&pending(f))continue;
      const info=(issue.severity||'').toUpperCase()==='INFO'||['import_unverified','dictionary_values_remote','proposed_dictionary'].includes(issue.code)||issue.code==='requires_review'&&f?.coi?.confirmed;
      add((issue.severity||'').toUpperCase()==='ERROR'?'errors':info?'info':'confirm',issue.code,{...issue,internal_id:f?.id});
    }
    for(const f of result.form.fields.filter(pending))add('confirm',f.coi?.origin==='standard_policy'?'standard_confirmation':'source_confirmation',{field_id:f.id,internal_id:f.id,message:f.coi?.origin==='standard_policy'?'Pole dodane na podstawie standardu COI, a nie bezpośrednio odczytane z dokumentu.':'Sprawdź nazwę, typ i reguły rozpoznanego pola.',recommendation:'Porównaj ze źródłem. Popraw pole, usuń je albo zaznacz świadome potwierdzenie jego właściwości.'});
    const names={standard_confirmation:'Uzupełnienia standardu COI',source_confirmation:'Pola wymagające sprawdzenia',dictionary_values_remote:'Wartości słowników są dostępne na platformie COI',proposed_dictionary:'Lokalne propozycje słowników',import_unverified:'Import do rzeczywistej platformy nie został sprawdzony',requires_review:'Pierwotny wynik rozpoznania',source_warning:'Uwagi dotyczące odczytu dokumentu'};
    const root=$('review-messages');root.replaceChildren();let total=0;
    for(const [key,title]of [['errors','Wymaga poprawy'],['confirm','Wymaga potwierdzenia'],['info','Informacje']]){
      const section=el('section','message-category');section.dataset.messageCategory=key;section.append(el('h3','',title));
      if(!groups[key].size)section.append(el('p','muted small','Brak uwag w tej kategorii.'));
      for(const [code,items]of groups[key]){total+=items.length;const details=el('details','message-group'),name=names[code]||items[0].message;details.append(el('summary','',name+' ('+items.length+')'));
        details.append(el('p','',items[0].message),el('p','',items[0].recommendation||'Sprawdź źródło i wskazany element. Szczegółowe kody i ścieżki są dostępne w trybie eksperckim.'));
        if(code==='requires_review'&&key==='info')details.append(el('p','','Ręczne potwierdzenie nie zmienia pierwotnego wyniku heurystyki. Uwaga techniczna pozostaje w diagnostyce.'));
        const list=el('ul');for(const item of items){const li=el('li'),f=field(item.internal_id);li.append(el('span','',f?.label||item.message));if(f)li.append(button('Sprawdź pole',()=>edit(f.id)));list.append(li);}details.append(list);section.append(details);
      }
      root.append(section);
    }
    $('review-messages-summary').textContent='Uwagi · wymaga poprawy: '+counted(groups.errors.size,'grupa','grupy','grup')+' · do potwierdzenia: '+counted(groups.confirm.size,'grupa','grupy','grup')+' · informacje: '+counted(groups.info.size,'grupa','grupy','grup');
  }
  function exportSummary(){
    const r=data();if(!r)return;const c=r.coi_validation||{},root=$('export-checks');root.replaceChildren();
    for(const [title,good,note]of [['Schemat JSON',c.schema_valid,'Kontrola struktury pliku według schematu organizatora.'],['Lokalne reguły techniczne',c.business_rules_valid&&c.compatibility_profile_valid,'Sprawdzone lokalnie: strony, sekcje, identyfikatory i powiązania.'],['Przegląd treści',null,'Porównaj dokument z polami. Kontrole techniczne nie potwierdzają kompletności rozpoznania.'],['Import do COI',null,'Nie został sprawdzony na rzeczywistej platformie. Plik nie jest oznaczony jako gotowy do publikacji.']]){
      const card=el('div','export-check'+(good===true?' good':good===false?' error':''));card.append(el('span','check-symbol',good===true?'✓':good===false?'!':'i'));const content=el('div');content.append(el('h3','',title),el('p','',good===false?'Wykryto błędy. Popraw wskazane elementy przed użyciem pliku. '+note:note));card.append(content);root.append(card);
    }
    const n=r.form.fields.filter(pending).length,e=blocking().length,attention=$('export-attention');attention.replaceChildren();attention.append(el('strong','',e?'Konfiguracja wymaga poprawy':'Sprawdź wynik przed użyciem na platformie'),el('p','',e?e+' zgłoszeń błędów blokuje zwykły eksport. Możesz wrócić do edycji albo pobrać wyraźnie oznaczony szkic.':n?'Do potwierdzenia: '+counted(n,'pole','pola','pól')+'. Pobranie pliku nie oznacza ich zatwierdzenia.':'Nie ma pól oznaczonych jako oczekujące na potwierdzenie. Nadal sprawdź kompletność i zachowanie importera.'));
    const unsupported=r.quality_review?.unsupported_features||[];if(unsupported.length)attention.append(el('p','','Nieobsługiwane elementy: '+counted(unsupported.length,'cecha','cechy','cech')+'. Nie wszystkie reguły modelu są reprezentowane w JSON. Przejrzyj uwagi przed użyciem konfiguracji.'));
    if(!c.valid&&!e)attention.append(el('p','','Kontrole konfiguracji nie zakończyły się wynikiem poprawnym. Sprawdź szczegółową diagnostykę.'));
    attention.append(button('Wróć do pól i uwag',()=>{go(2);$('review-messages-container').open=true;}));
    $('simple-download-draft').hidden=!e&&!!c.valid;$('simple-download-draft').disabled=dirty();
  }
  function expertMetrics(){
    const r=data(),m=r?.quality_review?.metrics;if(!m)return;$('layer-metrics')?.remove();const details=el('details','layer-metrics');details.id='layer-metrics';details.append(el('summary','','Co oznaczają liczby? Dokument, model i eksport COI'));
    const table=el('table','layer-metrics-table'),head=el('tr');for(const s of ['Warstwa','Strony','Sekcje','Pola / komponenty wejściowe','Użyte słowniki'])head.append(el('th','',s));table.append(head);
    for(const values of [['Dokument / surowe wykrycie',r.document.pages.length,r.detected_form?.sections?.length??'—',r.detected_form?.fields?.filter(f=>f.field_type!=='information').length??'—','—'],['Model po uzupełnieniach',m.model.pages,m.model.sections,m.model.input_fields,m.model.dictionaries_used],['Eksport COI',m.export.pages,m.export.sections,m.export.input_components,m.export.dictionaries_used]]){const tr=el('tr');values.forEach(v=>tr.append(el('td','',String(v))));table.append(tr);}details.append(table);
    const d=m.dependencies;for(const [name,value]of [['Warunki wykryte w źródle',d.source],['Warunki dodane przez standard COI',d.standard_policy],['Warunki skonfigurowane ręcznie',d.manual],['Warunki bez potwierdzonego pochodzenia',d.unverified],['Stany w eksportowanej konfiguracji (wszystkie poziomy)',d.exported_states]])details.append(el('p','',name+': '+(value??'nie oceniono')));
    details.append(el('p','',Object.entries(d.exported_by_type).map(([k,v])=>k+': '+v).join(' · ')||'Brak stanów dynamicznych.'),el('p','','Warunki modelu są pojedynczymi porównaniami, także w sekcjach i wyrażeniach COI. Pochodzenie wynika z dowodu reguły, znacznika polityki COI lub deklaracji w modelu; brak dowodu starszej reguły jest oznaczony osobno. Jeden stan JSON może łączyć kilka warunków. Liczba stron eksportu obejmuje FINISH; elementy informacyjne nie są polami wejściowymi. Definicje katalogu nie oznaczają użytych słowników.'));
    $('overview-view').append(details);
  }
  function stateChanged(){
    if(!data()||loadedFile!==W.get().sourceFile)return;
    if(window.FormForgeUX?.isDirty()){reviewed=false;visitedPreview=false;}
    const wait=dirty(),errors=blocking().length,p=data().form.fields.filter(pending).length;
    $('review-save-state').textContent=wait?'Zmiany czekają na sprawdzenie…':'Zmiany sprawdzone i zapisane w pamięci tej karty.';
    $('review-continue').disabled=!!errors||wait;
    $('review-continue-note').textContent=errors?'Popraw wskazane błędy. Uwagi i potwierdzenia są opisane przy polach.':p?'Do potwierdzenia: '+counted(p,'pole','pola','pól')+'. Możesz testować formularz; ten krok nie potwierdzi ich automatycznie.':'Przejdź do testu. Sprawdź kompletność dokumentu również wtedy, gdy nie ma ostrzeżeń.';
    const status=$('review-status');status.replaceChildren();if(wait)status.append(el('span','','Sprawdzamy zmiany. Liczby poniżej dotyczą ostatniego sprawdzonego wyniku.'));
    if(errors)status.append(el('span','blocking-count','Wymaga poprawy: '+counted(errors,'zgłoszenie','zgłoszenia','zgłoszeń')));status.append(el('span','attention-count',counted(p,'pole','pola','pól')+' do potwierdzenia'),el('span','',counted(visibleFields().length,'element','elementy','elementów')+' formularza · '+counted(data().document.pages.length,'strona źródłowa','strony źródłowe','stron źródłowych')),button('Zobacz uwagi',()=>{$('review-messages-container').open=true;$('review-messages').scrollIntoView({block:'nearest',behavior:'smooth'});}));
    const trigger=status.querySelector('button');trigger.setAttribute('aria-controls','review-messages-container');trigger.setAttribute('aria-expanded',String($('review-messages-container').open));
    $('simple-download-draft').disabled=wait;
  }
  function render(result){
    if(loadedFile!==W.get().sourceFile){loadedFile=W.get().sourceFile;selected=result.form.fields.find(f=>f.field_type!=='information')?.id||result.form.fields[0]?.id;reviewed=false;visitedPreview=false;step=2;$('review-search').value='';$('review-filter').value='all';}
    if(!visibleFields().some(f=>f.id===selected))selected=visibleFields()[0]?.id;
    $('review-source-kind').textContent=result.document.format==='pdf'?'Oryginalny PDF · lokalny render':['png','jpg','jpeg','jpe'].includes(result.document.format)?'Oryginalny obraz':'Odtworzony tekst i komórki · bez oryginalnego składu';
    mount();renderList();renderProperties();groupedMessages();exportSummary();expertMetrics();show();stateChanged();
  }
  function loaded(){processing=false;expert=false;go(2);$('completed-stages').replaceChildren(...[...$('stages').children].map(n=>n.cloneNode(true)));$('completed-elapsed').textContent=$('processing-elapsed').textContent;}
  $('review-messages-container').addEventListener('toggle',()=>{$('review-status').querySelector('button')?.setAttribute('aria-expanded',String($('review-messages-container').open));});
  document.querySelector('.product-header .brand').addEventListener('click',event=>{event.preventDefault();navigate(1);});
  $('expert-mode').addEventListener('click',()=>setExpert(!expert));
  for(const n of document.querySelectorAll('[data-step]'))n.addEventListener('click',()=>navigate(Number(n.dataset.step)));
  for(const [id,selector,kind]of [['review-label','.label-input','input'],['review-type','.type-input','change'],['review-required','.required-input','change'],['review-options','.options-editor','input'],['review-confirm','.confirm-input','change']])proxy(id,selector,kind);
  $('review-search').addEventListener('input',renderList);$('review-filter').addEventListener('change',renderList);
  $('review-field-list').addEventListener('keydown',event=>{if(!['ArrowDown','ArrowUp','Home','End'].includes(event.key))return;const buttons=[...$('review-field-list').querySelectorAll('button')],i=buttons.findIndex(b=>b.dataset.reviewField===selected);if(!buttons.length)return;event.preventDefault();const target=buttons[event.key==='Home'?0:event.key==='End'?buttons.length-1:Math.max(0,Math.min(buttons.length-1,i+(event.key==='ArrowDown'?1:-1)))];select(target.dataset.reviewField);$('review-field-list').querySelector('[data-review-field="'+CSS.escape(target.dataset.reviewField)+'"]')?.focus({preventScroll:true});});
  $('review-source').addEventListener('click',()=>window.FormForgeSource.focus(selected));
  $('review-add').addEventListener('click',()=>{$('add-field').click();selected=data().form.fields.at(-1)?.id;renderList();renderProperties();$('review-label').focus();$('review-label').select();});
  $('review-delete').addEventListener('click',()=>{row(selected)?.querySelector('.delete-field').click();selected=visibleFields()[0]?.id;renderList();renderProperties();});
  $('review-advanced').addEventListener('click',()=>{setExpert(true);W.selectTab('fields');window.FormForgeUX.jump(selected);});
  $('review-continue').addEventListener('click',async()=>{if(await window.FormForgeUX.flush()&&!blocking().length){reviewed=true;go(3);}else{W.error('Popraw wskazane błędy przed przejściem do testu.');}});
  $('preview-back').addEventListener('click',()=>go(2));$('preview-continue').addEventListener('click',()=>{visitedPreview=true;navigate(4);});$('export-back').addEventListener('click',()=>go(3));
  $('expert-export').addEventListener('click',()=>navigate(4));
  $('simple-download-draft').addEventListener('click',()=>$('download-draft').click());$('export-expert').addEventListener('click',()=>{setExpert(true);W.selectTab('json');});
  $('how-it-works').addEventListener('click',e=>{e.stopPropagation();$('help-dialog').showModal();});
  document.addEventListener('formforge-field-selected',e=>{if(!expert&&field(e.detail)){selected=e.detail;renderList();renderProperties();}});
  document.addEventListener('formforge-reset',()=>{loadedFile=null;selected=null;step=1;reviewed=false;visitedPreview=false;processing=false;$('review-source-slot').replaceChildren();$('review-field-list').replaceChildren();$('review-messages').replaceChildren();$('review-messages-container').open=false;$('completed-stages').replaceChildren();setTimeout(()=>show(),0);});
  document.addEventListener('formforge-processing',e=>{processing=e.detail.active;if(processing){$('home-screen').hidden=true;$('results').hidden=true;for(const b of document.querySelectorAll('[data-step],#expert-mode'))b.disabled=true;}else{$('expert-mode').disabled=false;show();}});
  const divider=$('workspace-divider'),workspace=document.querySelector('.review-workspace');
  function setWidth(value){const n=Math.max(30,Math.min(70,value));workspace.style.setProperty('--source-width',n+'fr');workspace.style.setProperty('--editor-width',(100-n)+'fr');divider.setAttribute('aria-valuenow',String(Math.round(n)));}
  divider.addEventListener('pointerdown',e=>{if(e.button!==0)return;resizing=true;workspace.classList.add('resizing');divider.setPointerCapture(e.pointerId);e.preventDefault();});
  divider.addEventListener('pointermove',e=>{if(!resizing)return;const rect=workspace.getBoundingClientRect();setWidth((e.clientX-rect.left)/rect.width*100);});
  for(const name of ['pointerup','pointercancel','lostpointercapture'])divider.addEventListener(name,()=>{resizing=false;workspace.classList.remove('resizing');});
  divider.addEventListener('keydown',e=>{const n=Number(divider.getAttribute('aria-valuenow'));if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();setWidth(e.key==='Home'?30:e.key==='End'?70:n+(e.key==='ArrowLeft'?-2:2));}});
  window.FormForgeJourney={render,loaded,stateChanged,routeTab,edit,go,isExpert:()=>expert};show();
})();
