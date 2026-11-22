/* Local compliance diagnostics with explicit scope and editor navigation. */
(() => {
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  window.FormForgeCompatibility=(root,result)=>{
    root.replaceChildren();const r=result.coi_validation||{},q=result.quality_review||{},errors=r.errors||[];
    const cards=el('div','compliance-summary');
    const card=(title,value,level)=>{const node=el('div','compliance-item '+level);node.append(el('strong','',title),el('span','',value));cards.append(node);};
    card('JSON Schema organizatora',r.schema_valid?'Kontrola lokalna poprawna':'Błędy schematu',r.schema_valid?'good':'error');
    card('Reguły techniczne',r.business_rules_valid?'Kontrola lokalna poprawna':'Wykryto błędy',r.business_rules_valid?'good':'error');
    card('Profil rekurencyjny',r.compatibility_profile_valid?'Kontrola lokalna poprawna':'Niepoprawny profil',r.compatibility_profile_valid?'good':'error');
    const invalidLinks=errors.filter(i=>/link|flow|unreachable|reference|cycle/.test(i.code)),invalidSections=errors.filter(i=>/section|finish|grid|outside/.test(i.code));
    card('Powiązania między polami',invalidLinks.length+' nieprawidłowych powiązań',invalidLinks.length?'error':'good');
    card('Struktura formularza',invalidSections.length+' błędów sekcji, stron i układu',invalidSections.length?'error':'good');
    card('Walidatory',result.form.fields.reduce((n,f)=>n+f.validation.length,0)+' reguł w modelu','good');
    const dictionaries=new Set(result.form.fields.map(f=>f.coi?.dictionary_name||f.dictionary?.id).filter(Boolean));
    card('Słowniki',dictionaries.size+' użytych; pełne oficjalne wartości nie są lokalnie dostępne','warning');
    const deps=q.metrics?.dependencies;
    card('Warunki wykryte w źródle',deps?String(deps.source)+' porównań':'Nie oceniono','good');
    card('Warunki dodane przez standard COI',deps?String(deps.standard_policy)+' porównań':'Nie oceniono','warning');
    card('Stany w eksportowanym JSON',deps?.exported_states!=null?String(deps.exported_states)+' stanów na wszystkich poziomach; '+Object.entries(deps.exported_by_type).map(([k,v])=>k+': '+v).join(', '):'Nie oceniono','good');
    card('Warunki ręczne / nieobsługiwane cechy',(deps?.manual??'—')+' ręcznych porównań; '+(r.unsupported_features||[]).length+' nieobsługiwanych cech',(r.unsupported_features||[]).length?'warning':'good');
    card('Porównanie z referencją','Nie jest wykonywane w runtime dla nowego źródła; wyniki par 01/05 są w benchmarku.','warning');
    card('Import na platformie COI','Nieprzeprowadzony. Poprawność lokalna nie potwierdza importu.','warning');
    root.append(cards);
    const provenance=Object.values(r.provenance||{}),pending=provenance.filter(p=>p.requires_confirmation);
    root.append(el('p','compliance-note',provenance.filter(p=>p.origin==='source').length+' pól ze źródła · '+provenance.filter(p=>p.origin==='standard_policy').length+' uzupełnień standardu · '+pending.length+' wymaga potwierdzenia.'));
    root.append(el('p','compliance-note','Brakujące pola: nie znamy pełnego oczekiwanego formularza dla nowego dokumentu. Porównaj źródło z edytorem i dodaj pominięte elementy.'));
    let diagnostics=q.diagnostics;
    if(!diagnostics)diagnostics=[...(result.issues||[]),...errors,...(r.warnings||[]),...(r.review_items||[])].map(i=>({...i,severity:(i.severity||'warning').toUpperCase()}));
    const ordered=[...diagnostics].sort((a,b)=>['ERROR','WARNING','INFO'].indexOf(a.severity)-['ERROR','WARNING','INFO'].indexOf(b.severity));
    for(const issue of ordered){
      const severity=(issue.severity||'WARNING').toLowerCase(),node=el('div','diagnostic '+severity),body=el('div','diagnostic-content');
      const internal=result.form.fields.find(f=>f.id===issue.field_id)?issue.field_id:r.provenance?.[issue.field_id]?.internal_field_id,field=result.form.fields.find(f=>f.id===internal);
      node.append(el('span','level',{error:'BŁĄD',warning:'OSTRZEŻENIE',info:'INFORMACJA'}[severity]||'INFORMACJA'));
      body.append(el('strong','',issue.message),el('p','',field?'Pole: '+field.label:issue.path?'Lokalizacja: '+(Array.isArray(issue.path)?issue.path.join('/'):issue.path):'Dotyczy formularza'),el('p','',issue.recommendation||'Sprawdź źródło, popraw konfigurację w edytorze i ponów walidację.'));
      const code=el('small','muted',issue.code||'');body.append(code);node.append(body);
      const jump=el('button','secondary',field?'Otwórz pole':'Otwórz edytor');jump.addEventListener('click',()=>document.dispatchEvent(new CustomEvent('formforge-edit',{detail:internal})));node.append(jump);root.append(node);
    }
    if(result.normalization?.suppressed?.length){const details=el('details','compliance-note');details.append(el('summary','','Pominięte lub zastąpione kandydaty źródłowe: '+result.normalization.suppressed.length));for(const field of result.normalization.suppressed)details.append(el('p','',field.label));root.append(details);}
    const details=el('details','compliance-note');details.append(el('summary','','Pola wymagające potwierdzenia ('+pending.length+')'));for(const p of pending){const field=result.form.fields.find(f=>f.id===p.internal_field_id);details.append(el('p','',field?.label||p.internal_field_id));}root.append(details);
  };
})();
