"""Compile editorial C v4 direction into actor-specific render controls."""
from __future__ import annotations

import copy
from pathlib import Path
from adapters.chatterbox_actor_adapter import resolve_controls


def _override_for(director: dict, article_id: str, sentence_id: str, segment_id: str) -> dict:
    merged = {}
    for item in director.get('overrides', []):
        if item.get('article_id') not in (None, article_id):
            continue
        if item.get('sentence_id') == sentence_id and (not item.get('segment_id') or item.get('segment_id') == segment_id):
            merged.update(item)
    return merged


def build_voice_plan(content: dict, voice_profile: dict, director: dict, calibration_dir: Path) -> dict:
    discourse_map = director.get('discourse_map', {})
    out = {
        'schema_version':'c-v4-voice-plan-1',
        'year':content.get('year'),
        'article_id':content['article_id'],
        'primary_actor_id':voice_profile.get('primary_actor_id', content.get('primary_actor_id')),
        'article_arc':copy.deepcopy(voice_profile.get('article_arc', [])),
        'sentences':[]
    }
    for sentence in content.get('sentences', []):
        discourse = sentence.get('discourse_function')
        if discourse not in discourse_map:
            raise ValueError(f"unmapped discourse function: {discourse}")
        base = discourse_map[discourse]
        if isinstance(base, str):
            base = {'director_intent':base, 'intensity':1}
        sentence_out = {'id':sentence['id'], 'discourse_function':discourse, 'prosody_focus':copy.deepcopy(sentence.get('prosody_focus', [])), 'segments':[]}
        for segment in sentence.get('segments', []):
            rule = copy.deepcopy(base)
            override = _override_for(director, content['article_id'], sentence['id'], segment['id'])
            rule.update({k:v for k,v in override.items() if k not in ('article_id','sentence_id','segment_id')})
            actor_id = str(rule.get('actor_id') or segment.get('actor_id') or out['primary_actor_id']).zfill(2)
            intent = rule['director_intent']
            intensity = int(rule.get('intensity', 1))
            controls = resolve_controls(actor_id, intent, intensity, calibration_dir)
            sentence_out['segments'].append({
                'id':segment['id'], 'text':segment['text'], 'speaker_role':segment.get('speaker_role','narrator'),
                'actor_id':actor_id, 'director_intent':intent, 'intensity':intensity,
                'prosody_focus':copy.deepcopy(sentence.get('prosody_focus', [])), 'controls':controls
            })
        out['sentences'].append(sentence_out)
    return out
