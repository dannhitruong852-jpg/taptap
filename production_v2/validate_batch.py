import json
from pathlib import Path

from .manifest import validate_manifest

VALID_PHASES = {'preflight', 'freeze', 'release'}


def _reader_path(reader_root, value):
    return Path(reader_root) / str(value).removeprefix('./')


def validate_batch(manifest, catalog, reader_root, phase='preflight'):
    if phase not in VALID_PHASES:
        raise ValueError(f'unknown phase: {phase}')

    errors = list(validate_manifest(manifest))
    years = set(manifest.get('years', []))
    selected = [row for row in catalog.get('articles', []) if row.get('year') in years]
    present_years = {row.get('year') for row in selected}

    for year in sorted(years - present_years):
        errors.append(f'year {year}: no catalog articles')

    expected_articles = manifest.get('expected_articles') or {}
    for year in sorted(years):
        expected = set(expected_articles.get(str(year), []))
        actual = {
            row['id'].removeprefix(f'{year}-')
            for row in selected
            if row.get('year') == year
        }
        if expected and actual != expected:
            errors.append(
                f'year {year}: article inventory mismatch '
                f'expected={sorted(expected)} actual={sorted(actual)}'
            )

    for row in selected:
        article_id = row.get('id', '<unknown>')
        content_path = _reader_path(reader_root, row.get('content', ''))
        if not content_path.is_file():
            errors.append(f'{article_id}: missing content {content_path}')
            continue

        try:
            content = json.loads(content_path.read_text())
        except Exception as exc:
            errors.append(f'{article_id}: invalid content json: {exc}')
            continue

        sentences = content.get('sentences')
        if not isinstance(sentences, list) or not sentences:
            errors.append(f'{article_id}: empty sentences')
            continue

        expected = row.get('sentences')
        if isinstance(expected, int) and expected != len(sentences):
            errors.append(f'{article_id}: sentence count {len(sentences)} != catalog {expected}')

        for sentence in sentences:
            segments = sentence.get('segments') or []
            if segments and ''.join(segment.get('text', '') for segment in segments) != sentence.get('en', ''):
                errors.append(f"{article_id}:{sentence.get('id')}: segment coverage mismatch")

        if phase == 'release':
            manifest_path = _reader_path(reader_root, row.get('manifest', ''))
            if not manifest_path.is_file():
                errors.append(f'{article_id}: missing audio manifest {manifest_path}')
                continue

            try:
                audio_manifest = json.loads(manifest_path.read_text())
            except Exception as exc:
                errors.append(f'{article_id}: invalid audio manifest json: {exc}')
                continue

            missing = audio_manifest.get('missing_segments') or []
            if missing:
                errors.append(f'{article_id}: missing_segments={missing}')

            audio_sentences = audio_manifest.get('sentences') or {}
            if len(audio_sentences) != len(sentences):
                errors.append(
                    f'{article_id}: audio sentence count {len(audio_sentences)} != content {len(sentences)}'
                )

            for sentence_id, audio in audio_sentences.items():
                for key in ('path', 'mp3_path'):
                    path_value = audio.get(key)
                    if not path_value:
                        errors.append(f'{article_id}:{sentence_id}: missing {key}')
                        continue
                    target = _reader_path(reader_root, path_value)
                    if not target.is_file():
                        errors.append(f'{article_id}:{sentence_id}: missing asset {target}')

    return {
        'ok': not errors,
        'phase': phase,
        'years': sorted(years),
        'articles_checked': len(selected),
        'errors': errors,
    }
