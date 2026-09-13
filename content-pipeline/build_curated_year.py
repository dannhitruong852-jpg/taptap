"""Compile one reviewed yearly manuscript into canonical C-mode article JSON."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'voice-pipeline'))
from batch_schema import validate_article

PROFILES = {
    'compare': ('neutral', 'micro', .98, 95), 'contrast': ('serious', 'micro', .98, 130),
    'explain': ('neutral', 'micro', 1.00, 65), 'sequence': ('lively', 'micro', 1.03, 65),
    'qualify': ('neutral', 'low', .97, 85), 'emphasize': ('warm', 'micro', .97, 90),
    'advance': ('lively', 'micro', 1.02, 65), 'conclude': ('warm', 'micro', .97, 95),
    'story': ('warm', 'micro', 1.01, 75), 'settle': ('warm', 'low', .98, 90),
    'action_turn': ('lively', 'strong', 1.04, 70), 'dialogue': ('curious', 'micro', 1.00, 85),
    'irony': ('ironic', 'strong', .97, 180), 'warning': ('serious', 'micro', .97, 105),
    'resolve': ('warm', 'micro', 1.00, 75), 'encourage': ('warm', 'micro', 1.00, 75),
    'playful': ('lively', 'micro', 1.02, 130), 'example': ('neutral', 'low', 1.02, 65),
    'ask': ('curious', 'micro', .98, 110), 'statistic': ('neutral', 'micro', .96, 90),
    'report': ('neutral', 'low', 1.00, 75), 'explain_quote': ('neutral', 'micro', .99, 95),
    'qualify_quote': ('serious', 'micro', .96, 95), 'evaluation_quote': ('serious', 'strong', .97, 115),
}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def vocabulary_for(text: str, lexicon: dict) -> list[dict]:
    found = []
    for lemma, entry in lexicon.items():
        level, meaning, *variants = entry
        for surface in [lemma, *variants]:
            for match in re.finditer(r'(?<![\w-])' + re.escape(surface) + r'(?![\w-])', text, flags=re.I):
                found.append({'word': match.group(), 'lemma': lemma, 'level': int(level), 'meaning': meaning,
                              'start': match.start(), 'end': match.end()})
    return sorted(found, key=lambda x: (x['start'], -(x['end'] - x['start'])))


def compile_article(source: dict, item: dict) -> dict:
    year = int(source['year'])
    article_id = item['id']
    actor = str(item['actor']).zfill(2)
    result = {
        'year': year, 'section_type': item['section_type'], 'article_id': article_id,
        'source_sha256': source['source_sha256'], 'source_pages': item.get('pages', []),
        'accent': item.get('accent', 'en-US'), 'primary_actor_id': actor,
        'article_context': item['context'],
        'article': {'year': year, 'section': article_id, 'title': item['title'], 'background': item['context']},
        'editorial_status': item.get('editorial_status', 'reviewed_candidate'),
        'audio_status': 'not_rendered', 'vocabulary_scale': 'project-curated-1-9-v1', 'sentences': [],
    }
    lexicon = source.get('vocabulary', {})
    overrides = item.get('segment_overrides', {})
    for number, row in enumerate(item['rows'], 1):
        paragraph, marked, zh, discourse, focus = row
        if discourse not in PROFILES:
            raise ValueError(f'{article_id}/s{number:02d}: unknown discourse function {discourse}')
        en = marked.replace('|', '')
        emotion, contrast, rate, pause = PROFILES[discourse]
        sentence = {
            'id': f's{number:02d}', 'paragraph': paragraph, 'en': en, 'zh': zh,
            'vocab': vocabulary_for(en, lexicon), 'discourse_function': discourse,
            'prosody_focus': focus, 'contrast_level': contrast, 'strong_evidence': None, 'segments': [],
        }
        parts = marked.split('|')
        for part_index, text in enumerate(parts, 1):
            sid = f's{number:02d}-{part_index:02d}'
            override = overrides.get(sid, {})
            seg_actor = str(override.get('actor_id', actor)).zfill(2)
            sentence['segments'].append({
                'id': sid, 'text': text, 'speaker_role': override.get('speaker_role', 'narrator'),
                'actor_id': seg_actor, 'emotion': override.get('emotion', emotion),
                'intensity': int(override.get('intensity', 2 if contrast == 'strong' else 1)),
                'rate': round(float(override.get('rate', rate)), 3), 'pause_before_ms': 0,
                'pause_after_ms': int(override.get('pause_after_ms', pause if part_index < len(parts) else 0)),
                'audio_path': f'./audio/{year}/c-{article_id}/{sid}.opus',
                'generation_fingerprint': 'pending-render', 'qa_status': 'not_generated',
            })
        if ''.join(seg['text'] for seg in sentence['segments']) != en:
            raise ValueError(f'{article_id}/s{number:02d}: segment fidelity failure')
        result['sentences'].append(sentence)
    errors = validate_article(result)
    if errors:
        raise ValueError(f'{article_id}: {errors}')
    return result


def build_year(source: dict) -> tuple[list[dict], list[dict]]:
    docs, catalog_rows = [], []
    year = int(source['year'])
    for item in source['articles']:
        doc = compile_article(source, item)
        docs.append(doc)
        catalog_rows.append({
            'id': f"{year}-{item['id']}", 'year': year, 'section_type': item['section_type'],
            'title': item['title'], 'content': f"./content/{year}/c/{item['id']}.json",
            'manifest': f"./audio/{year}/c-{item['id']}/manifest.json", 'sentences': len(doc['sentences']),
        })
    return docs, catalog_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, required=True)
    args = parser.parse_args()
    source_path = ROOT / f'content-pipeline/curated/{args.year}.json'
    source = json.loads(source_path.read_text(encoding='utf-8'))
    if int(source['year']) != args.year:
        raise ValueError('curated source year disagrees with --year')
    docs, rows = build_year(source)
    for doc in docs:
        write_json(ROOT / f"kaoyan-reader-v1/content/{args.year}/c/{doc['article_id']}.json", doc)
    catalog_path = ROOT / 'kaoyan-reader-v1/content/catalog.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8')) if catalog_path.is_file() else {'version': 1, 'years': [], 'articles': []}
    catalog['years'] = sorted(set(catalog.get('years', [])) | {args.year})
    catalog['articles'] = [x for x in catalog.get('articles', []) if x.get('year') != args.year] + rows
    catalog['articles'].sort(key=lambda x: (x['year'], x['id']))
    catalog.setdefault('default_article', f'{args.year}-text1')
    write_json(catalog_path, catalog)
    write_json(ROOT / f'reports/extraction/{args.year}.json', {
        'year': args.year, 'source_filename': source.get('source_filename'), 'source_sha256': source['source_sha256'],
        'method': source.get('method', 'visual PDF review plus curated manuscript'),
        'articles': [{'id': d['article_id'], 'sentences': len(d['sentences'])} for d in docs],
        'suspected_contamination': [], 'unresolved_sections': source.get('unresolved_sections', []),
    })
    print(json.dumps({'year': args.year, 'articles': len(docs)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
