"""HTML report (escape external text before inserting into markup)."""
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json


def render(rows, errors, scanned, timestamp=None):
    stamp = timestamp or datetime.now(timezone.utc).isoformat(timespec='seconds')
    head = '<tr>' + ''.join(f'<th>{escape(x)}</th>' for x in ('Ticker', 'Price', 'Consensus', 'Target', 'Support zone', 'Resistance zone', 'Revenue growth', 'Relative strength', 'Why it qualifies', 'Sources')) + '</tr>'
    body = []
    for r in rows:
        url = lambda value: escape(value, quote=True)
        links = ' | '.join(f'<a href="{url(r.links[k])}">{escape(title)}</a>' for k, title in [('source','Quote'), ('analysis_source','Analysts'), ('financials_source','Financials'), ('cash_source','Cash flow')])
        vals = (r.ticker, f'${r.price:.2f}', r.rating, f'${r.target:.2f}', f'${r.support:.2f}', f'${r.resistance:.2f}', f'{r.growth*100:.1f}%', f'{r.relative_strength:+.1f} pp', r.reason)
        body.append('<tr>' + ''.join(f'<td>{escape(v)}</td>' for v in vals) + f'<td>{links}</td></tr>')
    if not body:
        body.append('<tr><td colspan="10">No stocks passed all mandatory filters. Missing data is not treated as a pass.</td></tr>')
    css = 'body{font-family:Arial,sans-serif;color:#1f2937;padding:16px}table{border-collapse:collapse;width:100%;font-size:13px}th{background:#12304a;color:white}td,th{border:1px solid #d9e2e9;padding:9px;text-align:left;vertical-align:top}tr:nth-child(even){background:#f1f5f9}a{color:#165a9f}p{line-height:1.5}'
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>'
            f'<h2>Daily Analyst-Consensus Research Screen</h2><p><b>Generated:</b> {escape(stamp)} UTC '
            f'| <b>Universe screened:</b> {scanned} | <b>Matched:</b> {len(rows)} '
            f'| <b>Provider errors:</b> {len(errors)}</p><table>{head}{"".join(body)}</table>'
            '<p><b>Interpretation:</b> Support is the lowest low over the previous 20 sessions; resistance is the highest high over the previous 60 sessions. These are historical reference levels, not trade instructions or forecasted returns. Analyst targets may be stale; consensus is source-reported rather than independently audited. Institutional ownership is not buying flow.</p>'
            '<p>Yahoo Finance information accessed with yfinance for personal research. Verify source rights and each metric before relying on or redistributing this report.</p></body></html>')


def write_artifacts(rows, errors, scanned, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    (out/'report.html').write_text(render(rows, errors, scanned, stamp), encoding='utf-8')
    (out/'report.json').write_text(json.dumps({'generated_utc':stamp, 'scanned':scanned,
                                               'matches':[r.__dict__ for r in rows],
                                               'errors':errors}, indent=2), encoding='utf-8')
    return out/'report.html'
