import argparse
import json
from pathlib import Path

YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def require_frozen(root: Path):
    freeze_root = root / 'reports/content-freeze'
    board = load_json(freeze_root / '2007-2012-production-board.json')
    if not board.get('content_frozen'):
        raise SystemExit('production blocked: content_frozen is not true')
    remaining = list(board.get('freeze_gate_remaining') or [])
    if remaining:
        raise SystemExit(f'production blocked: freeze_gate_remaining={remaining}')
    missing = []
    for year in YEARS:
        for unit in UNITS:
            if not (freeze_root / str(year) / f'{unit}.candidate.json').is_file():
                missing.append(f'{year}/{unit}')
    if missing:
        raise SystemExit('production blocked: missing candidates: ' + ', '.join(missing))
    for year in YEARS:
        mapping_path = root / 'content-pipeline/curated/bilingual-highlights' / f'{year}.json'
        if not mapping_path.is_file():
            raise SystemExit(
                f'production blocked: bilingual-highlights/{year}.json is missing'
            )
        mapping = load_json(mapping_path)
        articles = mapping.get('articles')
        has_sentence_mapping = (
            isinstance(articles, dict)
            and any(isinstance(sentence_map, dict) and bool(sentence_map) for sentence_map in articles.values())
        )
        if int(mapping.get('year', -1)) != year or not has_sentence_mapping:
            raise SystemExit(
                f'production blocked: bilingual-highlights/{year}.json is invalid'
            )
    return board


def compile_year(root: Path, output_dir: Path, inventory: dict, board: dict, year: int):
    y = str(year)
    source_meta = inventory['years'][y]
    actor_plan = board['actor_plan'][y]
    articles = []
    for unit in UNITS:
        path = root / 'reports/content-freeze' / y / f'{unit}.candidate.json'
        candidate = load_json(path)
        if int(candidate.get('year', -1)) != year:
            raise SystemExit(f'{year}/{unit}: candidate year mismatch')
        article = candidate.get('article') or {}
        if article.get('id') != unit:
            raise SystemExit(f'{year}/{unit}: candidate article id mismatch')
        if not article.get('rows'):
            raise SystemExit(f'{year}/{unit}: candidate rows missing')
        if not (candidate.get('qa') or {}).get('source_scope_verified'):
            raise SystemExit(f'{year}/{unit}: source_scope_verified is not true')
        planned_actor = str(actor_plan[unit]).zfill(2)
        candidate_actor = str(article.get('actor', planned_actor)).zfill(2)
        if candidate_actor != planned_actor:
            raise SystemExit(
                f'{year}/{unit}: actor mismatch candidate={candidate_actor} plan={planned_actor}'
            )
        candidate_sha = (candidate.get('qa') or {}).get('source_sha256')
        if candidate_sha and candidate_sha != source_meta['source_sha256']:
            raise SystemExit(f'{year}/{unit}: source_sha256 mismatch')
        candidate_pdf = (candidate.get('qa') or {}).get('source_pdf')
        if candidate_pdf and candidate_pdf != source_meta['source_filename']:
            raise SystemExit(f'{year}/{unit}: source_filename mismatch')
        articles.append({
            'id': unit,
            'section_type': article['section_type'],
            'title': article['title'],
            'pages': article.get('pages', []),
            'actor': planned_actor,
            'context': article['context'],
            'rows': article['rows'],
            'editorial_status': 'reviewed_candidate',
        })
    vocabulary_path = root / 'reports/content-freeze' / y / 'vocabulary-1-9.json'
    if not vocabulary_path.is_file():
        raise SystemExit(f'{year}/vocabulary-1-9.json: reviewed vocabulary is missing')
    vocabulary_doc = load_json(vocabulary_path)
    if int(vocabulary_doc.get('year', -1)) != year:
        raise SystemExit(f'{year}/vocabulary-1-9.json: year mismatch')
    if vocabulary_doc.get('scale') != 'project-curated-1-9-v1':
        raise SystemExit(f'{year}/vocabulary-1-9.json: unsupported vocabulary scale')
    if (vocabulary_doc.get('qa') or {}).get('status') != 'reviewed':
        raise SystemExit(f'{year}/vocabulary-1-9.json: vocabulary QA is not reviewed')
    vocabulary = vocabulary_doc.get('vocabulary') or {}
    if not vocabulary:
        raise SystemExit(f'{year}/vocabulary-1-9.json: vocabulary is empty')
    for lemma, entry in vocabulary.items():
        if not isinstance(entry, list) or len(entry) < 2 or not isinstance(entry[0], int) or not 1 <= entry[0] <= 9:
            raise SystemExit(f'{year}/vocabulary-1-9.json: invalid entry for {lemma}')

    source = {
        'year': year,
        'source_filename': source_meta['source_filename'],
        'source_sha256': source_meta['source_sha256'],
        'method': 'compiled verbatim from frozen reviewed candidates',
        'unresolved_sections': [],
        'vocabulary': vocabulary,
        'articles': articles,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f'{year}.json'
    target.write_text(json.dumps(source, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir or (root / 'content-pipeline/curated')
    board = require_frozen(root)
    inventory = load_json(root / 'reports/extraction/2007-2012-article-inventory.json')
    written = [compile_year(root, output_dir, inventory, board, year) for year in YEARS]
    print(json.dumps({'years': list(YEARS), 'articles': 42, 'written': [str(p) for p in written]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
