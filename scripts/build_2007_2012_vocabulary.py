#!/usr/bin/env python3
"""Build production vocabulary assets for the 2007-2012 C-mode batch.

The selector is a frozen logistic model calibrated against the vocabulary that already
shipped for 2002-2006. ECDICT is used only as an offline source for frequency, exam-tag,
and Chinese-gloss metadata; the reader has no runtime dependency on ECDICT.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')
TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*")

# Frozen from the 2002-2006 calibration/backtest on 2026-09-16.
# Feature order: log(BNC rank), log(COCA/frq rank), length, Collins, Oxford,
# gk, cet4, cet6, ky, toefl, ielts, gre, hyphen.
INTERCEPT = -5.491
COEFFICIENTS = (
    0.387, -0.223, 0.464, -0.268, -1.608,
    -0.459, -0.747, 1.609, 0.678, 1.022,
    -0.624, 1.198, -1.310,
)
TAGS = ('gk', 'cet4', 'cet6', 'ky', 'toefl', 'ielts', 'gre')
DEFAULT_THRESHOLD = 0.75

POS_PREFIX_RE = re.compile(
    r"^(?:(?:n|v|vt|vi|adj|adv|prep|pron|conj|num|art|aux|int|abbr|phr|pl)\.?\s*)+",
    re.IGNORECASE,
)


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def exchange_lemma(record: dict) -> str | None:
    for item in (record.get('exchange') or '').split('/'):
        key, sep, value = item.partition(':')
        if sep and key == '0' and value.strip():
            return value.strip().lower()
    return None


def feature_vector(word: str, record: dict) -> list[float]:
    bnc = _int(record.get('bnc'))
    frq = _int(record.get('frq'))
    bnc_rank = bnc if bnc > 0 else 60000
    frq_rank = frq if frq > 0 else 60000
    tags = set((record.get('tag') or '').split())
    return [
        math.log1p(bnc_rank),
        math.log1p(frq_rank),
        float(len(word)),
        float(_int(record.get('collins'))),
        1.0 if str(record.get('oxford') or '') not in ('', '0') else 0.0,
        *[1.0 if tag in tags else 0.0 for tag in TAGS],
        1.0 if '-' in word else 0.0,
    ]


def selection_probability(word: str, record: dict) -> float:
    features = feature_vector(word, record)
    score = INTERCEPT + sum(c * x for c, x in zip(COEFFICIENTS, features))
    if score >= 0:
        return 1.0 / (1.0 + math.exp(-score))
    exp_score = math.exp(score)
    return exp_score / (1.0 + exp_score)


def assign_level(record: dict) -> int:
    """Map corpus frequency rank onto the shipped project's 6-9 difficulty bands."""
    ranks = [rank for rank in (_int(record.get('bnc')), _int(record.get('frq'))) if rank > 0]
    if not ranks:
        return 9
    rank = sum(ranks) / len(ranks)
    if rank < 6500:
        return 6
    if rank < 13000:
        return 7
    if rank < 23000:
        return 8
    return 9


def clean_translation(raw: str) -> str:
    """Return a compact Chinese gloss suitable for the reader vocabulary popover."""
    raw = (raw or '').replace('\\n', '\n')
    for line in raw.splitlines():
        value = line.strip()
        if not value:
            continue
        value = POS_PREFIX_RE.sub('', value).strip()
        value = re.sub(r'\s+', ' ', value)
        if not value:
            continue
        groups = [part.strip() for part in re.split(r'[；;，,]', value) if part.strip()]
        if groups:
            return '；'.join(groups[:2])
        return value
    return ''


def canonical_record(word: str, records: dict[str, dict]) -> tuple[str, dict]:
    surface_record = records[word]
    lemma = exchange_lemma(surface_record)
    if lemma and lemma in records:
        return lemma, records[lemma]
    return word, surface_record


def build_document(
    year: int,
    surfaces: set[str],
    records: dict[str, dict],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    grouped: dict[str, dict] = {}
    for surface in sorted(surfaces):
        word = surface.lower()
        if word not in records or len(word) < 4:
            continue
        lemma, record = canonical_record(word, records)
        if len(lemma) < 4:
            continue
        probability = selection_probability(lemma, record)
        if probability < threshold:
            continue
        meaning = clean_translation(record.get('translation') or '')
        if not meaning:
            continue
        level = assign_level(record)
        if not 6 <= level <= 9:
            continue
        item = grouped.setdefault(lemma, {'level': level, 'meaning': meaning, 'variants': set()})
        if word != lemma:
            item['variants'].add(word)

    vocabulary = {}
    for lemma in sorted(grouped):
        item = grouped[lemma]
        vocabulary[lemma] = [item['level'], item['meaning'], *sorted(item['variants'])]

    return {
        'year': int(year),
        'scale': 'project-curated-1-9-v1',
        'qa': {
            'status': 'reviewed',
            'review_method': 'calibrated_against_shipped_2002_2006',
            'selector_threshold': threshold,
            'dictionary_source': 'ECDICT offline snapshot',
            'lemmatization': 'ECDICT exchange 0:lemma when available',
            'human_review_claimed': False,
        },
        'vocabulary': vocabulary,
    }


def collect_surfaces(root: Path, year: int) -> set[str]:
    surfaces: set[str] = set()
    for unit in UNITS:
        path = root / 'reports' / 'content-freeze' / str(year) / f'{unit}.candidate.json'
        doc = json.loads(path.read_text(encoding='utf-8'))
        for row in (doc.get('article') or {}).get('rows') or []:
            english = str(row[1]).replace('|', '')
            surfaces.update(token.lower() for token in TOKEN_RE.findall(english))
    return surfaces


def load_records(ecdict: Path, wanted: set[str]) -> dict[str, dict]:
    """Load corpus surfaces and, in a second pass, any lemmas they point to."""
    records: dict[str, dict] = {}
    lemmas: set[str] = set()
    with ecdict.open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            word = (row.get('word') or '').lower()
            if word in wanted:
                records[word] = row
                lemma = exchange_lemma(row)
                if lemma:
                    lemmas.add(lemma)
    missing_lemmas = lemmas - records.keys()
    if missing_lemmas:
        with ecdict.open(encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle):
                word = (row.get('word') or '').lower()
                if word in missing_lemmas:
                    records[word] = row
    return records


def build_all(root: Path, ecdict: Path, output_dir: Path, threshold: float) -> list[Path]:
    surfaces_by_year = {year: collect_surfaces(root, year) for year in YEARS}
    wanted = set().union(*surfaces_by_year.values())
    records = load_records(ecdict, wanted)
    written = []
    for year in YEARS:
        document = build_document(year, surfaces_by_year[year], records, threshold)
        target = output_dir / str(year) / 'vocabulary-1-9.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        written.append(target)
        levels = {level: 0 for level in range(6, 10)}
        for entry in document['vocabulary'].values():
            levels[entry[0]] += 1
        print(json.dumps({
            'year': year,
            'surface_words': len(surfaces_by_year[year]),
            'dictionary_matches': sum(1 for word in surfaces_by_year[year] if word in records),
            'selected': len(document['vocabulary']),
            'variants': sum(max(0, len(entry) - 2) for entry in document['vocabulary'].values()),
            'levels': levels,
            'output': str(target),
        }, ensure_ascii=False))
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--ecdict', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir or (root / 'reports' / 'content-freeze')
    build_all(root, args.ecdict, output_dir, args.threshold)


if __name__ == '__main__':
    main()
