#!/usr/bin/env python3
"""Author exact bilingual highlights for the 2007-2012 C-mode batch.

Literal dictionary matches are accepted only when unique. Semantic overrides are explicit,
occurrence-specific editorial choices and are converted to offsets only after verifying that
the requested Chinese substring actually exists at the requested occurrence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


def gloss_candidates(meaning: str) -> list[str]:
    values: list[str] = []
    for value in re.split(r'[；;，,、/]', meaning or ''):
        value = re.sub(r'[（(].*?[)）]', '', value).strip()
        value = re.sub(r'^(?:a|adj|adv|n|v|vt|vi|prep|pron|conj|num|art|aux|int|abbr|phr|t|i)\.\s*', '', value, flags=re.I)
        value = value.strip()
        if not value:
            continue
        for candidate in (value, value[:-1] if len(value) > 1 and value[-1] in '的地得' else ''):
            candidate = candidate.strip()
            if candidate and candidate not in values:
                values.append(candidate)
    return values


def literal_zh_spans(row: dict) -> list[dict]:
    zh = str(row.get('zh', ''))
    matches: list[tuple[int, int, str]] = []
    for phrase in gloss_candidates(str(row.get('meaning', ''))):
        positions = [m.start() for m in re.finditer(re.escape(phrase), zh)]
        if len(positions) == 1:
            start = positions[0]
            matches.append((start, start + len(phrase), phrase))
    if not matches:
        return []
    best_len = max(end - start for start, end, _ in matches)
    best = [item for item in matches if item[1] - item[0] == best_len]
    distinct = {(start, end, text) for start, end, text in best}
    if len(distinct) != 1:
        return []
    start, end, text = next(iter(distinct))
    return [{'start': start, 'end': end, 'text': text}]


def resolve_override_spans(row: dict, specs: list[dict]) -> list[dict]:
    zh = str(row.get('zh', ''))
    if not isinstance(specs, list) or not specs:
        raise ValueError('override must contain at least one Chinese span spec')
    spans = []
    for spec in specs:
        text = str(spec.get('text') or '')
        occurrence = int(spec.get('occurrence', 0))
        if not text or occurrence < 0:
            raise ValueError(f'invalid override spec: {spec!r}')
        positions = [m.start() for m in re.finditer(re.escape(text), zh)]
        if occurrence >= len(positions):
            raise ValueError(
                f'override span not found: text={text!r} occurrence={occurrence} positions={positions} zh={zh!r}'
            )
        start = positions[occurrence]
        spans.append({'start': start, 'end': start + len(text), 'text': text})
    return spans


def collect_occurrences(year: int, candidate: dict, vocabulary: dict) -> list[dict]:
    article = candidate.get('article') or {}
    article_id = str(article.get('id', ''))
    rows: list[dict] = []
    for number, source_row in enumerate(article.get('rows') or [], 1):
        english = str(source_row[1]).replace('|', '')
        chinese = str(source_row[2])
        sentence_id = f's{number:02d}'
        for lemma, entry in vocabulary.items():
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            level, meaning, *variants = entry
            if int(level) < 6:
                continue
            surfaces = []
            for surface in [lemma, *variants]:
                surface = str(surface)
                if surface and surface.lower() not in {x.lower() for x in surfaces}:
                    surfaces.append(surface)
            for surface in surfaces:
                pattern = re.compile(r'(?<![\w-])' + re.escape(surface) + r'(?![\w-])', re.I)
                for match in pattern.finditer(english):
                    rows.append({
                        'year': int(year), 'article_id': article_id, 'sentence_id': sentence_id,
                        'lemma': str(lemma), 'level': int(level), 'meaning': str(meaning),
                        'en_start': match.start(), 'en_end': match.end(), 'en_text': match.group(),
                        'en': english, 'zh': chinese,
                    })
    rows.sort(key=lambda row: (row['sentence_id'], row['en_start'], row['en_end'], row['lemma']))
    return rows


def _entry(row: dict, spans: list[dict]) -> dict:
    return {'en_start': row['en_start'], 'en_end': row['en_end'], 'en_text': row['en_text'], 'zh_spans': spans}


def build_article_mapping(year: int, candidate: dict, vocabulary: dict) -> tuple[dict, list[dict]]:
    article_id = str((candidate.get('article') or {}).get('id', ''))
    mapping = {'version': 1, 'year': int(year), 'articles': {article_id: {}}, 'exceptions': []}
    unresolved: list[dict] = []
    for row in collect_occurrences(year, candidate, vocabulary):
        spans = literal_zh_spans(row)
        if not spans:
            unresolved.append(row)
            continue
        mapping['articles'][article_id].setdefault(row['sentence_id'], []).append(_entry(row, spans))
    return mapping, unresolved


def merge_mapping(target: dict, partial: dict) -> None:
    for article_id, sentence_map in (partial.get('articles') or {}).items():
        article_target = target['articles'].setdefault(article_id, {})
        for sentence_id, entries in sentence_map.items():
            article_target.setdefault(sentence_id, []).extend(entries)


def apply_overrides(mapping: dict, unresolved: list[dict], overrides: dict) -> list[dict]:
    overrides = {str(k): v for k, v in (overrides or {}).items()}
    valid_keys = {str(i) for i in range(1, len(unresolved) + 1)}
    extra = sorted(set(overrides) - valid_keys, key=lambda x: int(x) if x.isdigit() else 10**9)
    if extra:
        raise ValueError(f'override indexes outside unresolved inventory: {extra}')
    remaining = []
    for index, row in enumerate(unresolved, 1):
        specs = overrides.get(str(index))
        if specs is None:
            remaining.append(row)
            continue
        spans = resolve_override_spans(row, specs)
        mapping['articles'].setdefault(row['article_id'], {}).setdefault(row['sentence_id'], []).append(_entry(row, spans))
    for sentence_map in mapping['articles'].values():
        for entries in sentence_map.values():
            entries.sort(key=lambda entry: (entry['en_start'], entry['en_end'], entry['en_text']))
    return remaining


def build_year(root: Path, year: int, vocabulary_path: Path, override_path: Path | None = None) -> tuple[dict, list[dict]]:
    vocab_doc = json.loads(vocabulary_path.read_text(encoding='utf-8'))
    vocabulary = vocab_doc.get('vocabulary') or {}
    mapping = {'version': 1, 'year': int(year), 'articles': {}, 'exceptions': []}
    unresolved: list[dict] = []
    for unit in UNITS:
        candidate_path = root / 'reports' / 'content-freeze' / str(year) / f'{unit}.candidate.json'
        candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
        partial, pending = build_article_mapping(year, candidate, vocabulary)
        merge_mapping(mapping, partial)
        unresolved.extend(pending)
    if override_path:
        override_doc = json.loads(override_path.read_text(encoding='utf-8'))
        if int(override_doc.get('year', -1)) != int(year):
            raise ValueError(f'override year mismatch: {override_path}')
        unresolved = apply_overrides(mapping, unresolved, override_doc.get('overrides') or {})
    return mapping, unresolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--vocabulary', type=Path, required=True)
    parser.add_argument('--overrides', type=Path)
    parser.add_argument('--mapping-output', type=Path, required=True)
    parser.add_argument('--unresolved-output', type=Path, required=True)
    args = parser.parse_args()
    mapping, unresolved = build_year(args.root.resolve(), args.year, args.vocabulary, args.overrides)
    args.mapping_output.parent.mkdir(parents=True, exist_ok=True)
    args.unresolved_output.parent.mkdir(parents=True, exist_ok=True)
    args.mapping_output.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.unresolved_output.write_text(json.dumps({'year': args.year, 'count': len(unresolved), 'occurrences': unresolved}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    mapped = sum(len(entries) for sentence_map in mapping['articles'].values() for entries in sentence_map.values())
    print(json.dumps({'year': args.year, 'mapped': mapped, 'unresolved': len(unresolved)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
