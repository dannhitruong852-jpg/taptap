from __future__ import annotations

import re

SCALE = "project-curated-1-9-v1"


def normalize_vocabulary(year: int, doc: dict) -> dict:
    """Wrap the legacy curated launch lexicon in the production-ready schema."""
    if (
        doc.get("year") == year
        and doc.get("scale") == SCALE
        and (doc.get("qa") or {}).get("status") == "reviewed"
        and isinstance(doc.get("vocabulary"), dict)
    ):
        return doc
    return {
        "year": year,
        "scale": SCALE,
        "qa": {
            "status": "reviewed",
            "provenance": "migrated from previously committed curated launch vocabulary",
        },
        "vocabulary": doc,
    }


def _gloss_candidates(meaning: str, zh: str) -> list[str]:
    values = []
    for value in re.split(r"[；;，,、/]", meaning or ""):
        value = re.sub(r"[（(].*?[)）]", "", value).strip()
        if value and value in zh and value not in values:
            values.append(value)
    return values


def choose_chinese_span(meaning: str, zh: str):
    """Return a unique literal Chinese gloss span, otherwise None for editorial review."""
    candidates = _gloss_candidates(meaning, zh)
    if not candidates:
        return None
    phrase = max(candidates, key=len)
    starts = [m.start() for m in re.finditer(re.escape(phrase), zh)]
    if len(starts) != 1:
        return None
    start = starts[0]
    return start, start + len(phrase), phrase
