// Cloudflare Worker: on-demand read-only stock research. No AI subscription needed.
// Finnhub key is a Worker secret, never exposed to GitHub Pages.
const ORIGIN = "https://waseemraza844.github.io";
function output(data,status=200){
 return new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8","access-control-allow-origin":ORIGIN,"access-control-allow-methods":"GET, OPTIONS","cache-control":"public, max-age=300","x-content-type-options":"nosniff"}});
}
function num(v){const x=Number(v);return v===null||v===undefined||v===""||!Number.isFinite(x)?null:x;}
async function finnhub(path,ticker,key){
 const u=new URL("https://finnhub.io/api/v1/"+path);u.searchParams.set("symbol",ticker);u.searchParams.set("token",key);if(path==="stock/metric")u.searchParams.set("metric","all");
 const r=await fetch(u.toString(),{headers:{"accept":"application/json"}});
 if(!r.ok)throw new Error(r.status===429?"Market-data free-tier limit reached":"Market-data provider error ("+r.status+")");
 return r.json();
}
export default {async fetch(request,env,ctx){
 if(request.method==="OPTIONS")return new Response(null,{headers:{"access-control-allow-origin":ORIGIN,"access-control-allow-methods":"GET, OPTIONS","access-control-allow-headers":"content-type"}});
 if(request.method!=="GET")return output({error:"Method not allowed"},405);
 const url=new URL(request.url);
 if(url.pathname==="/health")return output({status:"ok",configured:!!env.FINNHUB_API_KEY});
 if(url.pathname!=="/stock")return output({error:"Not found"},404);
 const ticker=(url.searchParams.get("ticker")||"").toUpperCase();
 if(!/^[A-Z][A-Z0-9.-]{0,9}$/.test(ticker))return output({error:"Invalid ticker"},400);
 if(!env.FINNHUB_API_KEY)return output({error:"Backend not configured: FINNHUB_API_KEY is missing"},503);
 const key=new Request("https://cache.local/v2/stock/"+ticker);
 const cache=caches.default;
 const cached=await cache.match(key);if(cached)return cached;
 try{
 const [quote,profile,metrics,recs]=await Promise.all([
   finnhub("quote",ticker,env.FINNHUB_API_KEY),
   finnhub("stock/profile2",ticker,env.FINNHUB_API_KEY),
   finnhub("stock/metric",ticker,env.FINNHUB_API_KEY).catch(()=>({metric:{}})),
   finnhub("stock/recommendation",ticker,env.FINNHUB_API_KEY).catch(()=>[])
 ]);
 if(!num(quote.c)||quote.c<=0)return output({error:"No verified price for this ticker. It may be invalid or unsupported."},404);
 const m=metrics.metric||{};const trend=Array.isArray(recs)?recs[0]:null;
 const ratings=trend?[trend.strongBuy||0,trend.buy||0,trend.hold||0,trend.sell||0,trend.strongSell||0]:[];
 const total=ratings.reduce((a,b)=>a+b,0);
 const rating=total ? (ratings[0]+ratings[1])/total>=0.6?"Buy-leaning":(ratings[3]+ratings[4])/total>=0.5?"Sell-leaning":"Mixed / Hold" : "N/A";
 const result={
  ticker,name:profile.name||ticker,price:num(quote.c),price_date:new Date((quote.t||Date.now()/1000)*1000).toISOString().slice(0,10),
  generated_utc:new Date().toISOString(),rating,analyst_count:total||null,target:num(m.targetMeanPrice)||num(m.priceTargetMean)||null,
  growth:num(m.revenueGrowthTTMYoy)===null?null:num(m.revenueGrowthTTMYoy)/100,indicators:{
    pe:num(m.peTTM),forward_pe:num(m.peForwardAnnual),peg:num(m.pegRatio),eps:num(m.epsTTM),
    price_to_book:num(m.pbAnnual),roe:num(m.roeTTM),debt_to_equity:num(m.totalDebtEquityAnnual),
    market_cap:num(profile.marketCapitalization)?Number(profile.marketCapitalization)*1e6:null,
    profit_margin:num(m.netProfitMarginTTM),current_ratio:num(m.currentRatioAnnual)
  },fcf:[],source:"Finnhub API",links:{source:"https://finnhub.io/",financials_source:"https://finance.yahoo.com/quote/"+ticker+"/financials/"}
 };
 const response=output(result);
 ctx.waitUntil(cache.put(key,new Response(JSON.stringify(result),{headers:{"content-type":"application/json","access-control-allow-origin":ORIGIN,"cache-control":"public, max-age=3600"}})));
 return response;
 }catch(e){return output({error:String(e.message||e)},503);}
 }};
