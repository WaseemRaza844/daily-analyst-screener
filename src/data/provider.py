"""Read-only personal-research market data provider with serialized TTL cache."""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import random
import time
from datetime import datetime, timezone
import math
import yfinance as yf

LOG = logging.getLogger(__name__)


def numeric(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def _series_values(frame, index):
    """Return annual/quarterly observations newest first; no zero filling."""
    if frame is None or frame.empty:
        return []
    for label in index:
        if label in frame.index:
            values = []
            for col in sorted(frame.columns, reverse=True):
                v = numeric(frame.loc[label, col])
                if v is not None:
                    values.append(v)
            if values:
                return values
    return []


def _normalize_frame(frame):
    if frame is None or frame.empty:
        return []
    result = []
    for idx, row in frame.iterrows():
        close = numeric(row.get('Close'))
        high = numeric(row.get('High'))
        low = numeric(row.get('Low'))
        if None not in (close, high, low):
            result.append({'date': str(idx)[:10], 'close': close, 'high': high, 'low': low})
    return result


class YahooProvider:
    def __init__(self, folder='.cache', ttl_hours=18, delay=1.5):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_hours * 3600
        self.delay = delay
        self._last_request = 0.0

    def _wait(self):
        remaining = self.delay - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request = time.monotonic()

    def _cached(self, key, fetcher):
        path = self.folder / (key.replace('/', '_') + '.json')
        if path.exists() and time.time() - path.stat().st_mtime < self.ttl:
            try:
                return json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                LOG.warning('Cache invalid for %s', key)
        last_error = None
        for attempt in range(3):
            try:
                self._wait()
                result = fetcher()
                if result:
                    tmp = path.with_suffix('.tmp')
                    tmp.write_text(json.dumps(result, allow_nan=False), encoding='utf-8')
                    os.replace(tmp, path)
                return result
            except Exception as exc:
                last_error = exc
                LOG.warning('Provider %s attempt %s failed: %s', key, attempt + 1, exc)
                if attempt < 2:
                    time.sleep(min(3 * 2 ** attempt + random.random(), 10))
        raise RuntimeError(f'Data unavailable for {key}: {last_error}')

    def history(self, ticker, period='1y'):
        def load():
            t = yf.Ticker(ticker)
            return _normalize_frame(t.history(period=period, auto_adjust=True))
        return self._cached(f'history_{ticker}_{period}', load)

    def fundamentals(self, ticker):
        def load():
            t = yf.Ticker(ticker)
            info = t.info or {}
            targets = {}
            try:
                targets = t.analyst_price_targets or {}
            except Exception as exc:
                LOG.info('Analyst targets not available for %s: %s', ticker, exc)
            cash = _series_values(t.cashflow, ['Free Cash Flow'])
            if not cash:
                operating = _series_values(t.cashflow, ['Operating Cash Flow', 'Total Cash From Operating Activities'])
                capital = _series_values(t.cashflow, ['Capital Expenditure'])
                if operating and capital and len(operating) == len(capital):
                    cash = [a + b if b <= 0 else a - b for a, b in zip(operating, capital)]
            sales = _series_values(t.financials, ['Total Revenue'])
            growth = numeric(info.get('revenueGrowth'))
            if growth is None and len(sales) >= 2 and sales[1] > 0:
                growth = sales[0] / sales[1] - 1
            return {
                'sector': info.get('sector'),
                'name': info.get('shortName') or ticker,
                'rating': info.get('recommendationKey'),
                'analyst_count': numeric(info.get('numberOfAnalystOpinions')),
                'target': numeric(targets.get('mean') or info.get('targetMeanPrice')),
                'revenue_growth': growth,
                'fcf': cash[:3],
                'institutional_percent': numeric(info.get('heldPercentInstitutions')),
                'insider_percent': numeric(info.get('heldPercentInsiders')),
                'valuation': {key: numeric(info.get(field)) for key, field in {
                    'pe': 'trailingPE', 'forward_pe': 'forwardPE',
                    'peg': 'trailingPegRatio', 'eps': 'trailingEps',
                    'forward_eps': 'forwardEps', 'price_to_book': 'priceToBook',
                    'market_cap': 'marketCap', 'profit_margin': 'profitMargins',
                    'operating_margin': 'operatingMargins', 'roe': 'returnOnEquity',
                    'debt_to_equity': 'debtToEquity', 'current_ratio': 'currentRatio',
                    'earnings_growth': 'earningsGrowth', 'dividend_yield': 'dividendYield',
                    'beta': 'beta', 'price_to_sales': 'priceToSalesTrailing12Months'
                }.items()},
                'source': f'https://finance.yahoo.com/quote/{ticker}/',
                'financials_source': f'https://finance.yahoo.com/quote/{ticker}/financials/',
                'cash_source': f'https://finance.yahoo.com/quote/{ticker}/cash-flow/',
                'analysis_source': f'https://finance.yahoo.com/quote/{ticker}/analysis/'
            }
        return self._cached(f'fundamentals_{ticker}', load)
