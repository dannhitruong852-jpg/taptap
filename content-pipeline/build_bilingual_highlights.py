"""Compile reviewed bilingual highlight mappings into reader-ready JSON and QA reports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bilingual_highlights import validate_bilingual_highlights

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def compile_mapping(mapping: dict, docs: list[dict], *, root: Path = ROOT) -> tuple[dict, dict]:
    report = validate_bilingual_highlights(mapping, docs)
    if report['errors']:
        preview = json.dumps(report['errors'][:10], ensure_ascii=False)
        raise ValueError(f"bilingual highlight validation failed: {preview}")
    year = int(mapping['year'])
    canonical = mapping
    write_json(root / f'kaoyan-reader-v1/content/{year}/bilingual-highlights.json', canonical)
    write_json(root / f'reports/bilingual-highlights/{year}.json', report)
    return canonical, report


def load_docs(root: Path, year: int) -> list[dict]:
    article_dir = root / f'kaoyan-reader-v1/content/{year}/c'
    paths = sorted(article_dir.glob('*.json'))
    if not paths:
        raise FileNotFoundError(f'no compiled article JSON for {year}: {article_dir}')
    return [json.loads(path.read_text(encoding='utf-8')) for path in paths]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--mapping', type=Path)
    args = parser.parse_args()
    mapping_path = args.mapping or ROOT / f'content-pipeline/curated/bilingual-highlights/{args.year}.json'
    if not mapping_path.is_file():
        raise FileNotFoundError(f'no reviewed bilingual mapping for {args.year}: {mapping_path}')
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    if int(mapping.get('year', -1)) != args.year:
        raise ValueError('bilingual mapping year disagrees with --year')
    docs = load_docs(ROOT, args.year)
    _, report = compile_mapping(mapping, docs, root=ROOT)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
