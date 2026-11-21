/* Data-driven renderer. No eval, remote assets, or persisted citizen values. */
(() => {
  'use strict';
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  function expression(rule, values, byId, active) {
    if (!rule) return true;
    if (rule.op==='and') return rule.rules.every(r=>expression(r,values,byId,active));
    if (rule.op==='or') return rule.rules.some(r=>expression(r,values,byId,active));
    const parent=byId[rule.field_id];
    if(!parent||!visible(parent,values,byId,active))return false;
    const value=values[parent.id]??'';
    const equal=Array.isArray(value)?value.includes(rule.value):value===rule.value;
    return rule.op==='not_equals'?!equal:equal;
  }
  function visible(field, values, byId, active = new Set()) {
    if (active.has(field.id)) return false;
    const next = new Set(active); next.add(field.id);
    return expression(field.coi?.show_when,values,byId,next) && expression(field.sectionCoi?.show_when,values,byId,next) && (field.conditions||[]).every(c => {
      const parent = byId[c.field_id];
      if (!parent || !visible(parent, values, byId, next)) return false;
      const value = values[parent.id] ?? (parent.field_type === 'checkbox' ? false : '');
      return c.operator === 'equals' ? value === c.value : value !== c.value;
    });
  }
  function pesel(value) {
    if (!/^[0-9]{11}$/.test(value)) return false;
    const weights = [1,3,7,9,1,3,7,9,1,3];
    if ((10 - weights.reduce((sum, w, i) => sum + w * Number(value[i]), 0) % 10) % 10 !== Number(value[10])) return false;
    const yy=Number(value.slice(0,2)), mm=Number(value.slice(2,4)), dd=Number(value.slice(4,6));
    const century=[1900,2000,2100,2200,1800][Math.floor(mm/20)];
    if (!century) return false;
    const date=new Date(Date.UTC(century+yy, mm%20-1, dd));
    return date.getUTCFullYear()===century+yy && date.getUTCMonth()===mm%20-1 && date.getUTCDate()===dd;
  }
  window.FormForgeRender = function(container, model, official) {
    container.replaceChildren();
    const shell=el('div','eform-shell'); container.append(shell);
    shell.append(el('h2','eform-title',model.title), el('p','eform-subtitle','* Pola wymagane · Dane służą wyłącznie do testowania podglądu.'));
    const form=el('form'); form.noValidate=true; shell.append(form);
    const viewFields=[...model.fields];
    const sectionById=Object.fromEntries(model.sections.map(s=>[s.id,s]));
    const byId=Object.fromEntries(model.fields.map(f=>[f.id,{...f,sectionCoi:sectionById[f.section].coi,conditions:[...f.conditions,...(sectionById[f.section].conditions||[])]}]));
    const wrappers={}, controls={}, errors={}, sectionWrappers={};
    const getValues=()=>Object.fromEntries(viewFields.map(f=> {
      const list=controls[f.id]||[];
      const value=['checkbox','consent'].includes(f.field_type) ? !!list[0]?.checked : f.field_type==='radio' ? list.find(n=>n.checked)?.value||'' : f.field_type==='attachment' ? list[0]?.files?.[0]?.name||'' : list[0]?.value||'';
      return [f.id,value];
    }));
    for (const section of [...model.sections].sort((a,b)=>a.order-b.order)) {
      const group=el('fieldset','eform-section'); group.append(el('legend','',section.title));
      sectionWrappers[section.id]=group;
      section.instructions.forEach(text=>group.append(el('p','eform-help',text)));
      for (const field of model.fields.filter(f=>f.section===section.id).sort((a,b)=>a.order-b.order)) {
        const row=el('div','eform-field'); row.dataset.fieldId=field.id; wrappers[field.id]=row;
        const labelText=field.label+(field.required?' *':'');
        const required=field.required||field.validation.some(r=>r.kind==='required');
        const addInput = input => {
          input.name=field.id; input.dataset.required=required?'true':'false'; input.required=required;
          input.setAttribute('aria-describedby',field.id+'_error'); (controls[field.id]??=[]).push(input); return input;
        };
        if (field.field_type==='information') {
          row.append(el('p','eform-help',field.help_text||field.label));
        } else if (['checkbox','consent'].includes(field.field_type)) {
          const label=el('label','eform-option'); const input=addInput(el('input')); input.type='checkbox'; input.id=field.id; label.append(input,document.createTextNode(labelText)); row.append(label);
        } else if (field.field_type==='radio') {
          row.append(el('span','',labelText));
          for (const option of field.options) { const label=el('label','eform-option'); const input=addInput(el('input')); input.type='radio'; input.value=option; label.append(input,document.createTextNode(option)); row.append(label); }
        } else {
          const label=el('label','',labelText); label.htmlFor=field.id; row.append(label);
          let input;
          if (field.field_type==='textarea') input=el('textarea');
          else if (field.field_type==='select') { input=el('select'); const empty=el('option','','Wybierz…'); empty.value=''; input.append(empty); for (const option of field.options) { const item=el('option','',option); item.value=option; input.append(item); } }
          else { input=el('input'); input.type=({number:'number',date:'date',email:'email',phone:'tel',attachment:'file'})[field.field_type]||'text'; if (field.field_type==='number') input.step='any'; }
          input.id=field.id; addInput(input);
          for (const rule of field.validation) { if (rule.kind==='min_length') input.minLength=Number(rule.value); if (rule.kind==='max_length') input.maxLength=Number(rule.value); if (rule.kind==='min') input.min=rule.value; if (rule.kind==='max') input.max=rule.value; }
          if (field.field_type==='postal_code') { input.pattern='[0-9]{2}-[0-9]{3}'; input.placeholder='00-000'; }
          if (field.field_type==='pesel') input.inputMode='numeric';
          if (field.field_type==='attachment') input.title='Załącznik jest wybierany wyłącznie lokalnie; nie jest przesyłany.';
          row.append(input);
        }
        if(field.field_type==='consent') row.append(el('p','eform-help',field.help_text));
        if(field.coi?.dictionary_name)row.append(el('p','eform-help','Słownik COI: '+field.coi.dictionary_name+'. Pełne wartości udostępnia platforma COI; lokalny podgląd zawiera tylko wartości jawnie podane w dokumencie.'));
        if(field.coi?.default_value_type==='EXTERNAL_SYSTEM')row.append(el('p','eform-help','Dane inicjalne: '+field.coi.default_value+'. Rejestr nie jest podłączony w lokalnym podglądzie.'));
        const error=el('p','eform-error'); error.id=field.id+'_error'; error.setAttribute('role','alert'); errors[field.id]=error; row.append(error);
        if(field.group_id){const definition=(model.groups||[]).find(g=>g.id===field.group_id);if(definition)row.prepend(el('p','eform-group-title',definition.title));}
        group.append(row);
        if(Object.hasOwn(model.initial_data||{},field.id)){for(const input of controls[field.id]||[]){const value=model.initial_data[field.id];if(input.type==='checkbox')input.checked=value===true;else if(input.type==='radio')input.checked=input.value===String(value);else if(input.type!=='file')input.value=String(value);}}
        else if(field.coi?.default_value!=null&&!field.coi.default_value_type){for(const input of controls[field.id]||[]){const value=Array.isArray(field.coi.default_value)?field.coi.default_value[0]:field.coi.default_value;if(input.type==='radio')input.checked=input.value===String(value);else if(input.type!=='file')input.value=String(value);}}
      }
      form.append(group);
    }
    // Page navigation changes visibility only; entered values and File objects stay in the DOM.
    const nav=el('div','eform-navigation'), previous=el('button','secondary','← Wstecz'), next=el('button','secondary','Dalej →'), selector=el('select');
    previous.type=next.type='button';selector.setAttribute('aria-label','Strona e-formularza');
    const tabs=[...new Set([...model.sections].sort((a,b)=>a.order-b.order).map(s=>s.coi?.tab||'Strona '+s.page))];
    for(const value of ['Wszystkie strony',...tabs,'FINISH']){const option=el('option','',value==='FINISH'?'Zakończenie (FINISH)':value);option.value=value;selector.append(option);}
    nav.append(previous,selector,next);form.before(nav);
    const finish=el('section','eform-finish');finish.hidden=true;finish.append(el('h3','','Zakończenie'),el('p','','To lokalny podgląd strony INFO_SECTION. Wniosek nie został wysłany.'));
    const finishTab=official?.tabs?.find(t=>t.type==='FINISH');
    if(finishTab)for(const question of finishTab.questions||[])if(question.field?.type==='INFO_SECTION')finish.append(el('p','',question.field.label||question.field.description||''));
    form.after(finish);
    function navigate(){const value=selector.value;form.hidden=value==='FINISH';finish.hidden=value!=='FINISH';previous.disabled=selector.selectedIndex===0;next.disabled=selector.selectedIndex===selector.options.length-1;refresh();}
    selector.addEventListener('change',navigate);previous.addEventListener('click',()=>{selector.selectedIndex--;navigate();});next.addEventListener('click',()=>{selector.selectedIndex++;navigate();});
    // Repeating instances are local test data, never new source fields in the export.
    for(const definition of (model.groups||[]).filter(g=>g.repeat_key)){
      const members=model.fields.filter(f=>f.group_id===definition.id);if(!members.length)continue;
      const host=el('div','eform-repeat'), base=el('div','eform-repeat-instance');wrappers[members[0].id].before(host);host.append(el('h4','',definition.title),el('p','eform-help','Powtarzanie w lokalnym podglądzie · maksymalnie 20 wierszy.'));
      for(const field of members)base.append(wrappers[field.id]);host.append(base);
      const add=el('button','secondary','Dodaj wiersz');add.type='button';host.append(add);let serial=0,count=1;
      add.addEventListener('click',()=>{
        if(count>=20)return;serial++;count++;const instance=el('div','eform-repeat-instance'), ids=Object.fromEntries(members.map((f,i)=>[f.id,'repeat_'+definition.id.replace(/[^a-zA-Z0-9_]/g,'').slice(0,35)+'_'+serial+'_'+i]));
        const remap=value=>{if(Array.isArray(value))return value.map(remap);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,k==='field_id'?(ids[v]||v):remap(v)]));return value;};
        for(const original of members){const field=remap(JSON.parse(JSON.stringify(original)));field.id=ids[original.id];viewFields.push(field);byId[field.id]={...field,sectionCoi:sectionById[field.section].coi,conditions:[...field.conditions,...(sectionById[field.section].conditions||[])]};
          const row=wrappers[original.id].cloneNode(true);row.dataset.fieldId=field.id;row.querySelector('.eform-group-title')?.remove();wrappers[field.id]=row;controls[field.id]=[...row.querySelectorAll('input,select,textarea')];
          for(const input of controls[field.id]){input.name=field.id;if(input.id)input.id=field.id;input.setAttribute('aria-describedby',field.id+'_error');if(['radio','checkbox'].includes(input.type))input.checked=false;else input.value='';}
          for(const label of row.querySelectorAll('label[for]'))label.htmlFor=field.id;const error=row.querySelector('.eform-error');error.id=field.id+'_error';error.textContent='';errors[field.id]=error;instance.append(row);
        }
        const remove=el('button','secondary','Usuń wiersz');remove.type='button';remove.addEventListener('click',()=>{for(const id of Object.values(ids)){viewFields.splice(viewFields.findIndex(f=>f.id===id),1);delete byId[id];delete wrappers[id];delete controls[id];delete errors[id];}instance.remove();count--;add.disabled=false;refresh();});instance.append(remove);add.before(instance);add.disabled=count>=20;refresh();
      });
    }
    const submitRow=el('div','eform-submit'); const submit=el('button','primary','Sprawdź formularz →'); submit.type='submit'; submitRow.append(submit); form.append(submitRow);
    const status=el('p'); status.setAttribute('role','status'); form.append(status);
    function refresh() {
      const values=getValues();
      for (const field of viewFields) {
        const show=visible(byId[field.id],values,byId); wrappers[field.id].hidden=!show;
        const conditional=(field.required_conditions||[]).length&&visible({...field,conditions:field.required_conditions},values,byId);
        const locked=field.coi?.read_only||field.coi?.default_value_type==='EXTERNAL_SYSTEM'||(field.coi?.read_only_when&&expression(field.coi.read_only_when,values,byId,new Set()));
        for (const input of controls[field.id]||[]) { input.disabled=!show||!!locked; input.required=show&&!locked&&(input.dataset.required==='true'||!!conditional); }
        if (!show) errors[field.id].textContent='';
      }
      for(const section of model.sections){sectionWrappers[section.id].hidden=(selector.value!=='Wszystkie strony'&&selector.value!==(section.coi?.tab||'Strona '+section.page))||!visible({id:'section_'+section.id,conditions:section.conditions,coi:section.coi},values,byId);}
    }
    form.addEventListener('input',refresh); form.addEventListener('change',refresh); navigate();
    form.addEventListener('submit',event=> {
      event.preventDefault(); const values=getValues(); let good=true; status.textContent=''; status.className='';
      for (const field of viewFields) {
        errors[field.id].textContent=''; if(wrappers[field.id].hidden) continue;
        const input=(controls[field.id]||[])[0]; if (!input) continue;
        if(field.coi?.default_value_type==='EXTERNAL_SYSTEM'&&(field.required||field.validation.some(r=>r.kind==='required'))&&!values[field.id]){errors[field.id].textContent='Wymagane dane rejestrowe nie są dostępne w lokalnym podglądzie.';good=false;continue;} input.setCustomValidity('');
        if (field.field_type==='pesel'&&values[field.id]&&!pesel(values[field.id])) input.setCustomValidity('Nieprawidłowy PESEL (suma kontrolna lub data urodzenia).');
        if (!input.checkValidity()) { errors[field.id].textContent=input.validationMessage; good=false; }
      }
      if (!good) { status.textContent='Popraw oznaczone pola.'; status.className='eform-error'; return; }
      const report=issues=> {
        if (issues.length) { issues.forEach(i=>{if(errors[i.field_id]) errors[i.field_id].textContent=i.message;}); status.textContent='Popraw oznaczone pola.'; status.className='eform-error'; }
        else { status.textContent='Dane są poprawne. Podgląd nie zapisuje ani nie wysyła wniosku do urzędu.'; status.className='eform-success'; }
      };
      if (window.FormForgeValidate) { submit.disabled=true; window.FormForgeValidate({...model,fields:viewFields},values).then(report).catch(error=>{status.textContent=error.message;status.className='eform-error';}).finally(()=>submit.disabled=false); }
      else report([]);
    });
  };
  document.addEventListener('DOMContentLoaded',()=> {
    const embedded=document.getElementById('form-model');
    if (embedded) window.FormForgeRender(document.getElementById('eform-root'),JSON.parse(embedded.textContent));
  });
})();
