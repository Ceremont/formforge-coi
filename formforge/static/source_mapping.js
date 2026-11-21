(() => {
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  let active=null,cachedFile=null;const pageCache=new Map(),requests=new Set();
  function attach(view,result,url){
    const left=el('div','review-original');while(view.firstChild)left.append(view.firstChild);
    const right=el('div','review-generated'),toolbar=el('div','review-toolbar'),fields=el('div','source-field-list'),preview=el('div','source-eform-preview');preview.hidden=true;
    const toggle=el('button','secondary','Podgląd e-formularza →'),list=el('button','secondary','Wykryte pola');toolbar.append(list,toggle);right.append(toolbar,fields,preview);
    for(const field of result.form.fields){const b=el('button','source-field-item'+(field.requires_review?' uncertain':''));b.dataset.sourceField=field.id;b.append(el('strong','',field.label),el('small','',`${field.field_type} · str. ${field.source_reference.page} · wskaźnik ${field.confidence.toFixed(2)}`));if(field.requires_review||field.confidence<.8)b.append(el('small','source-warning','Do sprawdzenia'));b.addEventListener('click',()=>focus(field.id));fields.append(b);}
    const detail=el('p','source-location');right.append(detail);const split=el('div','source-comparison');split.append(left,right);view.append(split);
    toggle.addEventListener('click',()=>{fields.hidden=true;preview.hidden=false;preview.replaceChildren();const frame=el('iframe','comparison-eform');frame.title='Lokalny podgląd e-formularza';preview.append(frame);const doc=frame.contentDocument;const css=doc.createElement('link');css.rel='stylesheet';css.href='/static/app.css';doc.head.append(css);const extra=doc.createElement('link');extra.rel='stylesheet';extra.href='/static/workspace.css';doc.head.append(extra);doc.documentElement.lang='pl';doc.body.className='standalone-eform';window.FormForgeRender(doc.body,result.form);});
    list.addEventListener('click',()=>{fields.hidden=false;preview.hidden=true;preview.replaceChildren();});
    active={result,url,left,right,detail,page:1,mapMode:true};controls(active);
  }
  async function focus(id){if(!active)return;const context=active,selected=context.result.form.fields.find(f=>f.id===id);if(selected&&context.mapMode&&context.result.document.format==='pdf'){await pdfPage(context,selected.source_reference.page);if(active!==context||context.renderedPage!==selected.source_reference.page)return;}const {result,url,left,right,detail}=active,field=result.form.fields.find(f=>f.id===id);if(!field)return;const ref=field.source_reference;
    right.querySelectorAll('[data-source-field]').forEach(b=>b.classList.toggle('selected',b.dataset.sourceField===id));
    detail.textContent=`Źródło: strona ${ref.page}${ref.cell?' · '+ref.cell:''}${ref.bbox?' · bbox '+ref.bbox.map(v=>Math.round(v)).join(', '):' · brak geometrii'} — ${ref.text}`;
    const pdf=left.querySelector('.source-pdf');if(pdf)pdf.src=url+'#page='+ref.page+'&view=FitH';
    left.querySelectorAll('.source-selected').forEach(n=>n.classList.remove('source-selected'));
    const block=[...left.querySelectorAll('[data-block-id]')].find(n=>n.dataset.blockId===ref.block_id);if(block){block.classList.add('source-selected');block.scrollIntoView({behavior:'smooth',block:'center'});}
    const image=left.querySelector('img');if(image&&ref.bbox){let wrapper=image.parentElement;if(!wrapper.classList.contains('image-map')){wrapper=el('div','image-map');image.before(wrapper);wrapper.append(image);}wrapper.querySelector('.source-region')?.remove();const region=el('span','source-region');const page=result.document.pages.find(p=>p.id===ref.page),box=ref.input_bbox||ref.bbox,tiles=result.document.analysis?.image_tiles||[],tile=tiles.find(t=>t.page===ref.page),origin=tile?.source_bbox||[0,0],width=image.classList.contains('pdf-map-image')?page.width:image.naturalWidth||page.width,height=image.classList.contains('pdf-map-image')?page.height:image.naturalHeight||(tiles.length?Math.max(...tiles.map(t=>t.source_bbox[3])):page.height);region.style.left=(box[0]+origin[0])/width*100+'%';region.style.top=(box[1]+origin[1])/height*100+'%';region.style.width=(box[2]-box[0])/width*100+'%';region.style.height=Math.max(.05,(box[3]-box[1])/height*100)+'%';wrapper.append(region);if(tile||image.classList.contains('pdf-map-image'))region.scrollIntoView({behavior:'smooth',block:'center'});}
  }
  document.addEventListener('formforge-source',event=>{document.querySelector('[data-tab="document"]').click();focus(event.detail);});
  function clearCache(){for(const request of requests)request.abort();requests.clear();for(const url of pageCache.values())URL.revokeObjectURL(url);pageCache.clear();cachedFile=null;}
  function controls(context){
    const file=window.FormForgeWorkspace.get().sourceFile;if(cachedFile!==file){clearCache();cachedFile=file;}
    const bar=el('div','source-controls'),label=el('label','','Strona'),pages=el('select');pages.setAttribute('aria-label','Strona źródła');
    for(const p of context.result.document.pages){const o=el('option','',String(p.id));o.value=p.id;pages.append(o);}label.append(pages);
    const zoom=el('input');zoom.type='range';zoom.min='70';zoom.max='200';zoom.value='100';zoom.setAttribute('aria-label','Powiększenie źródła');const percent=el('span','','100%');bar.append(label,zoom,percent);
    context.left.prepend(bar);context.pages=pages;context.zoom=zoom;
    pages.addEventListener('change',()=>{context.page=Number(pages.value);if(context.result.document.format==='pdf'){if(context.mapMode)pdfPage(context,context.page);else context.left.querySelector('.source-pdf').src=context.url+'#page='+context.page;}else context.left.querySelectorAll('.source-document')[context.page-1]?.scrollIntoView({block:'start',behavior:'smooth'});});
    zoom.addEventListener('input',()=>{percent.textContent=zoom.value+'%';const map=context.left.querySelector('.image-map');if(map){map.style.maxWidth='none';map.style.width=zoom.value+'%';const img=map.querySelector('img');img.style.width='100%';img.style.maxWidth='none';img.style.maxHeight='none';}else for(const sheet of context.left.querySelectorAll('.source-document'))sheet.style.zoom=Number(zoom.value)/100;});
    if(context.result.document.format==='pdf'){
      const toggle=el('button','secondary','Oryginalny PDF');toggle.type='button';bar.append(toggle);context.frame=context.left.querySelector('.source-pdf');context.map=el('div','image-map pdf-source-map');context.note=el('p','source-note','Lokalny podgląd strony z zaznaczeniem rozpoznanych obszarów.');context.left.append(context.note,context.map);context.frame.hidden=true;
      toggle.addEventListener('click',()=>{context.mapMode=!context.mapMode;context.map.hidden=!context.mapMode;context.frame.hidden=context.mapMode;toggle.textContent=context.mapMode?'Oryginalny PDF':'Mapa rozpoznanych pól';if(context.mapMode)pdfPage(context,context.page);else context.frame.src=context.url+'#page='+context.page;});
      pdfPage(context,1);
    }
  }
  async function pdfPage(context,page){
    if(!context.map||!context.mapMode)return;
    context.page=page;context.pages.value=String(page);if(context.renderedPage===page)return;
    const file=window.FormForgeWorkspace.get().sourceFile;if(!file)return;
    try{
      let url=pageCache.get(page);
      if(!url){const body=new FormData();body.append('file',file);const controller=new AbortController();requests.add(controller);const timeout=setTimeout(()=>controller.abort(),15000);let response;
        try{response=await fetch('/api/v1/forms/source-page?page='+page,{method:'POST',headers:window.FormForgeWorkspace.headers(),body,signal:controller.signal});if(!response.ok)throw Error('Podgląd strony jest niedostępny. Użyj przycisku Oryginalny PDF.');url=URL.createObjectURL(await response.blob());}
        finally{clearTimeout(timeout);requests.delete(controller);}
        if(cachedFile!==file){URL.revokeObjectURL(url);return;}pageCache.set(page,url);
      }
      if(active!==context||context.page!==page)return;
      const img=el('img','source-image pdf-map-image');img.alt='Strona '+page+' przesłanego PDF';context.map.replaceChildren(img);context.map.style.width=context.zoom.value+'%';context.map.style.maxWidth='none';
      await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(Error('Nie można wyświetlić strony.'));img.src=url;});context.renderedPage=page;context.note.textContent='Rzeczywisty render strony PDF. Wybierz pole, aby zobaczyć jego położenie.';
    }catch(error){if(active===context)context.note.textContent=error.name==='AbortError'?'Podgląd strony przerwany. Możesz otworzyć oryginalny PDF.':error.message;}
  }
  window.FormForgeSource={attach,focus,clear:()=>{active=null;clearCache();}};
})();
