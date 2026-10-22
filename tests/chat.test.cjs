const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const src=fs.readFileSync('chat.js','utf8');
new vm.Script(src);
function el(id){return {id,hidden:id==='research-chat',disabled:false,value:'',listeners:{},children:[],textContent:'',setAttribute(){},addEventListener(k,fn){this.listeners[k]=fn},appendChild(c){this.children.push(c)},focus(){},click(){this.onclick?.()},scrollTop:0,scrollHeight:100};}
(async()=>{
 const ids=['research-chat','research-launch','research-close','research-form','research-question','research-messages','research-send','day','research-enable-ai'];
 const elements=Object.fromEntries(ids.map(x=>[x,el(x)]));
 const document={readyState:'complete',currentScript:{src:'https://example.github.io/site/chat.js'},getElementById:id=>elements[id],createElement:()=>el('message'),querySelectorAll:()=>[],addEventListener(){}};
 const requests=[];
 const fetch=async (url,opts={})=>{
   requests.push({url:String(url),opts});
   if(String(url).endsWith('/chat')){
     const body=JSON.parse(opts.body);
     return {ok:true,json:async()=>({answer:'AI answer for '+(body.ticker||'general question'),stock_date:'2026-10-22'})};
   }
   return {ok:false,json:async()=>({error:'Not found'})};
 };
 const context={document,window:{STOCK_RESEARCH_API_URL:'https://worker.example.workers.dev'},location:{href:'https://example.github.io/site/'},URL,fetch,console,encodeURIComponent,Number,Array,Set,RegExp,Error,String};
 vm.createContext(context);vm.runInContext(src,context);
 const launch=elements['research-launch'],panel=elements['research-chat'];
 assert.equal(panel.hidden,true);launch.click();assert.equal(panel.hidden,false);launch.click();assert.equal(panel.hidden,true);launch.click();
 async function ask(q){elements['research-question'].value=q;elements['research-form'].listeners.submit({preventDefault(){}});await new Promise(r=>setImmediate(r));}
 await ask('Should I buy Nvidia or wait?');
 await ask('What about its PEG?');
 await ask('Analyze AT&T');
 await ask('Please analyze T-Mobile in simple English');
 const calls=requests.filter(r=>r.url.endsWith('/chat')).map(r=>JSON.parse(r.opts.body));
 assert.equal(calls[0].ticker,'NVDA');
 assert.equal(calls[1].ticker,'NVDA','follow-up retains stock context');
 assert.equal(calls[2].ticker,'T','AT&T company name resolved to T');
 assert.equal(calls[3].ticker,'TMUS','T-Mobile company name resolved to TMUS');
 assert.equal(calls[1].history.length,2,'follow-up passes conversational history');
 assert.equal(elements['research-messages'].children.some(x=>x.textContent.includes('AI answer for')),true);
 elements['research-close'].click();assert.equal(panel.hidden,true);
 console.log('Chat open/close, AI endpoint, Nvidia, followups, AT&T and T-Mobile: PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
