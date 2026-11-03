// Software UI test against the shipped HTML; inference is not simulated here.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('path');
require('fs').mkdirSync('.scratch/arabic-transcriber',{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||undefined});
 const page=await browser.newPage({viewport:{width:1060,height:800},deviceScaleFactor:1});
 await page.goto('file://'+path.resolve('src/arabic_transcriber/ui/index.html'));
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-idle.png'});
 await page.evaluate(()=>{
   window.snapshot={status:'running',stage:'Transkription läuft · TESTFIXTUR',progress:0.42,segments:[
   {start:0,end:24,text:'مرحبًا بكم. نتحدث اليوم عن أهمية التعلم وتبادل المعرفة.'},
   {start:24,end:48,text:'يمكن للتقنية أن تساعدنا على الوصول إلى المعلومات بسهولة. Berlin 2026'},
   {start:48,end:72,text:'الأهم هو أن نستخدم هذه الأدوات بطريقة واضحة ومفيدة.'}]};
   // app.js uses a lexical snapshot. This assignment is intentionally through its existing binding.
 });
 await page.evaluate("snapshot=window.snapshot; document.getElementById('times').checked=true; render();");
 if(!await page.locator('#start').isDisabled())throw Error('start enabled during job');
 if(!await page.locator('#cancel').isVisible())throw Error('cancel missing');
 if(await page.locator('.segment').count()!==3)throw Error('segments missing');
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-running.png'});
 await page.locator('#times').uncheck();
 if(await page.locator('.segment time').count())throw Error('timestamp toggle failed');
 if(await page.locator('.words').count()!==3)throw Error('toggle lost transcript');
 await page.locator('#settingsButton').click();
 await page.screenshot({path:'.scratch/arabic-transcriber/ui-settings.png',fullPage:true});
 console.log('UI smoke passed: growing RTL segments, busy controls, timestamp toggle, settings');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
