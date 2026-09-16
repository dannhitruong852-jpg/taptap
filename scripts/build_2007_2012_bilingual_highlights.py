#!/usr/bin/env python3
"""Author exact bilingual highlight skeletons for the 2007-2012 C-mode batch.

This module only auto-accepts a Chinese span when a dictionary gloss produces one
unique literal occurrence in the already reviewed sentence translation. Everything
else is emitted as unresolved editorial work instead of being guessed.
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
    # Prefer the longest unique phrase. If two distinct phrases of the same best length
    # point to different text, the choice is semantically ambiguous and remains unresolved.
    best_len = max(end - start for start, end, _ in matches)
    best = [item for item in matches if item[1] - item[0] == best_len]
    distinct = {(start, end, text) for start, end, text in best}
    if len(distinct) != 1:
        return []
    start, end, text = next(iter(distinct))
    return [{'start': start, 'end': end, 'text': text}]


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
                        'year': int(year),
                        'article_id': article_id,
                        'sentence_id': sentence_id,
                        'lemma': str(lemma),
                        'level': int(level),
                        'meaning': str(meaning),
                        'en_start': match.start(),
                        'en_end': match.end(),
                        'en_text': match.group(),
                        'en': english,
                        'zh': chinese,
                    })
    rows.sort(key=lambda row: (row['sentence_id'], row['en_start'], row['en_end'], row['lemma']))
    return rows


def build_article_mapping(year: int, candidate: dict, vocabulary: dict) -> tuple[dict, list[dict]]:
    article_id = str((candidate.get('article') or {}).get('id', ''))
    mapping = {'version': 1, 'year': int(year), 'articles': {article_id: {}}, 'exceptions': []}
    unresolved: list[dict] = []
    for row in collect_occurrences(year, candidate, vocabulary):
        spans = literal_zh_spans(row)
        if not spans:
            unresolved.append(row)
            continue
        entry = {
            'en_start': row['en_start'],
            'en_end': row['en_end'],
            'en_text': row['en_text'],
            'zh_spans': spans,
        }
        mapping['articles'][article_id].setdefault(row['sentence_id'], []).append(entry)
    return mapping, unresolved


def merge_mapping(target: dict, partial: dict) -> None:
    for article_id, sentence_map in (partial.get('articles') or {}).items():
        article_target = target['articles'].setdefault(article_id, {})
        for sentence_id, entries in sentence_map.items():
            article_target.setdefault(sentence_id, []).extend(entries)


def build_year(root: Path, year: int, vocabulary_path: Path) -> tuple[dict, list[dict]]:
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
    return mapping, unresolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--vocabulary', type=Path, required=True)
    parser.add_argument('--mapping-output', type=Path, required=True)
    parser.add_argument('--unresolved-output', type=Path, required=True)
    args = parser.parse_args()
    mapping, unresolved = build_year(args.root.resolve(), args.year, args.vocabulary)
    args.mapping_output.parent.mkdir(parents=True, exist_ok=True)
    args.unresolved_output.parent.mkdir(parents=True, exist_ok=True)
    args.mapping_output.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.unresolved_output.write_text(json.dumps({'year': args.year, 'count': len(unresolved), 'occurrences': unresolved}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    mapped = sum(len(entries) for sentence_map in mapping['articles'].values() for entries in sentence_map.values())
    print(json.dumps({'year': args.year, 'mapped': mapped, 'unresolved': len(unresolved)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
