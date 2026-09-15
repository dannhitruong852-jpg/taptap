import argparse
import json
from pathlib import Path

YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


def inspect(root: Path):
    board = json.loads((root / '2007-2012-production-board.json').read_text())
    ready, partial, missing, errors = [], [], [], []
    for year in YEARS:
        directory = root / str(year)
        for unit in UNITS:
            path = directory / f'{unit}.candidate.json'
            if path.is_file():
                try:
                    doc = json.loads(path.read_text())
                    if int(doc.get('year', -1)) != year:
                        errors.append(f'{path}: bad year')
                    article = doc.get('article', {})
                    if article.get('id') != unit:
                        errors.append(f'{path}: bad article id')
                    if not article.get('rows'):
                        errors.append(f'{path}: no rows')
                    ready.append(f'{year}/{unit}')
                except Exception as exc:
                    errors.append(f'{path}: {exc}')
            elif list(directory.glob(f'{unit}.candidate.part*.json')):
                partial.append(f'{year}/{unit}')
            else:
                missing.append(f'{year}/{unit}')
    summary = {
        'units': 42,
        'ready': len(ready),
        'partial': len(partial),
        'missing': len(missing),
        'errors': errors,
        'content_frozen': bool(board.get('content_frozen')),
        'freeze_gate_remaining': list(board.get('freeze_gate_remaining') or []),
    }
    return board, summary


def validate(board: dict, summary: dict, require_frozen: bool = False):
    incomplete = (
        summary['ready'] != 42
        or summary['partial']
        or summary['missing']
        or summary['errors']
    )
    if board.get('content_frozen') and incomplete:
        raise SystemExit('content_frozen=true but candidate set is incomplete/invalid')
    if require_frozen:
        if not board.get('content_frozen'):
            raise SystemExit('production blocked: content_frozen is not true')
        if incomplete:
            raise SystemExit('production blocked: candidate set is incomplete/invalid')
        if summary['freeze_gate_remaining']:
            raise SystemExit('production blocked: freeze_gate_remaining is not empty')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='reports/content-freeze')
    parser.add_argument('--require-frozen', action='store_true')
    args = parser.parse_args()
    board, summary = inspect(Path(args.root))
    print(json.dumps(summary, ensure_ascii=False))
    validate(board, summary, require_frozen=args.require_frozen)


if __name__ == '__main__':
    main()
