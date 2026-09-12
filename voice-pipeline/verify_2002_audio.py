"""Verify every live 2002 C audio asset, not only a green generation job.

This verifies delivery, render inputs and decodability, not ASR or artistic quality.
The public files are also retained for reproducible browser/offline verification.
"""
import argparse
import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from generate_2002 import render_fingerprint, save

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {'cloze': (13, 24), 'text1': (21, 36), 'text2': (16, 30),
            'text3': (21, 31), 'text4': (15, 32), 'translation': (5, 12)}
BASE = 'https://dannhitruong852-jpg.github.io/taptap/kaoyan-reader-v1/'


def safe_relative(path):
    if not isinstance(path, str) or not path or '\\' in path:
        raise ValueError('Invalid relative asset path')
    parts = urlsplit(path)
    if parts.scheme or parts.netloc or parts.query or parts.fragment or path.startswith('/'):
        raise ValueError('Asset must be a same-site relative path')
    if '..' in path.split('/'):
        raise ValueError('Parent traversal is not permitted')
    result = str(PurePosixPath(path))
    if result == '.':
        raise ValueError('An asset path cannot be empty')
    return result


def verify_file(path, digest):
    path = Path(path)
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest


def validate_manifest(doc, manifest):
    errors = []
    article = doc['article_id']
    ordered = [s for row in doc['sentences'] for s in row['segments']]
    ids = [s['id'] for s in ordered]
    segments = manifest.get('segments', {})
    if len(set(ids)) != len(ids):
        errors.append('Duplicate segment IDs in source')
    if manifest.get('article') != article:
        errors.append('Wrong article in manifest')
    if manifest.get('status') != 'complete_candidate' or manifest.get('missing') != []:
        errors.append('Incomplete manifest status')
    if list(segments) != ids:
        errors.append('Manifest segment coverage or ordering differs from source')
    for segment in ordered:
        sid = segment['id']
        entry = segments.get(sid)
        if not entry:
            errors.append(f'{sid}: missing audio')
            continue
        if entry.get('technical_qa') != 'passed':
            errors.append(f'{sid}: technical QA not passed')
        for ext, field in [('opus', 'path'), ('mp3', 'mp3_path')]:
            try:
                actual = safe_relative(entry[field])
                expected = f'audio/2002/c-{article}/{sid}.{ext}'
                if actual != expected or f'{sid}.{ext}' not in entry.get('files', {}):
                    errors.append(f'{sid}: missing or incorrect {ext} path/hash')
            except (KeyError, ValueError, TypeError):
                errors.append(f'{sid}: invalid {ext} path')
        try:
            expected = render_fingerprint(segment, entry['reference_sha256'], entry['seed'])
            if entry.get('fingerprint') != expected:
                errors.append(f'{sid}: stale render fingerprint')
        except (KeyError, TypeError, ValueError):
            errors.append(f'{sid}: invalid render metadata')
    return errors


def fetch_asset(base, relative, destination):
    relative = safe_relative(relative)
    request = Request(base.rstrip('/') + '/' + relative + '?audio_verify=' + str(time.time_ns()),
                      headers={'User-Agent': '2002-audio-delivery-verifier', 'Cache-Control': 'no-cache'})
    error = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                data = response.read()
            target = Path(destination) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return target
        except Exception as exc:
            error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f'Cannot fetch {relative}: {error}') from error


def decode_audio(path):
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-threads', '1', '-i', str(path),
                    '-f', 'null', '-'], check=True, timeout=45, capture_output=True)
    duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of', 'default=nw=1:nk=1', str(path)], timeout=15))
    if duration < .2:
        raise ValueError(f'Empty or implausibly short audio: {path}')
    return duration


def verify_live(base, destination, decode=True):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(fetch_asset(base, 'content/catalog.json', destination).read_text())
    entries = [x for x in catalog['articles'] if x['year'] == 2002]
    if {x['id'] for x in entries} != {'2002-' + x for x in EXPECTED} or len(entries) != 6:
        raise ValueError('Public catalog does not contain the six expected 2002 units')
    documents = []
    files = []
    results = []
    for entry in entries:
        doc = json.loads(fetch_asset(base, entry['content'], destination).read_text())
        article = doc['article_id']
        expected_doc = json.loads((ROOT / f'kaoyan-reader-v1/content/2002/c/{article}.json').read_text())
        if doc != expected_doc:
            raise ValueError(f'{article}: live article differs from verified source')
        manifest = json.loads(fetch_asset(base, entry['manifest'], destination).read_text())
        errors = validate_manifest(doc, manifest)
        if errors:
            raise ValueError(f'{article}: ' + '; '.join(errors))
        count = sum(len(row['segments']) for row in doc['sentences'])
        if (len(doc['sentences']), count) != EXPECTED[article]:
            raise ValueError(f'{article}: unexpected sentence/segment counts')
        for sid, record in manifest['segments'].items():
            for ext, key in [('opus', 'path'), ('mp3', 'mp3_path')]:
                files.append((record[key], record['files'][f'{sid}.{ext}']))
        documents.append(doc)
        results.append({'id': article, 'sentences': len(doc['sentences']), 'segments': count,
                        'missing': 0, 'qa_status': 'candidate'})
    def check_one(asset):
        relative, digest = asset
        path = fetch_asset(base, relative, destination)
        if not verify_file(path, digest):
            raise ValueError(f'Public audio hash mismatch: {relative}')
        duration = decode_audio(path) if decode else None
        return {'path': safe_relative(relative), 'sha256': digest, 'duration_seconds': duration}
    with ThreadPoolExecutor(max_workers=8) as pool:
        checked = list(pool.map(check_one, files))
    site_files = ['index.html', 'styles.css', 'app.js', 'catalog.js', 'audio-player.js',
                  'playback.js', 'scroll-behavior.js', 'content/2002/audio-status.json']
    for relative in site_files:
        fetch_asset(base, relative, destination)
    published = json.loads((destination / 'content/2002/audio-status.json').read_text())
    if published['generated_segments'] != 165 or published['missing_segments'] != 0:
        raise ValueError('Public completion report is stale or incomplete')
    result = {'verified_at': datetime.now(timezone.utc).isoformat(), 'base_url': base,
              'delivery_status': 'complete', 'articles': results, 'sentences': 91,
              'segments': 165, 'audio_files': len(checked), 'missing_segments': 0,
              'all_hashes_match': True, 'all_files_decode': bool(decode),
              'asr_qa': 'not_performed', 'speaker_qa': 'not_performed',
              'c_listening_acceptance': 'pending_user_acceptance', 'files': checked}
    save(ROOT / 'reports/qa/2002-live-audio.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=BASE)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    result = verify_live(args.base, args.destination)
    print(json.dumps({key: value for key, value in result.items() if key != 'files'}, indent=2))


if __name__ == '__main__':
    main()
