"""Strict validation helpers for occurrence-specific bilingual vocabulary highlights."""
from __future__ import annotations

from typing import Any


def _error(code: str, **fields: Any) -> dict:
    return {"code": code, **fields}


def _sentence_index(article_docs: list[dict]) -> dict[tuple[str, str], dict]:
    result: dict[tuple[str, str], dict] = {}
    for article in article_docs:
        article_id = str(article.get("article_id", ""))
        for sentence in article.get("sentences", []):
            result[(article_id, str(sentence.get("id", "")))] = sentence
    return result


def _required_occurrences(article_docs: list[dict]) -> dict[tuple[str, str, int, int], dict]:
    required: dict[tuple[str, str, int, int], dict] = {}
    for article in article_docs:
        article_id = str(article.get("article_id", ""))
        for sentence in article.get("sentences", []):
            sentence_id = str(sentence.get("id", ""))
            for vocab in sentence.get("vocab", []):
                if int(vocab.get("level", 0)) < 6:
                    continue
                start = vocab.get("start")
                end = vocab.get("end")
                if not isinstance(start, int) or not isinstance(end, int):
                    continue
                required[(article_id, sentence_id, start, end)] = vocab
    return required


def validate_bilingual_highlights(mapping: dict, article_docs: list[dict]) -> dict:
    """Validate exact reviewed bilingual spans against compiled article documents.

    Every level-6+ English vocabulary occurrence must be covered by exactly one valid
    mapping entry or by one explicit reviewed exception with a non-empty reason.
    """
    errors: list[dict] = []
    sentences = _sentence_index(article_docs)
    required = _required_occurrences(article_docs)
    mapped_keys: set[tuple[str, str, int, int]] = set()
    exception_keys: set[tuple[str, str, int, int]] = set()

    articles = mapping.get("articles", {}) if isinstance(mapping, dict) else {}
    if not isinstance(articles, dict):
        errors.append(_error("invalid_articles_object"))
        articles = {}

    for article_id, sentence_map in articles.items():
        if not isinstance(sentence_map, dict):
            errors.append(_error("invalid_sentence_map", article_id=article_id))
            continue
        for sentence_id, entries in sentence_map.items():
            sentence = sentences.get((str(article_id), str(sentence_id)))
            if sentence is None:
                errors.append(_error("nonexistent_sentence", article_id=article_id, sentence_id=sentence_id))
                continue
            if not isinstance(entries, list):
                errors.append(_error("invalid_mapping_list", article_id=article_id, sentence_id=sentence_id))
                continue
            en = str(sentence.get("en", ""))
            zh = str(sentence.get("zh", ""))
            for entry in entries:
                if not isinstance(entry, dict):
                    errors.append(_error("invalid_mapping_entry", article_id=article_id, sentence_id=sentence_id))
                    continue
                start, end = entry.get("en_start"), entry.get("en_end")
                if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or end > len(en):
                    errors.append(_error("invalid_english_span", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
                    continue
                key = (str(article_id), str(sentence_id), start, end)
                if en[start:end] != entry.get("en_text"):
                    errors.append(_error("stale_english_span", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
                    continue
                if key not in required:
                    errors.append(_error("mapping_not_required_occurrence", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
                    continue
                if key in mapped_keys:
                    errors.append(_error("duplicate_mapping", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
                    continue
                zh_spans = entry.get("zh_spans", [])
                if not isinstance(zh_spans, list) or not zh_spans:
                    errors.append(_error("missing_chinese_span", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
                    continue
                spans_valid = True
                for span in zh_spans:
                    if not isinstance(span, dict):
                        spans_valid = False
                        errors.append(_error("invalid_chinese_span", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
                        continue
                    zh_start, zh_end = span.get("start"), span.get("end")
                    if not isinstance(zh_start, int) or not isinstance(zh_end, int) or zh_start < 0 or zh_end <= zh_start or zh_end > len(zh):
                        spans_valid = False
                        errors.append(_error("invalid_chinese_span", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end, zh_start=zh_start, zh_end=zh_end))
                        continue
                    if zh[zh_start:zh_end] != span.get("text"):
                        spans_valid = False
                        errors.append(_error("stale_chinese_span", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end, zh_start=zh_start, zh_end=zh_end))
                if spans_valid:
                    mapped_keys.add(key)

    exceptions = mapping.get("exceptions", []) if isinstance(mapping, dict) else []
    if not isinstance(exceptions, list):
        errors.append(_error("invalid_exceptions_list"))
        exceptions = []
    for exception in exceptions:
        if not isinstance(exception, dict):
            errors.append(_error("invalid_exception"))
            continue
        article_id = str(exception.get("article_id", ""))
        sentence_id = str(exception.get("sentence_id", ""))
        start, end = exception.get("en_start"), exception.get("en_end")
        key = (article_id, sentence_id, start, end)
        reason = str(exception.get("reason", "")).strip()
        if key not in required:
            errors.append(_error("exception_not_required_occurrence", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
            continue
        if not reason:
            errors.append(_error("exception_missing_reason", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
            continue
        if key in mapped_keys:
            errors.append(_error("mapped_occurrence_also_excepted", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
            continue
        if key in exception_keys:
            errors.append(_error("duplicate_exception", article_id=article_id, sentence_id=sentence_id, en_start=start, en_end=end))
            continue
        exception_keys.add(key)

    covered = mapped_keys | exception_keys
    for key, vocab in required.items():
        if key in covered:
            continue
        article_id, sentence_id, start, end = key
        errors.append(_error(
            "unmapped_required_occurrence",
            article_id=article_id,
            sentence_id=sentence_id,
            en_start=start,
            en_end=end,
            word=vocab.get("word", ""),
            level=int(vocab.get("level", 0)),
            meaning=vocab.get("meaning", ""),
        ))

    return {
        "year": mapping.get("year") if isinstance(mapping, dict) else None,
        "required_occurrences": len(required),
        "mapped_occurrences": len(mapped_keys),
        "reviewed_exceptions": len(exception_keys),
        "errors": errors,
    }
