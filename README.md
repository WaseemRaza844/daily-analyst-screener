# Daily Analyst-Consensus Stock Screener

Personal-research stock screener using free-to-access Yahoo Finance data through `yfinance`, technical support/resistance, configurable strict filtering, and optional SMTP email delivery. **Not an investment recommendation service.** No guarantee of 5–10 matches. This is a screened *configured ticker universe*, not an exchange-wide exhaustive scan.

## How screening works

All required conditions must pass: price < configured maximum, consensus `buy` or `strong_buy`, minimum analyst count and target upside, latest reported/derived revenue growth, positive benchmark-relative 63-session performance, and positive/improving annual free cash flow. Sector ETFs provide a benchmark, falling back to SPY. Buy and sell "zones" in the HTML are **historical support/resistance reference levels**: lowest low in previous 20 sessions and highest high in previous 60. They are not optimized trading entries/exits, and resistance may be below current price in a breakout. Scoring ranks eligible stocks by analyst upside, revenue growth, and relative strength, without asserting a guaranteed growth outcome.

**Buying signals limitation:** Yahoo's `heldPercentInstitutions` measures ownership, not net buying. Recent insider or institutional *buying* is not verified by this provider. Accordingly `require_institutional_or_insider_buying: true` fails closed (no matches) until a proper purchases-flow provider is implemented. Analyst coverage may be missing, consensus definitions may differ, target price may be stale, and financials may be delayed. No fabricated values or automatic loosening of filters. A result can have low liquidity and material risk; this is not comprehensive diligence.

## Setup locally

Python 3.11+ recommended:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.main
```

Open `output/report.html`; `output/report.json` includes matches, run timestamp and nonfatal per-ticker provider errors. No SMTP needed for local report-only execution. Edit `config/settings.yaml` to add/remove symbols, tune thresholds, select benchmark ETFs, and change the result count (1–10). Increasing the universe too quickly may result in upstream throttling. Local JSON cache in `.cache` expires after `cache_hours`; GitHub Actions caches this folder between runs on a best-effort basis. Financial data will only be as fresh as its underlying source, regardless of the job timestamp.

## Setup email securely (Gmail example)

Create a Gmail app password **only if your Google account supports app passwords** (normally requires two-step verification). Do not use your primary Gmail password. Do not commit `.env` or credentials. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret** and create:

| Secret | Example |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USER` | `you@gmail.com` |
| `SMTP_PASSWORD` | Gmail app password |
| `EMAIL_TO` | `destination@gmail.com` |
| `EMAIL_FROM` | `you@gmail.com` (optional; typically same as authenticated user) |

For local sending, set these environment variables in your shell (do not source an untrusted `.env` file). Then run:

```bash
python -m src.main --send
```

If SMTP credentials are absent, GitHub's email step fails rather than pretending delivery. The HTML and JSON reports are still uploaded as a GitHub Actions artifact by `if: always()` (if generated). SMTP acceptance does not prove inbox delivery; check spam and provider limits.

## Deploy GitHub Actions

1. Create a new GitHub repository named `daily-analyst-screener` in your account (private is recommended for personal-use research).
2. From this folder:

   ```bash
   git init
   git add .
   git commit -m "Initial daily stock screener"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/daily-analyst-screener.git
   git push -u origin main
   ```

3. Add the SMTP Actions secrets above.
4. Open **Actions → Daily Analyst Screen → Run workflow** to test manually; view logs and downloadable `daily-screen-report` artifact.
5. The workflow runs daily on the default branch. **`0 7 * * *` is 07:00 UTC** (3 AM EDT/2 AM EST), not 7 AM New York time. To use 7 AM New York time where supported, change the schedule to:

   ```yaml
   schedule:
     - cron: '0 7 * * *'
       timezone: America/New_York
   ```

   GitHub may delay or skip cron runs under load. Public repositories can have cron disabled after inactivity; review GitHub's up-to-date policy. A 7 AM run occurs before the U.S. stock market opens, so last-session close is typical, not a live market opening quote.

## Extend

The market provider is isolated in `src/data/provider.py`; implement another API/data source respecting its license, with `history()` and `fundamentals()` returning the documented normalized dictionaries. For verifiable insider net purchases, use SEC filings or a compliant provider that includes dated trades, compute the net bought amount over a specified lookback, and explicitly track source coverage. Use stale-data checks, financial statement period labels, unit-normalized FCF, turnover/liquidity and analyst publication dates before treating this as a rigorous quantitative strategy. Broaden ticker coverage by maintaining an externally validated universe list. Add rate-limit tests and mocked provider fixtures before production expansion.

## Files

- `src/data/provider.py`: upstream requests, retries, normalization and TTL cache.
- `src/analysis/screener.py`: filters, relative strength, historical levels and ranking.
- `src/report/render.py`: escaped HTML and JSON artifacts.
- `src/report/mail.py`: SSL SMTP.
- `src/main.py`: CLI, validation, logs and job orchestration.
- `tests/`: offline unit tests.
- `.github/workflows/daily-screen.yml`: daily automation and artifact.

## Data use and risk

`yfinance` is not affiliated with Yahoo; its documentation calls out Yahoo Finance data as intended for **personal use** and requires reviewing Yahoo's terms. This project does not scrape Finviz or MarketWatch pages, circumvent authentication, or promise authorized automated extraction under every provider policy. **The fact that a service is publicly accessible does not automatically authorize all automated uses.** Review current upstream terms before enabling hosted automation or sharing content. Research only; not personalized financial advice.
