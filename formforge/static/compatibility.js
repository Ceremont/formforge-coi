/* Render server diagnostics as text. The conversion result is never executable. */
(() => {
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  window.FormForgeCompatibility=(root,result)=>{
    root.replaceChildren();const r=result.coi_validation||{};
    const row=(title,value,good)=>{const n=el('div','issue '+(good?'info':'warning'));n.append(el('strong','',title),el('p','',value));root.append(n);};
    if(result.quality)row('Jakość odczytu',result.quality.status+' · '+result.quality.message,false);
    row('JSON Schema organizatora',r.schema_valid?'Poprawny':'Błędy schematu',r.schema_valid);
    row('Rekurencyjny profil zgodności',r.compatibility_profile_valid?'Poprawny':'Niepoprawny',r.compatibility_profile_valid);
    row('Reguły techniczne i biznesowe',r.business_rules_valid?'Poprawne':'Wykryto błędy',r.business_rules_valid);
    const errors=r.errors||[],warnings=r.warnings||[];
    row('Nieprawidłowe powiązania',String(errors.filter(e=>/link|flow|unreachable|jsonata.*reference/.test(e.code)).length),!errors.some(e=>/link|flow|unreachable|jsonata.*reference/.test(e.code)));
    row('Nieprawidłowe sekcje',String(errors.filter(e=>/section|finish|outside/.test(e.code)).length),!errors.some(e=>/section|finish|outside/.test(e.code)));
    row('Brakujące pola','Automatyczna walidacja nie potwierdza kompletności odczytu. Porównaj źródło z polami; pominięte dane dodaj w edytorze.',false);
    if(result.normalization?.suppressed?.length){const details=el('details');details.append(el('summary','',`Pominięte lub zastąpione kandydaty źródłowe (${result.normalization.suppressed.length})`));for(const field of result.normalization.suppressed)details.append(el('p','',field.label+' · '+field.reason));root.append(details);}
    row('Nieobsługiwane cechy',String((r.unsupported_features||[]).length),(r.unsupported_features||[]).length===0);
    const provenance=Object.values(r.provenance||{}), pending=provenance.filter(p=>p.requires_confirmation);
    row('Automatyczne ustalenia',`${provenance.filter(p=>p.origin==='source').length} pól ze źródła · ${provenance.filter(p=>p.origin==='standard_policy').length} uzupełnień standardu · ${pending.length} wymaga potwierdzenia`,!pending.length);
    row('Import na platformie COI',r.target_import_verified?'Zweryfikowany':'Nieprzeprowadzony. Poprawność konfiguracji nie potwierdza działania docelowego importera.',!!r.target_import_verified);
    for(const issue of [...(r.schema_errors||[]).map(e=>({...e,code:'schema'})),...errors,...warnings,...(r.review_items||[])]){
      const node=el('div','issue '+(issue.severity||'warning'));node.append(el('strong','',issue.code),el('p','',issue.message),el('small','',issue.path||issue.field_id||''));root.append(node);
    }
    const details=el('details');details.append(el('summary','',`Pola wymagające potwierdzenia (${pending.length})`));
    for(const p of pending){const field=result.form.fields.find(f=>f.id===p.internal_field_id);details.append(el('p','',`${field?.label||p.internal_field_id}: ${p.policy_rule||p.origin}`));}
    root.append(details);
  };
})();
