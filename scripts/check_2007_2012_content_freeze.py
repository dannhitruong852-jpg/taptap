import json, sys
from pathlib import Path

YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')
root = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/content-freeze')
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
}
print(json.dumps(summary, ensure_ascii=False))

if board.get('content_frozen') and (len(ready) != 42 or partial or missing or errors):
    raise SystemExit('content_frozen=true but candidate set is incomplete/invalid')
