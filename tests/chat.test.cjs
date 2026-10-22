// Browser-independent regression tests for the public chat widget.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('chat.js', 'utf8');
new vm.Script(source); // must fail CI on any JS parse error
function element(id) {
  return {
    id, hidden: id === 'research-chat', disabled: false, value: '',
    attributes: {}, children: [], listeners: {}, textContent: '',
    setAttribute(k,v){this.attributes[k]=v;},
    addEventListener(k,fn){this.listeners[k]=fn;},
    appendChild(child){this.children.push(child);},
    focus(){}, scrollTop:0, scrollHeight:100,
    click(){if(this.onclick)this.onclick();else if(this.listeners.click)this.listeners.click();}
  };
}
(async()=>{
  const ids=['research-chat','research-launch','research-close','research-form','research-question','research-messages','research-send','day','research-enable-ai'];
  const elements=Object.fromEntries(ids.map(id=>[id,element(id)]));
  elements.day.value='2026-10-22';
  const document={
    readyState:'complete',
    currentScript:{src:'https://example.github.io/stock/chat.js'},
    getElementById:id=>elements[id]||null,
    createElement:()=>element('message'),
    querySelectorAll:()=>[],
    addEventListener(){}
  };
  const calls=[];
  const fetch=async url=>{
    const u=String(url);calls.push(u);
    if(u.includes('/stock?ticker=NVDA'))return {ok:true,json:async()=>({
      ticker:'NVDA',name:'NVIDIA',price:200,rating:'Buy-leaning',target:230,
      growth:12,indicators:{pe:30,forward_pe:25,peg:1.5,eps:7},source:'Finnhub'
    })};
    return {ok:false,json:async()=>({error:'Not found'})};
  };
  const context={document,window:{STOCK_RESEARCH_API_URL:'https://worker.example.workers.dev'},location:{href:'https://example.github.io/stock/'},URL,fetch,console,encodeURIComponent,Number,Array,Set,RegExp,Error,String};
  vm.createContext(context);
  vm.runInContext(source,context);
  const launch=elements['research-launch'],panel=elements['research-chat'];
  assert.equal(panel.hidden,true);
  launch.click();
  assert.equal(panel.hidden,false,'button opens chat');
  launch.click();
  assert.equal(panel.hidden,true,'button closes chat');
  launch.click();
  elements['research-question'].value='Should I buy NVIDIA now or wait?';
  elements['research-form'].listeners.submit({preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(calls.some(x=>x.includes('ticker=NVDA')),'company name resolved to NVDA');
  assert.ok(!calls.some(x=>x.includes('ticker=THE')),'THE must not be treated as ticker');
  assert.ok(elements['research-messages'].children.some(x=>x.textContent.includes('NVIDIA')),'answer displayed');
  elements['research-close'].click();
  assert.equal(panel.hidden,true);
  console.log('Chat syntax, open/close, NVIDIA lookup, and response: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
