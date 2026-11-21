/* Professional workspace over the existing API/editor. No storage or remote assets. */
(() => {
  'use strict';
  const W=window.FormForgeWorkspace,$=id=>document.getElementById(id);
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  let dirty=false,revision=0,timer=null,applying=false,committed=null,loadedFile=null,undo=[],redo=[];
  let query='',filter='all',compact=false,processingTimer=null,processingStart=0;
  const clone=x=>structuredClone(x),model=()=>W.get().result?.form;
  const button=(text,action,cls='secondary')=>{const b=el('button',cls,text);b.type='button';b.addEventListener('click',action);return b;};
  function fieldId(id){const r=W.get().result;return r?.form.fields.find(f=>f.id===id)?.id||r?.coi_validation?.provenance?.[id]?.internal_field_id;}
  function jump(id){const actual=fieldId(id);W.selectTab('fields');filter='all';query='';filters();const row=actual&&document.querySelector('[data-field-id="'+CSS.escape(actual)+'"]');if(row){row.hidden=false;row.querySelector('details').open=true;row.scrollIntoView({block:'center',behavior:'smooth'});row.querySelector('.label-input').focus({preventScroll:true});}}
  function toggleStale(){
    $('draft-banner').hidden=!dirty;
    for(const name of ['json','eform','overview','coi','structure'])$('panel-'+name)?.setAttribute('data-stale',String(dirty));
    const r=W.get().result;
    $('download-json').disabled=dirty||applying||!r?.coi_validation?.valid||r?.issues?.some(i=>i.severity==='error');
    $('json-validate').disabled=dirty||applying||!r;
    $('download-draft').disabled=dirty||applying||!r;
    $('undo-edit')?.toggleAttribute('disabled',dirty||applying||!undo.length);
    $('redo-edit')?.toggleAttribute('disabled',dirty||applying||!redo.length);
  }
  function draft(){if(!model())return;dirty=true;revision++;toggleStale();clearTimeout(timer);timer=setTimeout(()=>apply({silent:true}),1100);$('save-status').textContent='Zmiany oczekują na walidację…';}
  function focusSnapshot(){const node=document.activeElement,row=node?.closest('[data-field-id]');return row?{id:row.dataset.fieldId,cls:node.classList[0],start:node.selectionStart,end:node.selectionEnd,open:[...document.querySelectorAll('.advanced-field[open]')].map(n=>n.closest('tr').dataset.fieldId)}:null;}
  function restoreFocus(s){if(!s)return;for(const id of s.open)document.querySelector('[data-field-id="'+CSS.escape(id)+'"] details')?.setAttribute('open','');const node=document.querySelector('[data-field-id="'+CSS.escape(s.id)+'"] .'+CSS.escape(s.cls||'label-input'));if(node){node.focus({preventScroll:true});if(s.start!==null&&typeof node.setSelectionRange==='function'&&['text','search'].includes(node.type))node.setSelectionRange(s.start,s.end);}}
  async function apply(options={}){
    if(applying||!model())return;
    clearTimeout(timer);let next;
    try{next=options.snapshot?clone(options.snapshot):window.FormForgeEditor.read(clone(model()),$('fields-body'));}
    catch(error){dirty=true;toggleStale();W.error('Niepoprawna edycja: '+error.message);return;}
    const sent=revision,focus=focusSnapshot();applying=true;$('apply-fields').disabled=true;toggleStale();
    try{
      const checked=await W.request('/api/v1/forms/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({form:next})});
      if(sent!==revision&&!options.snapshot){timer=setTimeout(()=>apply({silent:true}),150);return;}
      if(options.history==='undo'){redo.push(clone(committed));undo.pop();}
      else if(options.history==='redo'){undo.push(clone(committed));redo.pop();}
      else if(committed&&JSON.stringify(committed)!==JSON.stringify(checked.form)){undo.push(clone(committed));if(undo.length>10)undo.shift();redo=[];}
      committed=clone(checked.form);dirty=false;$('error-banner').hidden=true;W.replace(checked);restoreFocus(focus);
      $('save-status').textContent='Zapisano zmiany w pamięci karty. JSON i podgląd zostały odświeżone.';
      if(!options.silent)W.toast('Zaktualizowano formularz i JSON');
    }catch(error){dirty=true;W.error(error.message);$('save-status').textContent='Zmiany nie zostały zastosowane. Popraw wskazane błędy.';}
    finally{applying=false;$('apply-fields').disabled=false;toggleStale();}
  }
  function overview(result){
    const root=$('overview-view');root.replaceChildren();const form=result.form,q=result.quality_review||{},counts=q.counts||{};
    const head=el('div','overview-head'),text=el('div');text.append(el('h3','','Sprawdź wynik przed eksportem'),el('p','','Lokalne kontrole oceniają konfigurację. Porównaj źródło z polami — poprawny JSON nie dowodzi kompletności rozpoznania.'));
    head.append(text,el('span','status-label'+(counts.error?' error':''),counts.error?'Wykryto błędy':result.quality?.status==='no_fields'?'Nie wykryto pól':result.quality?.status==='partial'?'Wynik częściowy':'Wymaga przeglądu'));root.append(head);
    const grid=el('div','overview-grid');
    for(const [value,label]of [[counts.error||0,'błędów'],[counts.warning||0,'ostrzeżeń'],[counts.dependencies||0,'zależności'],[new Set(form.fields.map(f=>f.coi?.dictionary_name||f.dictionary?.id).filter(Boolean)).size,'użytych słowników']]){const n=el('div','overview-metric');n.append(el('strong','',String(value)),el('span','',label));grid.append(n);}root.append(grid);
    const checks=el('div','overview-checks');
    for(const [title,good,info]of [['JSON Schema',result.coi_validation?.schema_valid,'Schemat przekazany przez organizatora'],['Reguły techniczne',result.coi_validation?.business_rules_valid,'Strony, sekcje, powiązania i układ'],['Profil rekurencyjny',result.coi_validation?.compatibility_profile_valid,'Kontrole uzupełniające ograniczoną schemę'],['Importer COI',false,'Import na rzeczywistej platformie nie został sprawdzony']]){const card=el('div','check-card');card.append(el('span','check-mark',good?'✓':'—'));const content=el('div');content.append(el('strong','',title),el('p','',(good?'Kontrola lokalna poprawna. ':'')+info));card.append(content);checks.append(card);}root.append(checks);
    const actions=el('div','overview-actions');actions.append(button('Porównaj ze źródłem',()=>W.selectTab('document'),'primary'),button('Otwórz edytor',()=>W.selectTab('fields')),button('Sprawdź zgodność',()=>W.selectTab('coi')));root.append(actions);
    const pending=form.fields.filter(f=>f.requires_review||f.confidence<.8);const list=el('div','review-list');list.append(el('h3','','Najpierw sprawdź te pola'));
    if(!pending.length)list.append(el('p','muted','Brak pól oznaczonych niskim wskaźnikiem. Nadal sprawdź kompletność dokumentu i uzupełnienia standardu.'));
    for(const field of pending.slice(0,6)){const row=el('div','review-item');row.append(el('span','',field.label),button('Sprawdź pole',()=>jump(field.id)));list.append(row);}root.append(list);
  }
  function filters(){
    if(!model())return;
    let root=$('final-editor-controls');if(!root){root=el('div','editor-controls');root.id='final-editor-controls';$('fields-body').closest('.table-scroll').before(root);}
    if(!root.children.length){
      const search=el('input');search.type='search';search.placeholder='Szukaj pola';search.setAttribute('aria-label','Szukaj w wykrytych polach');search.id='field-search';search.value=query;search.addEventListener('input',()=>{query=search.value;filterRows();});
      const mode=el('select');mode.id='field-filter';mode.setAttribute('aria-label','Filtr pól');for(const [key,label]of [['all','Wszystkie'],['review','Wymagają weryfikacji'],['error','Błędy'],['warning','Ostrzeżenia']]){const o=el('option','',label);o.value=key;mode.append(o);}mode.value=filter;mode.addEventListener('change',()=>{filter=mode.value;filterRows();});
      const un=button('Cofnij',()=>apply({snapshot:undo.at(-1),history:'undo'}));un.id='undo-edit';const re=button('Ponów',()=>apply({snapshot:redo.at(-1),history:'redo'}));re.id='redo-edit';
      const count=el('span','editor-filter-status');count.id='editor-filter-count';count.setAttribute('role','status');root.append(search,mode,un,re,count);
    }else{$('field-search').value=query;$('field-filter').value=filter;}
    filterRows();conditionTools();sectionTools(root);catalogOptions();toggleStale();
  }
  function filterRows(){
    const r=W.get().result;if(!r)return;const diagnostics=[...(r.issues||[]),...(r.quality_review?.diagnostics||[])];let visible=0,total=0;
    for(const row of $('fields-body').querySelectorAll('tr[data-field-id]')){const f=r.form.fields.find(f=>f.id===row.dataset.fieldId);if(!f)continue;const problem=diagnostics.filter(i=>fieldId(i.field_id)===f.id),error=problem.some(i=>i.severity.toLowerCase()==='error'),warning=problem.some(i=>i.severity.toLowerCase()==='warning'),review=f.requires_review||f.confidence<.8||Object.values(r.coi_validation?.provenance||{}).some(p=>p.internal_field_id===f.id&&p.requires_confirmation);const match=filter==='all'||filter==='review'&&review||filter==='error'&&error||filter==='warning'&&warning;row.hidden=!!row.dataset.deleted||!match||!row.querySelector('.label-input').value.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl'));if(!row.dataset.deleted)total++;if(!row.hidden)visible++;row.dataset.severity=error?'error':warning?'warning':'info';}
    if($('editor-filter-count'))$('editor-filter-count').textContent='Wyświetlono '+visible+' z '+total+' pól';
  }
  function conditionTools(){
    for(const row of $('fields-body').querySelectorAll('tr[data-field-id]')){
      if(row.querySelector('.condition-builder'))continue;
      const form=model(),id=row.dataset.fieldId,box=el('div','condition-builder');box.append(el('strong','','Dodaj zależność bez pisania JSON'));
      const source=el('select');source.setAttribute('aria-label','Pole sterujące zależnością');for(const f of form.fields.filter(f=>f.id!==id)){const o=el('option','',f.label);o.value=f.id;source.append(o);}
      const operator=el('select');operator.setAttribute('aria-label','Operator zależności');for(const [value,title]of [['equals','Jest równe'],['not_equals','Jest różne']]){const o=el('option','',title);o.value=value;operator.append(o);}
      const value=el('input');value.setAttribute('aria-label','Wartość warunku');value.placeholder='Wartość lub true / false';const target=el('select');target.setAttribute('aria-label','Działanie zależności');for(const [key,title]of [['show','Pokaż pole'],['require','Wymagaj pola']]){const o=el('option','',title);o.value=key;target.append(o);}
      const hints=el('p');const update=()=>{const parent=form.fields.find(f=>f.id===source.value);hints.textContent=parent?.field_type==='checkbox'?'Pojedyncze pole wyboru: wpisz true albo false.':'Wartości źródła: '+(parent?.options?.join(', ')||'wpisz dokładną wartość');};source.addEventListener('change',update);update();
      box.append(source,operator,value,target,hints,button('Dodaj regułę',()=>{try{const parent=form.fields.find(f=>f.id===source.value);if(!parent||!value.value.trim())throw Error('Wybierz pole i podaj wartość.');let answer=value.value;if(parent.field_type==='checkbox'){if(!['true','false'].includes(answer))throw Error('Dla pola logicznego użyj true albo false.');answer=answer==='true';}const input=row.querySelector(target.value==='require'?'.required-conditions-input':'.conditions-input'),rules=JSON.parse(input.value);rules.push({field_id:parent.id,operator:operator.value,value:answer,action:target.value,evidence:'Reguła dodana ręcznie przez użytkownika',requires_review:true});input.value=JSON.stringify(rules,null,2);draft();}catch(error){W.error(error.message);}}));row.querySelector('.advanced-field').append(box);
    }
  }
  function sectionTools(root){
    root.querySelector('.section-manager')?.remove();const form=model(),details=el('details','section-manager');details.append(el('summary','','Sekcje i kolejność stron formularza'));
    const tabs=[...new Set([...form.sections].sort((a,b)=>a.order-b.order).map(s=>s.coi?.tab||form.pages.find(p=>p.id===s.page)?.title||'Dane'))];
    const reorder=(title,delta)=>{try{const next=window.FormForgeEditor.read(clone(form),$('fields-body')),order=[...tabs],i=order.indexOf(title),j=i+delta;if(j<0||j>=order.length)return;[order[i],order[j]]=[order[j],order[i]];next.sections.sort((a,b)=>order.indexOf(a.coi?.tab||next.pages.find(p=>p.id===a.page)?.title)-order.indexOf(b.coi?.tab||next.pages.find(p=>p.id===b.page)?.title)||a.order-b.order);next.sections.forEach((s,i)=>s.order=i);Object.assign(form,next);W.renderFields();draft();filters();}catch(error){W.error(error.message);}};
    for(const title of tabs){const row=el('div','section-row');row.append(el('span','','Strona COI: '+title),button('↑',()=>reorder(title,-1)),button('↓',()=>reorder(title,1)));row.querySelectorAll('button').forEach((b,i)=>b.setAttribute('aria-label',(i?'Przesuń stronę w dół: ':'Przesuń stronę w górę: ')+title));details.append(row);}
    for(const section of form.sections){const row=el('div','section-row'),title=el('input');title.value=section.title;title.setAttribute('aria-label','Nazwa sekcji '+section.title);title.addEventListener('change',()=>{if(title.value.trim()){section.title=title.value.trim();draft();}});row.append(title);details.append(row);}
    const title=el('input');title.placeholder='Nazwa nowej sekcji';title.setAttribute('aria-label','Nazwa nowej sekcji');const tab=el('input');tab.placeholder='Strona COI (opcjonalnie)';tab.setAttribute('aria-label','Strona nowej sekcji');
    details.append(title,tab,button('Dodaj sekcję',()=>{if(!title.value.trim()){W.error('Podaj nazwę sekcji.');return;}try{Object.assign(form,window.FormForgeEditor.read(clone(form),$('fields-body')));form.sections.push({id:'s_manual_'+crypto.randomUUID().slice(0,8),title:title.value.trim(),page:form.pages[0].id,order:form.sections.length,instructions:[],conditions:[],coi:{origin:'manual',confirmed:false,tab:tab.value.trim()||tabs[0]||'Dane'}});W.renderFields();draft();filters();}catch(error){W.error(error.message);}}));root.append(details);
  }
  let catalogPromise=null;
  function catalogOptions(){
    if(!catalogPromise)catalogPromise=W.request('/api/v1/dictionaries').then(data=>window.FormForgeOfficialCatalog=data.items).catch(()=>[]);
    catalogPromise.then(items=>{if(!model())return;for(const select of $('fields-body').querySelectorAll('.dictionary-input')){const current=select.value;for(const entry of items){if([...select.options].some(o=>o.value===entry.id))continue;const o=el('option','',entry.title+' · oficjalny katalog');o.value=entry.id;select.append(o);}select.value=current;}});
  }
  function renderJSON(){
    const root=$('json-view'),data=W.get().exportData;root.replaceChildren();if(!data)return;const text=JSON.stringify(data,null,compact?0:2),term=$('json-search').value.toLocaleLowerCase('pl');let count=0;
    const append=(parent,value)=>{if(!term){parent.append(document.createTextNode(value));return;}let offset=0,index;while((index=value.toLocaleLowerCase('pl').indexOf(term,offset))!==-1){parent.append(document.createTextNode(value.slice(offset,index)),el('mark','',value.slice(index,index+term.length)));count++;offset=index+term.length;}parent.append(document.createTextNode(value.slice(offset)));};
    const regex=/("(?:\\.|[^"\\])*"\s*:|"(?:\\.|[^"\\])*"|-?\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b|\btrue\b|\bfalse\b|\bnull\b)/gi;let cursor=0;
    for(const match of text.matchAll(regex)){append(root,text.slice(cursor,match.index));const token=match[0],span=el('span',token.endsWith(':')?'json-key':token.startsWith('"')?'json-string':token==='null'?'json-null':/^(true|false)$/.test(token)?'json-boolean':'json-number');append(span,token);root.append(span);cursor=match.index+token.length;}append(root,text.slice(cursor));$('json-match-count').textContent=term?count+' dopasowań':'';
  }
  function render(result){
    if(loadedFile!==W.get().sourceFile){loadedFile=W.get().sourceFile;committed=clone(result.form);undo=[];redo=[];dirty=false;revision=0;clearTimeout(timer);}
    overview(result);filters();renderJSON();toggleStale();
  }
  function reason(text,field){
    if(/[ąćęłńóśźż]/i.test(text)||text.startsWith('Reguła')||text.startsWith('Dodane ręcznie'))return text;
    if(text.startsWith('Semantic type:'))return 'Typ określony na podstawie etykiety i kontekstu źródła.';
    if(text.includes('Explicit answer marker'))return 'W źródle wykryto jawne miejsce na odpowiedź.';
    if(text.includes('Native form control'))return 'Pole pochodzi z rozpoznanej kontrolki dokumentu.';
    if(text.includes('Spatial label'))return 'Etykietę połączono z miejscem odpowiedzi na podstawie położenia.';
    if(text.includes('dictionary'))return 'Zaproponowano słownik na podstawie dopasowania opisu; potwierdź jego użycie.';
    if(text.includes('repeat'))return 'W źródle rozpoznano wskazówkę powtarzania grupy; potwierdź jej zakres.';
    return 'Zastosowano regułę analizy źródła ('+field.detection_method+'); szczegóły techniczne pozostają w modelu JSON.';
  }
  document.addEventListener('input',event=>{if(event.target.closest('#fields-body,#editor-tools')&&!event.target.closest('.condition-builder'))draft();});
  document.addEventListener('change',event=>{if(event.target.closest('#fields-body,#editor-tools')&&!event.target.closest('.condition-builder'))draft();});
  document.addEventListener('formforge-draft',draft);
  document.addEventListener('formforge-edit',event=>jump(event.detail));
  document.addEventListener('formforge-reset',()=>{clearTimeout(timer);dirty=false;committed=null;loadedFile=null;undo=[];redo=[];query='';filter='all';$('final-editor-controls')?.remove();$('editor-tools')?.remove();for(const id of ['fields-body','structure-view','json-view','validation-view','coi-view','overview-view'])$(id).replaceChildren();});
  document.addEventListener('formforge-processing',event=>{clearInterval(processingTimer);$('processing-elapsed').textContent='';if(event.detail.active){processingStart=performance.now();$('process-file').textContent=event.detail.file.name+' · '+(event.detail.file.size/1024).toFixed(1)+' KB';$('process-note').textContent='Serwer analizuje dokument. Szczegółowe etapy i ich czasy pojawią się po zakończeniu — bez szacowanego procentu postępu.';processingTimer=setInterval(()=>$('processing-elapsed').textContent='Czas przetwarzania: '+((performance.now()-processingStart)/1000).toFixed(1)+' s',100);}else $('processing-elapsed').textContent='Czas oczekiwania: '+((performance.now()-processingStart)/1000).toFixed(1)+' s';});
  $('discard-edits').addEventListener('click',()=>{clearTimeout(timer);revision++;dirty=false;if(committed){const current=W.get().result;W.replace({form:clone(committed),issues:current.issues,coi_validation:current.coi_validation,quality_review:current.quality_review,export:W.get().exportData});}toggleStale();});
  $('cancel-processing').addEventListener('click',W.cancel);
  $('try-example').addEventListener('click',event=>{event.stopPropagation();document.querySelector('.demo-grid').scrollIntoView({behavior:'smooth',block:'center'});document.querySelector('[data-demo]').focus({preventScroll:true});});
  $('open-help').addEventListener('click',()=>$('help-dialog').showModal());$('close-help').addEventListener('click',()=>$('help-dialog').close());
  $('json-search').addEventListener('input',renderJSON);$('json-format').addEventListener('click',()=>{compact=!compact;$('json-format').textContent=compact?'Sformatuj JSON':'Widok zwarty';renderJSON();});
  $('json-validate').addEventListener('click',async()=>{try{const r=await W.request('/api/v1/forms/coi-validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(W.get().exportData)});$('json-validation').textContent=r.valid?'Schemat i lokalne reguły techniczne są poprawne. Sprawdź również semantykę pól i ostrzeżenia; importer COI nie został zweryfikowany.':'JSON zawiera błędy: '+(r.errors||[]).map(i=>i.message).join(' ');}catch(error){$('json-validation').textContent=error.message;}});
  $('download-draft').addEventListener('click',()=>{if(dirty||!W.get().exportData)return;const blob=new Blob([JSON.stringify(W.get().exportData,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='formforge-coi-szkic.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);W.toast('Pobrano szkic. Rozwiąż wskazane problemy przed użyciem na platformie.');});
  window.FormForgeUX={render,apply,draft,isDirty:()=>dirty,reason,jump};
})();
