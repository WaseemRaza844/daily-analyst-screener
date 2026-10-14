import unittest
from src.analysis.screener import evaluate, technical_zones, pct_change
from src.report.render import render


def bars(mult=1):
    return [{'date': f'd{i}', 'close': (10 + i * .01) * mult,
             'high': (10.2 + i * .01) * mult, 'low': (9.8 + i * .01) * mult} for i in range(90)]

CFG = dict(max_price=20, allowed_ratings=['buy', 'strong_buy'], min_analyst_count=3,
           min_target_upside_pct=10, min_revenue_growth=.08,
           min_relative_strength_3m_pct=0, require_positive_fcf_trend=True,
           require_institutional_or_insider_buying=False)
META = dict(name='Example', rating='buy', analyst_count=5, target=18,
            revenue_growth=.30, fcf=[20, 10], institutional_percent=.4,
            source='https://example.org', cash_source='https://example.org',
            analysis_source='https://example.org', financials_source='https://example.org')


class ScreenerTests(unittest.TestCase):
    def test_valid(self):
        r = evaluate('EX', META, bars(), bars(.97), CFG)
        self.assertIsNotNone(r)
        self.assertGreater(r.resistance, r.support)

    def test_no_invented_rating(self):
        self.assertIsNone(evaluate('EX', {**META, 'rating': None}, bars(), bars(.97), CFG))

    def test_missing_cashflow_excluded(self):
        self.assertIsNone(evaluate('EX', {**META, 'fcf': []}, bars(), bars(.97), CFG))

    def test_buying_claim_not_substituted_with_ownership(self):
        self.assertIsNone(evaluate('EX', META, bars(), bars(.97), {**CFG, 'require_institutional_or_insider_buying': True}))

    def test_insufficient_prices(self):
        self.assertIsNone(evaluate('EX', META, bars()[:3], bars(), CFG))

    def test_empty_html(self):
        self.assertIn('No stocks passed', render([], [], 10))

    def test_html_escaping(self):
        row = evaluate('EX', {**META, 'name': '<script>'}, bars(), bars(.97), CFG)
        self.assertNotIn('<script>', render([row], [], 1))


if __name__ == '__main__':
    unittest.main()
