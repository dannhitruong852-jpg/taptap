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


def build_freeze_report(manifest, catalog, reader_root):
    reader_root = Path(reader_root)
    selected = [
        row for row in catalog.get('articles', [])
        if row.get('year') in set(manifest['years'])
    ]
    articles = {}
    for row in sorted(selected, key=lambda item: item['id']):
        path = _reader_path(reader_root, row['content'])
        if not path.is_file():
            raise FileNotFoundError(path)
        articles[row['id']] = {
            'year': row['year'],
            'content': row['content'],
            'content_sha256': sha256_file(path),
        }

    payload = {
        'batch_id': manifest['batch_id'],
        'pipeline_version': manifest['pipeline_version'],
        'source_ref': manifest['source_ref'],
        'years': list(manifest['years']),
        'article_count': len(articles),
        'articles': articles,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    payload['freeze_id'] = hashlib.sha256(canonical).hexdigest()
    return payload
