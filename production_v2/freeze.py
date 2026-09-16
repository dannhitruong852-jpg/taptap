import hashlib
import json
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _reader_path(reader_root, value):
    return Path(reader_root) / str(value).removeprefix('./')


def _repo_root(reader_root):
    reader_root = Path(reader_root)
    return reader_root.parent if reader_root.name == 'kaoyan-reader-v1' else reader_root


def _article_slug(row):
    year = int(row['year'])
    article_id = str(row['id'])
    prefix = f'{year}-'
    return article_id[len(prefix):] if article_id.startswith(prefix) else article_id


def _require_file(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _curated_inputs(repo_root, year):
    curated_dir = Path(repo_root) / 'content-pipeline/curated'
    exact = curated_dir / f'{year}.json'
    if exact.is_file():
        return [exact]
    compressed = curated_dir / f'{year}.json.gz'
    if compressed.is_file():
        return [compressed]
    parts = sorted(curated_dir.glob(f'{year}.json.gz.b64.part*'))
    if parts:
        return parts
    raise FileNotFoundError(curated_dir / f'{year}.json*')


def build_freeze_report(manifest, catalog, reader_root):
    reader_root = Path(reader_root)
    repo_root = _repo_root(reader_root)
    years = sorted({int(year) for year in manifest['years']})
    selected = [
        row for row in catalog.get('articles', [])
        if int(row.get('year', -1)) in set(years)
    ]

    articles = {}
    for row in sorted(selected, key=lambda item: item['id']):
        year = int(row['year'])
        article = _article_slug(row)
        content_path = _require_file(_reader_path(reader_root, row['content']))
        candidate_path = _require_file(
            repo_root / f'reports/content-freeze/{year}/{article}.candidate.json'
        )
        articles[row['id']] = {
            'year': year,
            'content': row['content'],
            'content_sha256': sha256_file(content_path),
            'candidate': str(candidate_path.relative_to(repo_root)),
            'candidate_sha256': sha256_file(candidate_path),
        }

    years_meta = {}
    for year in years:
        bilingual_path = _require_file(
            reader_root / f'content/{year}/bilingual-highlights.json'
        )
        voice_path = _require_file(
            repo_root / f'content-pipeline/voice_profiles/{year}.json'
        )
        curated_paths = _curated_inputs(repo_root, year)
        curated = {
            str(path.relative_to(repo_root)): sha256_file(path)
            for path in curated_paths
        }
        years_meta[str(year)] = {
            'bilingual': str(bilingual_path.relative_to(repo_root)),
            'bilingual_sha256': sha256_file(bilingual_path),
            'voice_profile': str(voice_path.relative_to(repo_root)),
            'voice_profile_sha256': sha256_file(voice_path),
            'curated_inputs': curated,
        }

    payload = {
        'batch_id': manifest['batch_id'],
        'pipeline_version': manifest['pipeline_version'],
        'source_ref': manifest['source_ref'],
        'years': years,
        'article_count': len(articles),
        'articles': articles,
        'years_meta': years_meta,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    payload['freeze_id'] = hashlib.sha256(canonical).hexdigest()
    return payload
