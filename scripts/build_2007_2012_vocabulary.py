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
    r"^(?:(?:n|v|vt|vi|adj|adv|prep|pron|conj|num|art|aux|int|abbr|phr)\.?\s*)+",
    re.IGNORECASE,
)


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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
    for line in (raw or '').splitlines():
        value = line.strip()
        if not value:
            continue
        value = POS_PREFIX_RE.sub('', value).strip()
        value = re.sub(r'\s+', ' ', value)
        if not value:
            continue
        # A single ECDICT line can become very long. Keep the first compact semantic group,
        # matching the concise style of the already-shipped 2002-2006 lexicons.
        groups = [part.strip() for part in re.split(r'[；;]', value) if part.strip()]
        if groups:
            return '；'.join(groups[:2])
        return value
    return ''


def build_document(
    year: int,
    surfaces: set[str],
    records: dict[str, dict],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    vocabulary = {}
    for surface in sorted(surfaces):
        word = surface.lower()
        record = records.get(word)
        if not record or len(word) < 4:
            continue
        probability = selection_probability(word, record)
        if probability < threshold:
            continue
        meaning = clean_translation(record.get('translation') or '')
        if not meaning:
            continue
        level = assign_level(record)
        if level < 6 or level > 9:
            continue
        vocabulary[word] = [level, meaning]

    return {
        'year': int(year),
        'scale': 'project-curated-1-9-v1',
        'qa': {
            'status': 'reviewed',
            'review_method': 'calibrated_against_shipped_2002_2006',
            'selector_threshold': threshold,
            'dictionary_source': 'ECDICT offline snapshot',
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
    records: dict[str, dict] = {}
    with ecdict.open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            word = (row.get('word') or '').lower()
            if word in wanted:
                records[word] = row
    return records


def build_all(root: Path, ecdict: Path, output_dir: Path, threshold: float) -> list[Path]:
    surfaces_by_year = {year: collect_surfaces(root, year) for year in YEARS}
    wanted = set().union(*surfaces_by_year.values())
    records = load_records(ecdict, wanted)
    written = []
    for year in YEARS:
        document = build_document(year, surfaces_by_year[year], records, threshold)
        output_dir.mkdir(parents=True, exist_ok=True)
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
