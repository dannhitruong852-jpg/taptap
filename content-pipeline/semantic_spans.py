"""Reviewed bilingual semantic spans for C v4 readalong.

Semantic groups are editorial data. They never rewrite the English source, Chinese
translation, or vocabulary annotations. English ranges use the exact word order
emitted by the forced-alignment transcript normalizer; Chinese ranges use source
character offsets and may be reordered relative to English when translation
requires it.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICE = ROOT / 'voice-pipeline'
if str(VOICE) not in sys.path:
    sys.path.insert(0, str(VOICE))

from alignment.normalize_transcript import normalize_transcript


def load_semantic_spans(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema_version') != 'c-v4-semantic-spans-1':
        raise ValueError('unsupported semantic span schema')
    if not isinstance(data.get('articles'), dict):
        raise ValueError('semantic span articles mapping is required')
    return data


def _significant_zh(ch: str) -> bool:
    if ch.isspace():
        return False
    return not unicodedata.category(ch).startswith('P')


def validate_semantic_groups(sentence: dict, groups: list[dict]) -> list[str]:
    errors: list[str] = []
    if not groups:
        return ['semantic groups must be nonempty']

    en_words = normalize_transcript(sentence.get('en', ''))
    en_coverage = [0] * len(en_words)
    zh = sentence.get('zh', '')
    zh_coverage = [0] * len(zh)
    previous_zh_end = 0
    seen_ids = set()

    for pos, group in enumerate(groups):
        gid = group.get('id')
        if not gid or gid in seen_ids:
            errors.append(f'group {pos}: id must be unique and nonempty')
        seen_ids.add(gid)
        try:
            es = int(group['en_word_start']); ee = int(group['en_word_end'])
            zs = int(group['zh_char_start']); ze = int(group['zh_char_end'])
        except (KeyError, TypeError, ValueError):
            errors.append(f'group {gid or pos}: invalid range fields')
            continue

        if not (0 <= es < ee <= len(en_words)):
            errors.append(f'group {gid or pos}: invalid English word range {es}:{ee}')
        else:
            for i in range(es, ee):
                en_coverage[i] += 1

        if not (0 <= zs < ze <= len(zh)):
            errors.append(f'group {gid or pos}: invalid Chinese character range {zs}:{ze}')
        else:
            if zs < previous_zh_end:
                errors.append(f'group {gid or pos}: Chinese spans are not ordered')
            previous_zh_end = ze
            for i in range(zs, ze):
                zh_coverage[i] += 1

    for i, count in enumerate(en_coverage):
        if count != 1:
            errors.append(f'English word {i} coverage is {count}, expected exactly 1')
    for i, ch in enumerate(zh):
        if _significant_zh(ch) and zh_coverage[i] != 1:
            errors.append(f'Chinese character {i} coverage is {zh_coverage[i]}, expected exactly 1')
    return errors


def attach_semantic_times(groups: list[dict], words: list[dict]) -> list[dict]:
    """Attach media-timeline times from aligned English words.

    Translation reordering is supported: group order follows Chinese display order,
    while each group independently references its English word interval.
    """
    timed = []
    for group in groups:
        start = int(group['en_word_start']); end = int(group['en_word_end'])
        if not (0 <= start < end <= len(words)):
            raise ValueError(f"semantic group {group.get('id')} references unavailable aligned words")
        selected = words[start:end]
        item = dict(group)
        item['start'] = round(min(float(w['start']) for w in selected), 3)
        item['end'] = round(max(float(w['end']) for w in selected), 3)
        timed.append(item)
    return timed
