import argparse
import json
from pathlib import Path

YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def inspect(root: Path):
    freeze = root / 'reports/content-freeze'
    board = load_json(freeze / '2007-2012-production-board.json')
    ready_candidates = []
    partial_candidates = []
    missing_candidates = []
    candidate_errors = []
    missing_vocabulary = []
    vocabulary_errors = []
    missing_bilingual = []
    bilingual_errors = []

    for year in YEARS:
        yd = freeze / str(year)
        for unit in UNITS:
            candidate = yd / f'{unit}.candidate.json'
            if candidate.is_file():
                try:
                    doc = load_json(candidate)
                    article = doc.get('article') or {}
                    if int(doc.get('year', -1)) != year or article.get('id') != unit or not article.get('rows'):
                        candidate_errors.append(f'{year}/{unit}')
                    else:
                        ready_candidates.append(f'{year}/{unit}')
                except Exception:
                    candidate_errors.append(f'{year}/{unit}')
            elif list(yd.glob(f'{unit}.candidate.part*.json')):
                partial_candidates.append(f'{year}/{unit}')
            else:
                missing_candidates.append(f'{year}/{unit}')

        vocabulary = yd / 'vocabulary-1-9.json'
        if not vocabulary.is_file():
            missing_vocabulary.append(f'{year}/vocabulary-1-9.json')
        else:
            try:
                doc = load_json(vocabulary)
                entries = doc.get('vocabulary') or {}
                valid = (
                    int(doc.get('year', -1)) == year
                    and doc.get('scale') == 'project-curated-1-9-v1'
                    and (doc.get('qa') or {}).get('status') == 'reviewed'
                    and bool(entries)
                    and all(
                        isinstance(entry, list)
                        and len(entry) >= 2
                        and isinstance(entry[0], int)
                        and 1 <= entry[0] <= 9
                        for entry in entries.values()
                    )
                )
                if not valid:
                    vocabulary_errors.append(f'{year}/vocabulary-1-9.json')
            except Exception:
                vocabulary_errors.append(f'{year}/vocabulary-1-9.json')

        mapping = root / 'content-pipeline/curated/bilingual-highlights' / f'{year}.json'
        if not mapping.is_file():
            missing_bilingual.append(f'{year}.json')
        else:
            try:
                doc = load_json(mapping)
                if int(doc.get('year', -1)) != year or not doc.get('articles'):
                    bilingual_errors.append(f'{year}.json')
            except Exception:
                bilingual_errors.append(f'{year}.json')

    frozen = bool(board.get('content_frozen'))
    remaining = list(board.get('freeze_gate_remaining') or [])
    ready = (
        frozen
        and not remaining
        and len(ready_candidates) == 42
        and not partial_candidates
        and not missing_candidates
        and not candidate_errors
        and not missing_vocabulary
        and not vocabulary_errors
        and not missing_bilingual
        and not bilingual_errors
    )
    return {
        'batch': '2007-2012',
        'ready': ready,
        'content_frozen': frozen,
        'freeze_gate_remaining': remaining,
        'candidate_ready': len(ready_candidates),
        'candidate_partial': len(partial_candidates),
        'candidate_missing': len(missing_candidates),
        'candidate_errors': candidate_errors,
        'partial_candidates': partial_candidates,
        'missing_candidates': missing_candidates,
        'missing_vocabulary': missing_vocabulary,
        'vocabulary_errors': vocabulary_errors,
        'missing_bilingual': missing_bilingual,
        'bilingual_errors': bilingual_errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--require-ready', action='store_true')
    args = parser.parse_args()
    report = inspect(args.root.resolve())
    print(json.dumps(report, ensure_ascii=False))
    if args.require_ready and not report['ready']:
        raise SystemExit('production not ready: see preflight report above')


if __name__ == '__main__':
    main()
