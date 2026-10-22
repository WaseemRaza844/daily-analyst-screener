/* Free, browser-only research assistant. No API credentials leave the device. */
(() => {
  const $ = id => document.getElementById(id);
  const panel = $('research-chat'), messages = $('research-messages'), input = $('research-question');
  const fmt = (n, unit='') => Number.isFinite(Number(n)) && n != null ? Number(n).toLocaleString('en-US',{maximumFractionDigits:2})+unit : 'not available';
  let report = null, engine = null, busy = false;
  function say(kind, text) {
    const node = document.createElement('div'); node.className = 'research-message '+kind;
    node.textContent = text; messages.appendChild(node); messages.scrollTop = messages.scrollHeight;
  }
  async function loadReport(){
    const day = $('day')?.value;
    if(!day) return null;
    try{
      const response = await fetch('docs/history/'+encodeURIComponent(day)+'.json',{cache:'no-store'});
      if(!response.ok) throw new Error('Snapshot unavailable');
      report = await response.json(); return report;
    }catch(e){ report = null; return null; }
  }
  function identify(query) {
    const upper = query.toUpperCase();
    const all = report?.matches || [];
    const explicit = upper.match(/\$([A-Z]{1,6})\b/) || upper.match(/\b(?:TICKER|STOCK|ABOUT|ANALYZE|ANALYSE|FOR|OF)\s+([A-Z]{1,6})\b/);
    if(explicit) return explicit[1];
    return all.find(x => new RegExp('\\b'+x.ticker+'\\b','i').test(query))?.ticker ||
      (upper.trim().match(/^[A-Z]{1,6}$/)?.[0]) || (upper.match(/\bCRWV\b/)?.[0]) || null;
  }
  const meanings = {
    'peg':'PEG compares P/E with expected earnings growth. It is less useful with negative earnings or unreliable growth forecasts.',
    'forward p/e':'Forward P/E compares the share price with projected earnings. It depends on estimates that may change.',
    'p/e':'P/E is price divided by annual earnings per share. A negative or missing P/E often means the firm has no positive trailing earnings.',
    'eps':'EPS means earnings per share, the profit or loss allocated to each share.',
    'roe':'ROE is return on equity. It measures profitability versus shareholder equity; leverage can inflate it.',
    'debt':'Debt/equity compares borrowing with shareholder equity. Higher values can indicate financial risk; industry comparisons matter.',
    'support':'Support is an observed historical price low, not a guaranteed floor.',
    'resistance':'Resistance is an observed historical price high, not a guaranteed selling price.',
    'target':'An analyst price target is an opinion about possible future value, not a promise.',
    'cash flow':'Free cash flow is cash remaining after capital expenditure; positive and growing cash flow may support financial resilience.'
  };
  function grounded(question) {
    const q = question.trim(), sym = identify(q);
    const metric = Object.keys(meanings).find(k=>q.toLowerCase().includes(k));
    const stock = report?.matches?.find(x=>x.ticker===sym);
    if(stock) {
      const v=stock.indicators||{};
      const upside=stock.target && stock.price ? ((stock.target/stock.price-1)*100).toFixed(1)+'%' : 'not available';
      let out = stock.name+' ('+sym+') appeared in the '+report.generated_utc.slice(0,10)+' research screen. The saved price was $'+fmt(stock.price)+', while analysts reported a '+stock.rating+' consensus and a $'+fmt(stock.target)+' average target (implied difference '+upside+'). Revenue growth was '+fmt(Number(stock.growth)*100,'%')+'; 3-month strength versus its benchmark was '+fmt(stock.relative_strength,' percentage points')+'. ';
      out += 'Trailing P/E: '+fmt(v.pe)+'; forward P/E: '+fmt(v.forward_pe)+'; PEG: '+fmt(v.peg)+'; EPS: '+fmt(v.eps)+'; debt/equity: '+fmt(v.debt_to_equity)+'. ';
      out += metric ? meanings[metric]+' ' : '';
      out += 'These figures are snapshots, not live quotes. A Buy analyst consensus is not a personal recommendation; check valuation, risk and updated filings before deciding.';
      return out;
    }
    if(sym) return sym+' is not included in the selected stocks for this report date. I cannot retrieve verified live financial statements for arbitrary tickers from this static site. You can research it at https://finance.yahoo.com/quote/'+encodeURIComponent(sym)+'/ . Ask about a ticker listed in the dashboard to get a grounded summary; a future backend can support live custom-ticker lookups.';
    if(metric) return meanings[metric]+' If you mention one of today\'s selected ticker symbols, I can connect the explanation to its saved numbers.';
    return 'I can explain P/E, forward P/E, PEG, EPS, free cash flow, growth, debt, support and analyst targets. Enter a ticker visible in the selected report, such as '+(report?.matches?.[0]?.ticker||'a stock in the table')+', or ask a question about a specific indicator.';
  }
  async function answer(question){
    if(busy) return;
    busy=true;$('research-send').disabled=true;say('user',question);
    if(!report || report.generated_utc.slice(0,10)!==$('day').value) await loadReport();
    const sym=identify(question);
    let watchSnapshot=null;
    if(sym && !(report?.matches||[]).some(x=>x.ticker===sym) && sym==='CRWV') {
      try { const response=await fetch('docs/research/CRWV.json',{cache:'no-store'}); if(response.ok) watchSnapshot=await response.json(); } catch(e) {}
    }
    let factual=grounded(question);
    if(watchSnapshot) {
      const v=watchSnapshot.indicators||{};
      const targetDifference=watchSnapshot.target && watchSnapshot.price ? ((watchSnapshot.target/watchSnapshot.price-1)*100).toFixed(1)+'%' : 'unavailable';
      factual=(watchSnapshot.name||sym)+' ('+sym+') was researched on '+watchSnapshot.generated_utc.slice(0,10)+'. Last price: 
    if(engine && (watchSnapshot || report?.matches?.some(x=>x.ticker===identify(question)))) {
      try {
        const completion=await engine.chat.completions.create({messages:[
          {role:'system',content:'Explain stock financial information in friendly, plain language using ONLY the following verified saved dashboard data. Never invent facts, recent news, prices, forecasts, or assert a buy/sell recommendation. Distinguish analyst rating from personalized advice. If data is missing say so. Answer under 140 words. Context: '+JSON.stringify(watchSnapshot || report.matches.find(x=>x.ticker===identify(question)))},
          {role:'user',content:question}
        ],temperature:0.2,max_tokens:230});
        say('assistant',(completion.choices?.[0]?.message?.content||factual)+'\n\nSaved report date: '+(watchSnapshot?.generated_utc||report.generated_utc).slice(0,10)+'.');
      }catch(e){say('assistant',factual+'\n\nLocal AI could not complete; showing verified metrics instead.');}
    } else say('assistant',factual);
    busy=false;$('research-send').disabled=false;
  }
  $('research-launch').addEventListener('click',()=>{panel.hidden=!panel.hidden;if(!panel.hidden) input.focus();});
  $('research-close').addEventListener('click',()=>panel.hidden=true);
  $('research-form').addEventListener('submit',e=>{e.preventDefault();let q=input.value.trim();if(q){input.value='';answer(q);}});
  document.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>answer(b.dataset.question)));
  $('day')?.addEventListener('change',()=>{report=null;say('assistant','Report date changed. I will use that date for the next answer.');});
  $('research-enable-ai').addEventListener('click',async ()=>{
    if(engine) return;
    if(!navigator.gpu){say('assistant','Local AI requires WebGPU in a compatible browser. The built-in metric explanations still work for free.');return;}
    $('research-enable-ai').disabled=true;
    say('assistant','Loading optional Qwen 0.5B locally. This downloads a large model to your browser and requires sufficient GPU memory. No API key or paid service is used.');
    try{
      const mlc=await import('https://esm.run/@mlc-ai/web-llm');
      engine=await mlc.CreateMLCEngine('Qwen2.5-0.5B-Instruct-q4f16_1-MLC',{initProgressCallback:p=>{$('research-ai-status').textContent=p.text||'Loading model';}});
      $('research-ai-status').textContent='Local AI ready';
      say('assistant','Local AI enabled. Answers use saved dashboard data and may still make errors.');
    }catch(err){$('research-ai-status').textContent='Unavailable';say('assistant','Local AI did not load ('+String(err.message||err).slice(0,100)+'). The free metric-based assistant remains available.');$('research-enable-ai').disabled=false;}
  });
  loadReport(); say('assistant','Ask me about a stock in today\'s table or what P/E, PEG or cash flow means. Optional local AI can rephrase saved numbers in simple words.');
})();
+fmt(watchSnapshot.price)+' (price date '+(watchSnapshot.price_date||'unavailable')+'). Analyst rating: '+(watchSnapshot.rating||'unavailable')+'; target: 
    if(engine && report?.matches?.some(x=>x.ticker===identify(question))) {
      try {
        const completion=await engine.chat.completions.create({messages:[
          {role:'system',content:'Explain stock financial information in friendly, plain language using ONLY the following verified saved dashboard data. Never invent facts, recent news, prices, forecasts, or assert a buy/sell recommendation. Distinguish analyst rating from personalized advice. If data is missing say so. Answer under 140 words. Context: '+JSON.stringify(report.matches.find(x=>x.ticker===identify(question)))},
          {role:'user',content:question}
        ],temperature:0.2,max_tokens:230});
        say('assistant',(completion.choices?.[0]?.message?.content||factual)+'\n\nSaved report date: '+report.generated_utc.slice(0,10)+'.');
      }catch(e){say('assistant',factual+'\n\nLocal AI could not complete; showing verified metrics instead.');}
    } else say('assistant',factual);
    busy=false;$('research-send').disabled=false;
  }
  $('research-launch').addEventListener('click',()=>{panel.hidden=!panel.hidden;if(!panel.hidden) input.focus();});
  $('research-close').addEventListener('click',()=>panel.hidden=true);
  $('research-form').addEventListener('submit',e=>{e.preventDefault();let q=input.value.trim();if(q){input.value='';answer(q);}});
  document.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>answer(b.dataset.question)));
  $('day')?.addEventListener('change',()=>{report=null;say('assistant','Report date changed. I will use that date for the next answer.');});
  $('research-enable-ai').addEventListener('click',async ()=>{
    if(engine) return;
    if(!navigator.gpu){say('assistant','Local AI requires WebGPU in a compatible browser. The built-in metric explanations still work for free.');return;}
    $('research-enable-ai').disabled=true;
    say('assistant','Loading optional Qwen 0.5B locally. This downloads a large model to your browser and requires sufficient GPU memory. No API key or paid service is used.');
    try{
      const mlc=await import('https://esm.run/@mlc-ai/web-llm');
      engine=await mlc.CreateMLCEngine('Qwen2.5-0.5B-Instruct-q4f16_1-MLC',{initProgressCallback:p=>{$('research-ai-status').textContent=p.text||'Loading model';}});
      $('research-ai-status').textContent='Local AI ready';
      say('assistant','Local AI enabled. Answers use saved dashboard data and may still make errors.');
    }catch(err){$('research-ai-status').textContent='Unavailable';say('assistant','Local AI did not load ('+String(err.message||err).slice(0,100)+'). The free metric-based assistant remains available.');$('research-enable-ai').disabled=false;}
  });
  loadReport(); say('assistant','Ask me about a stock in today\'s table or what P/E, PEG or cash flow means. Optional local AI can rephrase saved numbers in simple words.');
})();
+fmt(watchSnapshot.target)+'; implied target difference: '+targetDifference+'. Revenue growth: '+fmt(watchSnapshot.growth==null?null:watchSnapshot.growth*100,'%')+'. P/E: '+fmt(v.pe)+'; forward P/E: '+fmt(v.forward_pe)+'; PEG: '+fmt(v.peg)+'; earnings per share: '+fmt(v.eps)+'; debt/equity: '+fmt(v.debt_to_equity)+'. '+ 'This ticker is on the separate research watchlist, not necessarily a qualifying screened stock. Data is dated and incomplete fields are not investment signals.';
    }
    if(engine && report?.matches?.some(x=>x.ticker===identify(question))) {
      try {
        const completion=await engine.chat.completions.create({messages:[
          {role:'system',content:'Explain stock financial information in friendly, plain language using ONLY the following verified saved dashboard data. Never invent facts, recent news, prices, forecasts, or assert a buy/sell recommendation. Distinguish analyst rating from personalized advice. If data is missing say so. Answer under 140 words. Context: '+JSON.stringify(report.matches.find(x=>x.ticker===identify(question)))},
          {role:'user',content:question}
        ],temperature:0.2,max_tokens:230});
        say('assistant',(completion.choices?.[0]?.message?.content||factual)+'\n\nSaved report date: '+report.generated_utc.slice(0,10)+'.');
      }catch(e){say('assistant',factual+'\n\nLocal AI could not complete; showing verified metrics instead.');}
    } else say('assistant',factual);
    busy=false;$('research-send').disabled=false;
  }
  $('research-launch').addEventListener('click',()=>{panel.hidden=!panel.hidden;if(!panel.hidden) input.focus();});
  $('research-close').addEventListener('click',()=>panel.hidden=true);
  $('research-form').addEventListener('submit',e=>{e.preventDefault();let q=input.value.trim();if(q){input.value='';answer(q);}});
  document.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>answer(b.dataset.question)));
  $('day')?.addEventListener('change',()=>{report=null;say('assistant','Report date changed. I will use that date for the next answer.');});
  $('research-enable-ai').addEventListener('click',async ()=>{
    if(engine) return;
    if(!navigator.gpu){say('assistant','Local AI requires WebGPU in a compatible browser. The built-in metric explanations still work for free.');return;}
    $('research-enable-ai').disabled=true;
    say('assistant','Loading optional Qwen 0.5B locally. This downloads a large model to your browser and requires sufficient GPU memory. No API key or paid service is used.');
    try{
      const mlc=await import('https://esm.run/@mlc-ai/web-llm');
      engine=await mlc.CreateMLCEngine('Qwen2.5-0.5B-Instruct-q4f16_1-MLC',{initProgressCallback:p=>{$('research-ai-status').textContent=p.text||'Loading model';}});
      $('research-ai-status').textContent='Local AI ready';
      say('assistant','Local AI enabled. Answers use saved dashboard data and may still make errors.');
    }catch(err){$('research-ai-status').textContent='Unavailable';say('assistant','Local AI did not load ('+String(err.message||err).slice(0,100)+'). The free metric-based assistant remains available.');$('research-enable-ai').disabled=false;}
  });
  loadReport(); say('assistant','Ask me about a stock in today\'s table or what P/E, PEG or cash flow means. Optional local AI can rephrase saved numbers in simple words.');
})();
