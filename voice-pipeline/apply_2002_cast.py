"""Apply the reviewed 2002 content-selected cast after the canonical content build.
Keeps source English/Chinese/vocabulary untouched; only voice-direction metadata changes.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAST_PATH=ROOT/'voice-pipeline/config/cast_2002.json'
CONTENT_DIR=ROOT/'kaoyan-reader-v1/content/2002/c'


def apply_cast_to_doc(doc, cast):
    article=doc['article_id'];spec=cast['articles'][article]
    primary=spec['primary_actor_id'];roles=cast['role_actors']
    doc['primary_actor_id']=primary
    doc['article_context']=spec['context_zh']
    if isinstance(doc.get('article'),dict):doc['article']['background']=spec['context_zh']
    doc['reference_pack_status']='2002 C v3 content-selected cast: six primary narrators plus explicit dialogue roles; full 15-slot registry remains available for other articles'
    doc['audio_status']='v3_render_pending'
    for sentence in doc['sentences']:
        for seg in sentence['segments']:
            role=seg.get('speaker_role','narrator')
            seg['actor_id']=primary if role=='narrator' else roles.get(role,seg.get('actor_id',primary))
            seg['pause_before_ms']=0;seg['pause_after_ms']=0
            seg['generation_fingerprint']='pending-v3-render';seg['qa_status']='not_generated_v3'
    return doc


def main():
    cast=json.loads(CAST_PATH.read_text())
    for article in cast['articles']:
        path=CONTENT_DIR/f'{article}.json';doc=json.loads(path.read_text())
        apply_cast_to_doc(doc,cast)
        path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
        print(article,doc['primary_actor_id'],sorted({s['actor_id'] for row in doc['sentences'] for s in row['segments']}))

if __name__=='__main__':main()
