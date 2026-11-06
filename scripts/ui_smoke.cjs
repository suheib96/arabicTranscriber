// Exercise the shipped document through DOM controls; bridge/ASR output is test data.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {execFileSync} = require('child_process');
require('fs').mkdirSync('.scratch/arabic-transcriber', {recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||undefined});
 const page=await browser.newPage({viewport:{width:1060,height:960},deviceScaleFactor:1});
 const python=process.env.PYTHON||(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
 const html=execFileSync(python,['-c','import sys; from arabic_transcriber.app import ui_document; sys.stdout.buffer.write(ui_document().encode("utf-8"))'],{encoding:'utf8',maxBuffer:4*1024*1024});
 await page.setContent(html);
 await page.evaluate(()=>document.fonts.ready);
 if(!await page.evaluate(()=>document.fonts.check('21px NotoArabic')))throw Error('Arabic font missing');
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-idle.png'});
 await page.evaluate(()=>window.pywebview={api:{choose_file:async()=>{throw Error('Dialog nicht verfügbar');}}});
 await page.locator('#choose').click();
 await page.evaluate(()=>render());
 if(!await page.locator('#error').isVisible())throw Error('polling hides dialog error');
 await page.evaluate(()=>window.pywebview.api.choose_file=async()=>'/tmp/fixture.wav');
 await page.locator('#choose').click();
 if(await page.locator('#error').isVisible())throw Error('successful selection retains dialog error');
 await page.evaluate(()=>{
   window.fixture={status:'running',stage:'Transkribieren',progress:0.42,active_id:'one',selected_id:'one',paused:false,pausing:false,model_loaded:true,worker_running:true,segments:[
     {start:0,end:12,text:'مرحبًا بكم. نتحدث اليوم عن أهمية التعلم وتبادل المعرفة.'},
     {start:12,end:24,text:'يمكن للتقنية أن تساعدنا على الوصول إلى المعلومات بسهولة. Berlin 2026'},
     {start:24,end:36,text:'الأهم هو أن نستخدم هذه الأدوات بطريقة واضحة ومفيدة.'}],items:[
       {id:'one',source:'youtube',value:'https://youtu.be/one',title:'Interview · TESTFIXTUR',metadata_status:'ready',status:'running',stage:'Transkribieren',progress:0.42,elapsed_seconds:134},
       {id:'two',source:'youtube',value:'https://youtu.be/two',title:'<img src=x onerror="window.injected=true"> · TESTFIXTUR',metadata_status:'ready',status:'queued',stage:'Wartet',progress:null,elapsed_seconds:0}
     ]};
   window.originalSegments=window.fixture.segments;
   window.pywebview={api:{
     snapshot:async()=>window.fixture,
     start:async(source,value)=>{window.fixture.items.push({id:'three',title:value,value,source,metadata_status:'loading',status:'queued',stage:'Wartet',progress:null});return {ok:true,id:'three'};},
     select:async(id)=>{window.fixture.selected_id=id;window.fixture.segments=id==='one'?window.originalSegments:[{start:0,end:12,text:'نص آخر'}];return {ok:true};},
     pause:async()=>{Object.assign(window.fixture,{paused:true,pausing:false,release_in_seconds:300});window.fixture.items[0].status='paused';return {ok:true};},
     release_memory:async()=>{Object.assign(window.fixture,{model_loaded:false,worker_running:false,release_in_seconds:null});return {ok:true};},
     resume:async()=>{window.fixture.paused=false;window.fixture.items[0].status='running';return {ok:true};},
     remove:async(id)=>{window.fixture.items=window.fixture.items.filter(i=>i.id!==id);return {ok:true};},
     cancel:async()=>({ok:true}),platform_info:async()=>({platform:'darwin'})
   }};
 });
 await page.evaluate('snapshot=window.fixture; render();');
 if(await page.locator('.queue-row').count()!==2)throw Error('queue rows missing');
 if(!await page.locator('#start').isEnabled())throw Error('cannot add while running');
 await page.locator('#youtubeTab').click();
 await page.locator('#url').fill('https://youtu.be/three');
 await page.locator('#start').click();
 if(await page.locator('.queue-row').count()!==3)throw Error('new link did not enter queue');
 if(await page.locator('#url').inputValue()!=='')throw Error('added URL not cleared');
 if(await page.evaluate(()=>window.injected))throw Error('untrusted title became HTML');
 await page.evaluate(()=>{window.fixture.items[1].title='Gespräch · Studium · TESTFIXTUR'; snapshot=window.fixture; render();});
 await page.locator('#times').check();
 if(await page.locator('.segment time').count()!==3)throw Error('timestamps missing');
 const stable=await page.evaluate(()=>{
   const node=document.querySelector('.words');
   const selection=window.getSelection(),range=document.createRange();range.selectNodeContents(node);
   selection.removeAllRanges();selection.addRange(range);const selected=selection.toString();
   snapshot={...snapshot,progress:0.51};render();
   return document.querySelector('.words')===node&&selection.toString()===selected;
 });
 if(!stable)throw Error('progress replaced transcript or selection');
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-queue-running.png',fullPage:true});
 await page.locator('[data-id="two"] .queue-title').click();
 if(await page.locator('.words').count()!==1)throw Error('selection mixed transcripts');
 if(!await page.locator('#transcriptTitle').textContent())throw Error('selected title missing');
 await page.locator('[data-id="one"] .queue-title').click();
 await page.locator('#pause').click();
 if((await page.locator('#pause').textContent()).trim()!=='Fortsetzen')throw Error('resume action missing');
 if(!(await page.locator('#memoryState').textContent()).includes('05:00'))throw Error('pause retention countdown missing');
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-queue-paused.png',fullPage:true});
 await page.locator('#releaseMemory').click();
 if(!(await page.locator('#memoryState').textContent()).includes('entladen'))throw Error('release state missing');
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-queue-freed.png',fullPage:true});
 await page.locator('#pause').click();
 await page.locator('[data-id="three"] .queue-remove').click();
 if(await page.locator('.queue-row').count()!==2)throw Error('queued removal failed');
 await page.locator('#times').uncheck();
 if(await page.locator('.segment time').count())throw Error('timestamp toggle failed');
 await page.setViewportSize({width:760,height:600});
 if(await page.evaluate(()=>document.body.scrollWidth>innerWidth))throw Error('compact window overflows horizontally');
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-queue-compact.png',fullPage:true});
 await page.evaluate(()=>{
   window.pollStats={active:0,max:0,calls:0};
   window.pywebview.api.snapshot=async()=>{
     const stats=window.pollStats;stats.calls++;stats.active++;stats.max=Math.max(stats.max,stats.active);
     await new Promise(resolve=>setTimeout(resolve,650));stats.active--;return window.fixture;
   };
   window.dispatchEvent(new Event('pywebviewready'));
 });
 await page.waitForTimeout(1500);
 const stats=await page.evaluate(()=>window.pollStats);
 if(stats.max!==1||stats.calls<2)throw Error('snapshot polling overlaps or stopped');
 console.log('UI smoke passed: queue, titles, selection, pause/release/resume, RTL, compact window and single-flight polling');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
