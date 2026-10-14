"""Run: python -m src.main [--send] [--config config/settings.yaml]."""
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
import yaml
from src.data.provider import YahooProvider
from src.analysis.screener import scan
from src.report.render import write_artifacts
from src.report.mail import send_mail


def main():
    parser = argparse.ArgumentParser(description='Personal-use daily analyst screener')
    parser.add_argument('--config', default='config/settings.yaml')
    parser.add_argument('--output', default='output')
    parser.add_argument('--send', action='store_true', help='Send report using configured SMTP secrets')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    log = logging.getLogger('screener')
    cfg = yaml.safe_load(Path(args.config).read_text(encoding='utf-8'))
    if not 1 <= cfg['max_results'] <= 10:
        raise ValueError('max_results must be between 1 and 10')
    if not cfg.get('universe'):
        raise ValueError('Ticker universe cannot be empty')
    provider = YahooProvider(ttl_hours=cfg['cache_hours'], delay=cfg['request_delay_seconds'])
    rows, errors, scanned = scan(provider, cfg, log)
    report_path = write_artifacts(rows, errors, scanned, args.output)
    log.info('Processed %d tickers, %d matches, %d provider errors', scanned, len(rows), len(errors))
    if args.send:
        subject = f'Analyst-Consensus Screener | {datetime.now(timezone.utc):%Y-%m-%d} | {len(rows)} matches'
        send_mail(report_path.read_text(encoding='utf-8'), subject)
        log.info('Email accepted by SMTP server')
    if errors and len(errors) == scanned:
        raise RuntimeError('All provider requests failed; inspect output/report.json')


if __name__ == '__main__':
    main()
