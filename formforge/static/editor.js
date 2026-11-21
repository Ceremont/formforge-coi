/* Extends the existing editor. Drafts live only in the current browser tab. */
(() => {
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const input=(cls,value,label)=>{const n=el('input',cls);n.value=value??'';n.setAttribute('aria-label',label);return n;};
  const jsonInput=(cls,value,label)=>{const n=el('textarea',cls);n.value=JSON.stringify(value||[],null,2);n.setAttribute('aria-label',label);return n;};
  const select=(cls,values,current,label)=>{const n=el('select',cls);n.setAttribute('aria-label',label);for(const [id,title]of values){const o=el('option','',title);o.value=id;n.append(o);}n.value=current??'';return n;};
  function decorate(row,field,form){
    const details=el('details','advanced-field');details.append(el('summary','','Reguły, sekcja, grupa i źródło'));for(const reason of field.decision_reasons||[])details.append(el('p','muted small',window.FormForgeUX?.reason(reason,field)||'Reguła rozpoznania: '+field.detection_method));
    const rules=jsonInput('validation-input',field.validation,'Reguły walidacji JSON');rules.dataset.original=rules.value;row.dataset.originalType=field.field_type;
    details.append(el('label','','Walidacja (JSON)'),rules,el('label','','Sekcja'),select('section-input',form.sections.map(s=>[s.id,s.title]),field.section,'Sekcja pola'));
    const group=form.groups?.find(g=>g.id===field.group_id);
    details.append(el('label','','Grupa (ta sama nazwa łączy pola; pusta rozdziela)'),input('group-input',group?.title||'','Nazwa grupy'),el('label','','Kolejność'),input('order-input',field.order,'Kolejność pola'));
    const repeat=input('repeat-input','','Sekcja powtarzalna');repeat.type='checkbox';repeat.checked=!!group?.repeat_key;const repeatLabel=el('label','','Grupa jest sekcją powtarzalną ');repeatLabel.append(repeat);details.append(repeatLabel);
    const dicts=[...(form.dictionaries||[])];if(field.dictionary&&!dicts.some(d=>d.id===field.dictionary.id))dicts.push(field.dictionary);
    details.append(el('label','','Słownik'),select('dictionary-input',[['','Bez słownika'],...dicts.map(d=>[d.id,(d.title||d.id)+' · '+({official:'oficjalny',document:'z dokumentu',proposed:'proponowany',registered:'lokalny'}[d.source]||'lokalny')])],field.dictionary?.id||'','Słownik pola'));
    details.append(el('label','','Warunki widoczności (JSON)'),jsonInput('conditions-input',field.conditions,'Warunki widoczności JSON'),el('label','','Warunkowa obowiązkowość (JSON)'),jsonInput('required-conditions-input',field.required_conditions,'Warunkowa obowiązkowość JSON'));
    details.append(el('label','','Opis / treść zgody'),input('help-input',field.help_text,'Opis lub treść zgody'),el('label','','Właściwości COI (JSON: powiązania, słownik, warunki, dane inicjalne)'),jsonInput('coi-input',field.coi||{origin:'manual'},'Właściwości COI JSON'));
    const confirm=input('confirm-input','','Potwierdzam właściwości pola');confirm.type='checkbox';confirm.checked=!!field.coi?.confirmed;const confirmLabel=el('label','','Potwierdzam właściwości tego pola ');confirmLabel.append(confirm);details.append(confirmLabel);
    const remove=el('button','secondary delete-field','Usuń błędne pole');remove.type='button';remove.addEventListener('click',()=>{row.dataset.deleted='true';row.hidden=true;document.dispatchEvent(new CustomEvent('formforge-draft'));});details.append(remove);
    row.cells[0].append(details);
    const source=el('button','source-link','Pokaż źródło ↗');source.type='button';source.addEventListener('click',()=>document.dispatchEvent(new CustomEvent('formforge-source',{detail:field.id})));row.cells[3].append(source);
  }
  function read(form,body){
    const next=structuredClone(form),deleted=new Set(),groupByName=new Map();
    for(const row of body.querySelectorAll('tr[data-field-id]')){
      const field=next.fields.find(f=>f.id===row.dataset.fieldId);if(row.dataset.deleted){deleted.add(field.id);continue;}
      field.label=row.querySelector('.label-input').value.trim();if(!field.label)throw Error('Etykieta pola nie może być pusta.');
      const type=row.querySelector('.type-input').value,rules=row.querySelector('.validation-input');field.field_type=type;
      field.validation=type!==row.dataset.originalType&&rules.value===rules.dataset.original?(['pesel','nip','regon','email','phone','postal_code','date'].includes(type)?[{kind:type,value:null,message:null}]:[]):JSON.parse(rules.value);
      field.required=row.querySelector('.required-input').checked;if(!field.required)field.validation=field.validation.filter(r=>r.kind!=='required');
      field.coi=JSON.parse(row.querySelector('.coi-input').value);field.coi.confirmed=row.querySelector('.confirm-input').checked;field.help_text=row.querySelector('.help-input').value;
      if(field.coi.confirmed)field.requires_review=false;
      field.section=row.querySelector('.section-input').value;field.page=next.sections.find(s=>s.id===field.section).page;
      field.conditions=JSON.parse(row.querySelector('.conditions-input').value);field.required_conditions=JSON.parse(row.querySelector('.required-conditions-input').value);
      field.order=Number(row.querySelector('.order-input').value);if(!Number.isInteger(field.order)||field.order<0)throw Error('Kolejność musi być nieujemną liczbą całkowitą.');
      field.options=['radio','select'].includes(type)?row.querySelector('.options-editor').value.split('|').map(s=>s.trim()).filter(Boolean):[];
      const dictId=row.querySelector('.dictionary-input').value;
      const previousDict=field.dictionary?.id||'';
      field.dictionary=structuredClone(next.dictionaries.find(d=>d.id===dictId)||window.FormForgeOfficialCatalog?.find(d=>d.id===dictId)||(field.dictionary?.id===dictId?field.dictionary:null));
      if(field.dictionary&&!next.dictionaries.some(d=>d.id===field.dictionary.id))next.dictionaries.push(structuredClone(field.dictionary));
      if(previousDict!==dictId){field.coi.dictionary_name=field.dictionary?.source==='official'?dictId:null;field.coi.default_value=null;if(field.coi.default_value_type){field.coi.default_value_type=null;field.coi.read_only=false;}field.coi.confirmed=false;field.requires_review=true;if(field.coi.dictionary_name)field.field_type='select';}
      if(field.dictionary){if(field.dictionary.source!=='official')field.options=[...field.dictionary.values];}
      else if(field.options.length)field.dictionary={id:'dict_'+field.id,source:'proposed',title:field.label,values:field.options,aliases:[]};
      const name=row.querySelector('.group-input').value.trim();field.group_id=null;
      if(name){const key=field.section+'|'+name;if(!groupByName.has(key))groupByName.set(key,structuredClone(next.groups.find(g=>g.section===field.section&&g.title===name)||{id:'g_'+crypto.randomUUID().replaceAll('-','').slice(0,12),title:name,section:field.section,parent_id:null,repeat_key:null}));const group=groupByName.get(key);group.repeat_key=row.querySelector('.repeat-input').checked?(group.repeat_key||group.id):null;field.group_id=group.id;}
    }
    next.fields=next.fields.filter(f=>!deleted.has(f.id)).sort((a,b)=>a.order-b.order);next.fields.forEach((f,i)=>{f.order=i;f.conditions=f.conditions.filter(c=>!deleted.has(c.field_id));f.required_conditions=f.required_conditions.filter(c=>!deleted.has(c.field_id));});
    next.groups=[...groupByName.values()];for(let i=0;i<next.groups.length;i++){const parent=form.groups.find(g=>g.id===next.groups[i].parent_id);if(parent&&!next.groups.some(g=>g.id===parent.id))next.groups.push(structuredClone(parent));}for(const key of deleted)delete next.initial_data[key];
    for(const section of next.sections){const node=document.querySelector('[data-section-rules="'+section.id+'"]');if(node)section.conditions=JSON.parse(node.value);section.conditions=section.conditions.filter(c=>!deleted.has(c.field_id));}
    for(const section of next.sections){const node=document.querySelector('[data-section-coi="'+section.id+'"]');if(node)section.coi=JSON.parse(node.value);}
    const referencesDeleted=rule=>rule&&(deleted.has(rule.field_id)||(rule.rules||[]).some(referencesDeleted));
    for(const node of [...next.fields,...next.sections]){if(referencesDeleted(node.coi?.show_when)||referencesDeleted(node.coi?.read_only_when))throw Error('Usuwane pole steruje warunkiem COI. Najpierw popraw warunek w polu lub sekcji zależnej.');}
    return next;
  }
  function mount(form,body,rerender){
    let tools=document.getElementById('editor-tools');if(!tools){tools=el('div','editor-tools');tools.id='editor-tools';body.closest('.table-scroll').before(tools);}tools.replaceChildren();
    const add=el('button','secondary','+ Dodaj pominięte pole');add.id='add-field';add.addEventListener('click',()=>{try{Object.assign(form,read(form,body));const section=form.sections[0],id='f_manual_'+crypto.randomUUID().replaceAll('-','').slice(0,12);form.fields.push({id,label:'Nowe pole',field_type:'text',required:false,order:form.fields.length,page:section.page,section:section.id,validation:[],source_reference:{page:section.page,block_id:'manual',text:'Dodane ręcznie przez użytkownika',bbox:null,label_bbox:null,input_bbox:null,sheet:null,cell:null},confidence:1,detection_method:'manual',decision_reasons:['Dodane ręcznie przez użytkownika'],options:[],conditions:[],required_conditions:[],dictionary:null,requires_review:true,help_text:'',group_id:null,coi:{origin:'manual',confirmed:false}});rerender();}catch(e){const box=document.getElementById('error-banner');box.textContent=e.message;box.hidden=false;}});tools.append(add,el('span','muted small','Score to wynik heurystyki, nie prawdopodobieństwo poprawności.'));
    const advanced=el('details','editor-section-rules');advanced.append(el('summary','','Warunki sekcji i nowy słownik'));
    for(const section of form.sections){const textarea=jsonInput('section-conditions',section.conditions,'Widoczność sekcji '+section.title);textarea.dataset.sectionRules=section.id;const coi=jsonInput('section-coi',section.coi||{},'Właściwości COI sekcji '+section.title);coi.dataset.sectionCoi=section.id;advanced.append(el('label','',section.title),textarea,coi);}
    const title=input('dictionary-title','','Nazwa nowego słownika'),values=input('dictionary-values','','Wartości nowego słownika');title.placeholder='Nazwa słownika';values.placeholder='Wartość 1 | Wartość 2';
    const addDict=el('button','secondary','Dodaj proponowany słownik');addDict.addEventListener('click',()=>{try{const name=title.value.trim(),options=values.value.split('|').map(s=>s.trim()).filter(Boolean);if(!name||!options.length)throw Error('Podaj nazwę i wartości słownika.');Object.assign(form,read(form,body));form.dictionaries.push({id:'proposed_'+crypto.randomUUID().replaceAll('-','').slice(0,12),title:name,source:'proposed',values:options,aliases:[]});rerender();}catch(e){const box=document.getElementById('error-banner');box.textContent=e.message;box.hidden=false;}});advanced.append(title,values,addDict);tools.append(advanced);
  }
  window.FormForgeEditor={decorate,read,mount};
})();
