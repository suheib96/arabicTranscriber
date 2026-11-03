const $=id=>document.getElementById(id);
let source='file', selectedFile='', snapshot={segments:[],status:'idle'}, polling=false;
const timeLabel=s=>{s=Math.floor(s);return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;};
function render(){
 const busy=['running','cancelling'].includes(snapshot.status), segments=snapshot.segments||[];
 $('stage').textContent=snapshot.stage||'Bereit für deine Aufnahme';
 $('error').hidden=!snapshot.error;$('error').textContent=snapshot.error||'';
 $('progress').hidden=!busy;
 if(snapshot.progress==null){$('progress').removeAttribute('value');$('percent').textContent='';}
 else{$('progress').value=snapshot.progress;$('percent').textContent=`${Math.round(snapshot.progress*100)} %`;}
 ['start','choose','fileTab','youtubeTab','url','token','device','offline'].forEach(id=>$(id).disabled=busy);
 $('cancel').hidden=!busy;$('cancel').disabled=snapshot.status==='cancelling';
 $('copy').disabled=$('export').disabled=!segments.length;
 $('empty').hidden=segments.length>0;$('segmentCount').textContent=segments.length?`${segments.length} Abschnitte`:'';
 const area=$('transcript'), atBottom=area.scrollHeight-area.scrollTop-area.clientHeight<70;
 area.replaceChildren(...segments.map(s=>{let p=document.createElement('p');p.className='segment';if($('times').checked){let t=document.createElement('time');t.textContent=`≈ ${timeLabel(s.start)} – ${timeLabel(s.end)}`;p.append(t);}let text=document.createElement('span');text.className='words';text.textContent=s.text;p.append(text);return p;}));
 if(atBottom)area.scrollTop=area.scrollHeight;
}
function error(e){$('error').hidden=false;$('error').textContent=String(e.message||e);}
function feedback(s){$('feedback').textContent=s;setTimeout(()=>$('feedback').textContent='',3500);}
function selectSource(value){source=value;$('choose').hidden=value!=='file';$('urlLabel').hidden=value!=='youtube';for(const v of ['file','youtube']){$(v+'Tab').classList.toggle('selected',v===value);$(v+'Tab').setAttribute('aria-pressed',String(v===value));}}
$('fileTab').onclick=()=>selectSource('file');$('youtubeTab').onclick=()=>selectSource('youtube');
$('settingsButton').onclick=()=>{$('settings').hidden=!$('settings').hidden;$('settingsButton').setAttribute('aria-expanded',String(!$('settings').hidden));};
$('access').onclick=async e=>{e.preventDefault();try{await pywebview.api.open_model_access();}catch(e){error(e);}};
$('choose').onclick=async()=>{try{const path=await pywebview.api.choose_file();if(path){selectedFile=path;$('filename').textContent=path.split(/[\\/]/).pop();}}catch(e){error(e);}};
$('start').onclick=async()=>{try{const result=await pywebview.api.start(source,source==='file'?selectedFile:$('url').value,{token:$('token').value,offline:$('offline').checked,device:$('device').value});$('token').value='';if(!result.ok)error(result.error);else{snapshot=await pywebview.api.snapshot();render();}}catch(e){error(e);}};
$('cancel').onclick=async()=>{await pywebview.api.cancel();snapshot=await pywebview.api.snapshot();render();};
$('times').onchange=render;
$('copy').onclick=async()=>{try{const result=await pywebview.api.copy_all($('outputTimes').checked);if(!result.ok)error(result.error);else feedback('Kopiert');}catch(e){error(e);}};
$('export').onclick=async()=>{try{const r=await pywebview.api.export($('format').value,$('outputTimes').checked);if(r.error)error(r.error);else if(r.path)feedback('Gespeichert');}catch(e){error(e);}};
window.addEventListener('pywebviewready',()=>{polling=true;setInterval(async()=>{if(!polling)return;try{const next=await pywebview.api.snapshot();if(next.revision!==snapshot.revision||next.status!==snapshot.status){snapshot=next;render();}}catch(e){polling=false;error(e);}},400);});
window.desktopSmoke=async()=>{const state=await pywebview.api.snapshot();return {title:document.title,bridge:state.status==='idle',buttons:!!$('start')&&!!$('export'),rtl:$('transcript').dir,bodyWidth:document.body.scrollWidth,viewport:innerWidth};};
render();
