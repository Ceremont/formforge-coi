(() => {
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  let active=null;
  function attach(view,result,url){
    const left=el('div','review-original');while(view.firstChild)left.append(view.firstChild);
    const right=el('div','review-generated'),toolbar=el('div','review-toolbar'),fields=el('div','source-field-list'),preview=el('div','source-eform-preview');preview.hidden=true;
    const toggle=el('button','secondary','Generated eForm →'),list=el('button','secondary','Wykryte pola');toolbar.append(list,toggle);right.append(toolbar,fields,preview);
    for(const field of result.form.fields){const b=el('button','source-field-item'+(field.requires_review?' uncertain':''));b.dataset.sourceField=field.id;b.append(el('strong','',field.label),el('small','',`${field.field_type} · str. ${field.source_reference.page} · score ${field.confidence.toFixed(2)}`));if(field.requires_review||field.confidence<.8)b.append(el('small','source-warning','Do sprawdzenia'));b.addEventListener('click',()=>focus(field.id));fields.append(b);}
    const detail=el('p','source-location');right.append(detail);const split=el('div','source-comparison');split.append(left,right);view.append(split);
    toggle.addEventListener('click',()=>{fields.hidden=true;preview.hidden=false;preview.replaceChildren();const frame=el('iframe','comparison-eform');frame.title='Generated eForm';preview.append(frame);const doc=frame.contentDocument;const css=doc.createElement('link');css.rel='stylesheet';css.href='/static/app.css';doc.head.append(css);doc.documentElement.lang='pl';doc.body.className='standalone-eform';window.FormForgeRender(doc.body,result.form);});
    list.addEventListener('click',()=>{fields.hidden=false;preview.hidden=true;preview.replaceChildren();});
    active={result,url,left,right,detail};
  }
  function focus(id){if(!active)return;const {result,url,left,right,detail}=active,field=result.form.fields.find(f=>f.id===id);if(!field)return;const ref=field.source_reference;
    right.querySelectorAll('[data-source-field]').forEach(b=>b.classList.toggle('selected',b.dataset.sourceField===id));
    detail.textContent=`Źródło: strona ${ref.page}${ref.cell?' · '+ref.cell:''}${ref.bbox?' · bbox '+ref.bbox.map(v=>Math.round(v)).join(', '):' · brak geometrii'} — ${ref.text}`;
    const pdf=left.querySelector('.source-pdf');if(pdf)pdf.src=url+'#page='+ref.page+'&view=FitH';
    left.querySelectorAll('.source-selected').forEach(n=>n.classList.remove('source-selected'));
    const block=[...left.querySelectorAll('[data-block-id]')].find(n=>n.dataset.blockId===ref.block_id);if(block){block.classList.add('source-selected');block.scrollIntoView({behavior:'smooth',block:'center'});}
    const image=left.querySelector('img');if(image&&ref.bbox){let wrapper=image.parentElement;if(!wrapper.classList.contains('image-map')){wrapper=el('div','image-map');image.before(wrapper);wrapper.append(image);}wrapper.querySelector('.source-region')?.remove();const region=el('span','source-region');const page=result.document.pages.find(p=>p.id===ref.page),box=ref.input_bbox||ref.bbox,tiles=result.document.analysis?.image_tiles||[],tile=tiles.find(t=>t.page===ref.page),origin=tile?.source_bbox||[0,0],width=image.naturalWidth||page.width,height=image.naturalHeight||(tiles.length?Math.max(...tiles.map(t=>t.source_bbox[3])):page.height);region.style.left=(box[0]+origin[0])/width*100+'%';region.style.top=(box[1]+origin[1])/height*100+'%';region.style.width=(box[2]-box[0])/width*100+'%';region.style.height=Math.max(.05,(box[3]-box[1])/height*100)+'%';wrapper.append(region);if(tile)region.scrollIntoView({behavior:'smooth',block:'center'});}
  }
  document.addEventListener('formforge-source',event=>{document.querySelector('[data-tab="document"]').click();focus(event.detail);});
  window.FormForgeSource={attach,focus};
})();
