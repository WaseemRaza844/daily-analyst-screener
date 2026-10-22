"""Refresh extra research tickers even if they fail the top-six screener."""
import json
from datetime import datetime, timezone
from pathlib import Path
from src.data.provider import YahooProvider

WATCH = ("CRWV",)
def main():
    out = Path("docs/research");out.mkdir(parents=True, exist_ok=True)
    provider = YahooProvider(ttl_hours=0, delay=1.0)
    for ticker in WATCH:
        try:
            info = provider.fundamentals(ticker)
            bars = provider.history(ticker, "1y")
            latest = bars[-1] if bars else {}
            payload = {"ticker": ticker, "generated_utc": datetime.now(timezone.utc).isoformat(),
                       "name":info.get("name"),"price":latest.get("close"),
                       "price_date":latest.get("date"),"rating":info.get("rating"),
                       "analyst_count":info.get("analyst_count"),"target":info.get("target"),
                       "growth":info.get("revenue_growth"),"fcf":info.get("fcf"),
                       "indicators":info.get("valuation") or {}}
            (out / (ticker + ".json")).write_text(json.dumps(payload,indent=2),encoding="utf-8")
            print(f"Refreshed {ticker} research")
        except Exception as exc:
            print(f"Optional ticker {ticker} unavailable: {exc}")

if __name__ == "__main__":
    main()
