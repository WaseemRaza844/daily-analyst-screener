"""Create a daily browsable Pages dashboard and retain seven date-stamped reports."""
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo
from html import escape
from pathlib import Path

OUT = Path("docs")
HISTORY = OUT / "history"
KEEP = 7

def main():
    report = json.loads(Path("output/report.json").read_text(encoding="utf-8"))
    HISTORY.mkdir(parents=True, exist_ok=True)
    day = report["generated_utc"][:10]
    (HISTORY / (day + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
    history = []
    for path in sorted(HISTORY.glob("*.json"), reverse=True):
        try:
            age = (date.fromisoformat(day) - date.fromisoformat(path.stem)).days
        except ValueError:
            continue
        if age >= KEEP:
            path.unlink()
        elif age >= 0:
            try:
                history.append((path.stem, json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError):
                continue
    latest = history[0][1] if history else report
    previous = history[1][1] if len(history) > 1 else None
    latest_symbols = {x.get('ticker') for x in latest.get('matches', [])}
    previous_symbols = {x.get('ticker') for x in previous.get('matches', [])} if previous else set()
    overlap = len(latest_symbols & previous_symbols) if previous else None
    stamp_et = datetime.fromisoformat(report['generated_utc']).astimezone(ZoneInfo('America/New_York')).strftime('%b %d, %Y at %I:%M %p %Z')
    date_options = "".join('<option value="' + escape(d) + '">' + escape(d) + '</option>' for d, _ in history)
    items = []
    for d, r in history:
        blocks = []
        for x in r.get("matches", []):
            h = lambda k: escape(str(x.get(k, "N/A")))
            v = x.get("indicators") or {}
            def metric(k):
                number = v.get(k)
                return "N/A" if number is None else escape(f"{number:,.2f}")
            def dollars(k):
                number = x.get(k)
                return "N/A" if number is None else f"${number:,.2f}"
            links = x.get("links", {})
            source = links.get("source", "")
            source_link = ('<a href="' + escape(source, quote=True) + '" rel="noopener noreferrer">Yahoo Finance source</a>') if source.startswith("https://finance.yahoo.com/") else ""
            pct = lambda key: "N/A" if x.get(key) is None else f"{float(x[key])*100:.1f}%"
            blocks.append(f"""<article class="stock">
<h3>{h('ticker')} · {h('name')}</h3>
<p><strong>Price:</strong> {dollars('price')} · <strong>Analyst consensus:</strong> {h('rating')} · <strong>Target:</strong> {dollars('target')}</p>
<p><strong>20-session support:</strong> {dollars('support')} · <strong>60-session resistance:</strong> {dollars('resistance')}</p>
<p><strong>Revenue growth:</strong> {pct('growth')} · <strong>3-month relative strength:</strong> {h('relative_strength')} percentage points</p>
<div class="metrics"><span>P/E: <b>{metric('pe')}</b></span><span>Forward P/E: <b>{metric('forward_pe')}</b></span><span>PEG: <b>{metric('peg')}</b></span>
<span>EPS: <b>{metric('eps')}</b></span><span>Price/book: <b>{metric('price_to_book')}</b></span><span>Profit margin: <b>{metric('profit_margin')}</b></span>
<span>ROE: <b>{metric('roe')}</b></span><span>Debt/equity: <b>{metric('debt_to_equity')}</b></span><span>Current ratio: <b>{metric('current_ratio')}</b></span>
<span>Market cap: <b>{metric('market_cap')}</b></span></div>
<p>{h('reason')}</p><p>{source_link}</p></article>""")
        if not blocks:
            blocks = ["<p>No stocks met all required screening criteria for this day.</p>"]
        items.append(f'<section class="report" data-day="{escape(d)}"><p>Generated: {escape(r.get("generated_utc","unknown"))} · Screened: {int(r.get("scanned",0))} · Matched: {len(r.get("matches", []))} · Errors: {len(r.get("errors", []))}</p>{"".join(blocks)}</section>')
    glossary = {
        "P/E": "Current share price divided by earnings per share. Negative earnings make P/E unhelpful.",
        "Forward P/E": "Price relative to forecast earnings; forecasts can change.",
        "PEG": "P/E adjusted for expected earnings growth. Interpret carefully when growth estimates are uncertain.",
        "EPS": "Earnings per common share. One-time profits or losses can distort it.",
        "Price/book": "Market valuation relative to accounting equity; industry-dependent.",
        "Profit margin": "Profit as a fraction of revenue; shown as a decimal here (0.20 equals 20%).",
        "ROE": "Return on equity; shown as decimal (0.15 equals 15%). High debt can inflate it.",
        "Debt/equity": "Debt compared with equity. Yahoo often represents this in percentage points (e.g. 150 corresponds to 1.5x).",
        "Current ratio": "Current assets divided by current liabilities; less comparable for banks.",
        "Market cap": "Market value of outstanding shares in dollars.",
        "Relative strength": "Stock's 3-month return minus the configured sector ETF return, in percentage points.",
        "Support / resistance": "Historical 20-day low and 60-day high; neither is a price guarantee.",
        "Free cash flow": "Cash generated after capital spending. Trends should be considered over multiple years.",
        "Analyst target": "An estimate from analysts, not a promise of future price.",
    }
    definitions = "".join(f"<details><summary>{escape(k)}</summary><p>{escape(v)}</p></details>" for k,v in glossary.items())
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Analyst Research Dashboard</title><style>
body{{font:16px system-ui,Arial;background:#f3f7fb;color:#24364b;margin:0}}header{{background:#132f4f;color:white;padding:30px 5%}}
main{{max-width:1100px;margin:auto;padding:20px}}.stock,aside,.top{{background:white;border:1px solid #dce6ef;border-radius:13px;padding:20px;margin:15px 0;box-shadow:0 2px 10px #172c4210}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:9px;background:#f2f6fa;padding:12px;border-radius:9px}}
.metrics span{{padding:5px}}p{{line-height:1.5}}a{{color:#16609f}}select{{padding:10px;border-radius:8px;border:1px solid #a8b9c9;font:inherit}}
details{{padding:12px;border-bottom:1px solid #e1e7ee}}summary{{cursor:pointer;font-weight:bold}}.report{{display:none}}.report.active{{display:block}}
small{{color:#52677c}}</style></head><body>
<header><h1>Daily Analyst-Consensus Research Dashboard</h1><p>Daily at 7:00 AM Eastern · Historical results · No trading recommendations</p></header>
<main><div class="top"><label for="day"><b>View report date:</b></label> <select id="day">{date_options}</select>
<p><strong>Latest completed screening:</strong> {escape(stamp_et)} · <strong>Universe checked:</strong> {int(report.get('scanned',0))} · <strong>Qualified:</strong> {len(report.get('matches',[]))} · <strong>Repeated from prior report:</strong> {overlap if overlap is not None else 'N/A'}</p><p><small>Fresh screen conducted for every completed scheduled run. Some stocks may qualify repeatedly; daily screening does not guarantee five or six matches. Dates are report-generation dates, not necessarily trading days; prices may reflect the previous close. N/A means unavailable.</small></p></div>
{"".join(items)}
<aside><h2>Understand the indicators</h2>{definitions}</aside>
<p><small>For personal research only. Analysts and free market-data feeds may be incomplete or delayed. This dashboard is publicly reachable even if the source repository is private. No credentials or family information are published.</small></p></main>
<script>const select=document.getElementById('day');function show(){{document.querySelectorAll('.report').forEach(x=>x.classList.toggle('active',x.dataset.day===select.value));}}select.addEventListener('change',show);show();</script></body></html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    Path("index.html").write_text(page, encoding="utf-8")
    (OUT / ".nojekyll").touch()
    print(f"Dashboard contains {len(history)} days, most recent {day}")

if __name__ == "__main__":
    main()
