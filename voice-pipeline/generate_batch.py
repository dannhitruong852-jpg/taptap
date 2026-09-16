"""Fail-soft orchestration helpers for deterministic multi-year C-mode rendering."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Iterable

from batching import select_shard as _select_shard


def select_shard(items, shard_index: int, shard_count: int):
    """Planned public API: shard index first, delegating to the legacy helper."""
    return _select_shard(items, shard_count, shard_index)


def validate_render_request(year: int, article: str) -> None:
    if not isinstance(year, int) or year < 1900 or year > 2100:
        raise ValueError('year must be a four-digit exam year')
    if not article or not all(ch.isalnum() or ch in ('-', '_') for ch in article):
        raise ValueError('article must be a safe article id')


def resolve_render_paths(
    root: Path,
    year: int,
    article: str,
    *,
    output: Path | None = None,
    calibration_dir: Path | None = None,
    reference_dir: Path | None = None,
) -> dict[str, Path]:
    validate_render_request(year, article)
    root = Path(root)
    return {
        'content': root / f'kaoyan-reader-v1/content/{year}/c/{article}.json',
        'voice_profiles': root / f'content-pipeline/voice_profiles/{year}.json',
        'direction': root / f'content-pipeline/direction/{year}.json',
        'calibration_dir': Path(calibration_dir) if calibration_dir else root / 'voice-pipeline/calibration/actors',
        'reference_dir': Path(reference_dir) if reference_dir else root / 'voice-pipeline/references/2002-cast',
        'output': Path(output) if output else root / f'kaoyan-reader-v1/audio/{year}/v4/c-{article}',
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def item_fingerprint(item: dict) -> str:
    """Stable fingerprint for render-significant input data."""
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _cache_valid(entry: dict, output_dir: Path, expected_fingerprint: str) -> bool:
    if entry.get('status') != 'ok' or entry.get('fingerprint') != expected_fingerprint:
        return False
    files = entry.get('files') or {}
    if not files:
        return False
    for name, digest in files.items():
        path = output_dir / name
        if not path.is_file() or sha256_file(path) != digest:
            return False
    return True


def run_batch(
    items: Iterable[dict],
    output_dir: Path,
    old_manifest: dict | None,
    *,
    render_one: Callable[[dict, int, Path], dict | None],
    max_attempts: int = 2,
) -> dict:
    """Render independent items with verified cache hits and isolated retries."""
    if max_attempts < 1:
        raise ValueError('max_attempts must be positive')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    previous = (old_manifest or {}).get('items', {})
    report = {'items': {}, 'failures': [], 'cache_hits': 0}

    for item in items:
        item_id = item['id']
        fingerprint = item_fingerprint(item)
        cached = previous.get(item_id, {})
        if _cache_valid(cached, output_dir, fingerprint):
            report['items'][item_id] = cached
            report['cache_hits'] += 1
            continue

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                rendered = render_one(item, attempt, output_dir) or {}
                entry = {
                    **rendered,
                    'id': item_id,
                    'status': 'ok',
                    'fingerprint': fingerprint,
                    'attempts': attempt,
                }
                report['items'][item_id] = entry
                break
            except Exception as exc:  # fail-soft by item; unrelated work continues
                last_error = str(exc)
        else:
            entry = {
                'id': item_id,
                'status': 'failed',
                'fingerprint': fingerprint,
                'attempts': max_attempts,
                'error': last_error or 'unknown render failure',
            }
            report['items'][item_id] = entry
            report['failures'].append({'id': item_id, 'error': entry['error'], 'attempts': max_attempts})

    return report


def merge_manifests(manifests: Iterable[dict]) -> dict:
    """Merge shard manifests deterministically; a successful retry beats a failure."""
    merged_items: dict[str, dict] = {}
    cache_hits = 0
    for manifest in manifests:
        cache_hits += int(manifest.get('cache_hits', 0))
        for item_id, candidate in manifest.get('items', {}).items():
            current = merged_items.get(item_id)
            if current is None:
                merged_items[item_id] = candidate
                continue
            current_ok = current.get('status') == 'ok'
            candidate_ok = candidate.get('status') == 'ok'
            if current_ok and candidate_ok:
                if current.get('fingerprint') != candidate.get('fingerprint'):
                    raise ValueError(f'conflicting successful manifests for {item_id}')
                continue
            if candidate_ok and not current_ok:
                merged_items[item_id] = candidate

    failures = [
        {'id': item_id, 'error': entry.get('error', 'render failed'), 'attempts': entry.get('attempts')}
        for item_id, entry in merged_items.items()
        if entry.get('status') != 'ok'
    ]
    return {'items': merged_items, 'failures': failures, 'cache_hits': cache_hits}
