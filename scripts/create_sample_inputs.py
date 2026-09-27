"""Create an explicitly dated sample portfolio without changing original sources."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def create(destination: Path, as_of: str):
    date.fromisoformat(as_of)
    destination.mkdir(parents=True, exist_ok=False)
    for folder in ('fixtures', 'mock-drive', 'mock-sheets'):
        shutil.copytree(ROOT / folder, destination / folder)
    path = destination / 'fixtures/portfolio.json'
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    portfolio = json.loads(path.read_text())
    portfolio['as_of'] = as_of
    for position in portfolio['positions']:
        position['price_date'] = as_of
    portfolio['sample_provenance'] = (
        'Explicit dated sample prices for a lifecycle demonstration. '
        'The values are mocked and are not refreshed market observations.')
    path.write_text(json.dumps(portfolio, indent=2) + '\n')
    (destination / 'sample-provenance.json').write_text(json.dumps({
        'sample_date': as_of, 'description': portfolio['sample_provenance'],
        'original_portfolio_sha256': original_hash,
        'sample_portfolio_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'automatically_refreshes': False,
    }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--as-of', required=True, help='Explicit date for mocked demo prices, not a market-data refresh')
    args = parser.parse_args()
    create(args.out.expanduser().absolute(), args.as_of)
    print(args.out)
