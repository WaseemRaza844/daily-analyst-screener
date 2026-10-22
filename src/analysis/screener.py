"""Deterministic filters; never fabricate unavailable analyst or cash-flow data."""
from __future__ import annotations
from dataclasses import dataclass
from statistics import mean


@dataclass
class ScreenResult:
    ticker: str
    name: str
    price: float
    rating: str
    target: float
    support: float
    resistance: float
    growth: float
    relative_strength: float
    fcf: list[float]
    institutional_percent: float | None
    reason: str
    score: float
    links: dict
    indicators: dict | None = None
    analyst_count: int | None = None


def pct_change(history, lookback=63):
    if len(history) < lookback + 1:
        return None
    old = history[-(lookback + 1)]['close']
    return (history[-1]['close'] / old - 1) * 100 if old > 0 else None


def technical_zones(history):
    """20/60-day extrema of historical bars, excluding latest bar."""
    if len(history) < 65:
        return None
    bars = history[-61:-1]
    support = min(x['low'] for x in bars[-20:])
    resistance = max(x['high'] for x in bars)
    return support, resistance


def evaluate(ticker, meta, prices, benchmark, cfg):
    if len(prices) < 65 or len(benchmark) < 65:
        return None
    price = prices[-1]['close']
    if price <= 0 or price >= cfg['max_price']:
        return None
    rating = str(meta.get('rating') or '').lower().replace(' ', '_').replace('-', '_')
    if rating not in cfg['allowed_ratings']:
        return None
    count = meta.get('analyst_count')
    target = meta.get('target')
    if count is None or count < cfg['min_analyst_count'] or target is None or target <= 0:
        return None
    upside = (target / price - 1) * 100
    if upside < cfg['min_target_upside_pct']:
        return None
    growth = meta.get('revenue_growth')
    if growth is None or growth < cfg['min_revenue_growth']:
        return None
    relative = pct_change(prices)
    peer = pct_change(benchmark)
    if relative is None or peer is None:
        return None
    relative -= peer
    if relative < cfg['min_relative_strength_3m_pct']:
        return None
    fcf = meta.get('fcf') or []
    if cfg['require_positive_fcf_trend'] and not (len(fcf) >= 2 and fcf[0] > 0 and fcf[0] > fcf[1]):
        return None
    holding = meta.get('institutional_percent')
    if cfg['require_institutional_or_insider_buying']:
        # Ownership percentage is not evidence of net buying; reject until a buying-flow provider is added.
        return None
    zones = technical_zones(prices)
    if zones is None:
        return None
    support, resistance = zones
    if support <= 0 or resistance <= 0:
        return None
    score = 0.30 * min(upside, 100) + 0.35 * min(max(growth * 100, 0), 100) + 0.35 * min(max(relative, 0), 100)
    reason = (f'Public analyst consensus: {rating.replace("_", " ")}, {int(count)} analysts; '
              f'revenue growth {growth * 100:.1f}% and 3-month benchmark-relative strength {relative:+.1f} pp. '
              f'Latest annual free cash flow is positive and higher than the prior annual observation.')
    return ScreenResult(ticker, meta['name'], price, rating.replace('_', ' ').title(), target,
                        support, resistance, growth, relative, fcf, holding, reason, score,
                        {k: meta[k] for k in ('source', 'analysis_source', 'cash_source', 'financials_source')},
                        meta.get('valuation') or {}, int(count))


def scan(provider, cfg, logger):
    selected = []
    errors = []
    history_period = cfg['lookback_period']
    benchmark_cache = {}
    tickers = list(dict.fromkeys(cfg['universe']))[:cfg['max_tickers_per_run']]
    for ix, ticker in enumerate(tickers, start=1):
        try:
            meta = provider.fundamentals(ticker)
            prices = provider.history(ticker, history_period)
            sector = meta.get('sector')
            symbol = cfg['sector_benchmarks'].get(sector, cfg['fallback_benchmark'])
            if symbol not in benchmark_cache:
                benchmark_cache[symbol] = provider.history(symbol, history_period)
            result = evaluate(ticker, meta, prices, benchmark_cache[symbol], cfg)
            if result:
                selected.append(result)
            logger.info('%s/%s %s: %s', ix, len(tickers), ticker, 'PASS' if result else 'excluded')
        except Exception as exc:
            logger.warning('%s: %s', ticker, exc)
            errors.append({'ticker': ticker, 'error': str(exc)})
    selected.sort(key=lambda x: x.score, reverse=True)
    return selected[:cfg['max_results']], errors, len(tickers)
