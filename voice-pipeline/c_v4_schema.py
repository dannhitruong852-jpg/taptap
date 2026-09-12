"""Validation contracts for C v4 editorial direction and actor calibration.

C v4 intentionally keeps model controls out of editorial direction. Chatterbox
parameters are resolved later by an actor-specific adapter.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_INTENT_CONFIG = ROOT / 'config' / 'director_intents.json'

PROFILE_FIELDS = {
    'year', 'article_id', 'domain', 'author_stance', 'formality', 'narrativity',
    'humor_level', 'rationality_emotionality', 'baseline_mood', 'speaker_persona',
    'preferred_age_impression', 'preferred_gender_if_relevant', 'dialogue_roles',
    'article_arc', 'primary_actor_id'
}
SEGMENT_FIELDS = {
    'sentence_id', 'segment_id', 'speaker_role', 'actor_id', 'director_intent',
    'intensity', 'information_focus', 'contrast_target', 'sentence_role_in_article_arc'
}
FORBIDDEN_DIRECTOR_FIELDS = {
    'exaggeration', 'cfg_weight', 'temperature', 'repetition_penalty', 'rate',
    'pause_before_ms', 'pause_after_ms', 'artificial_pause_ms', 'post_tempo'
}
ACTOR_FIELDS = {
    'actor_id', 'source_speaker', 'persona', 'reference_variants', 'intents',
    'eligible', 'eligible_for', 'benchmark_relation'
}
CONTROL_FIELDS = {'exaggeration', 'cfg_weight', 'temperature', 'repetition_penalty'}


def _actor_id(value):
    return isinstance(value, str) and len(value) == 2 and value.isdigit() and 1 <= int(value) <= 15


def allowed_intents():
    data = json.loads(_INTENT_CONFIG.read_text(encoding='utf-8'))
    return set(data['intents'])


def validate_article_voice_profile(profile: dict) -> list[str]:
    errors = []
    if not isinstance(profile, dict):
        return ['article voice profile must be an object']
    for field in sorted(PROFILE_FIELDS - set(profile)):
        errors.append(f'missing article voice profile field: {field}')
    if not isinstance(profile.get('year'), int):
        errors.append('year must be an integer')
    if not isinstance(profile.get('article_id'), str) or not profile.get('article_id'):
        errors.append('article_id must be nonempty')
    if not isinstance(profile.get('domain'), list) or not profile.get('domain'):
        errors.append('domain must be a nonempty list')
    if not isinstance(profile.get('dialogue_roles'), list):
        errors.append('dialogue_roles must be a list')
    if not isinstance(profile.get('article_arc'), list) or not profile.get('article_arc'):
        errors.append('article_arc must be a nonempty list')
    if not _actor_id(profile.get('primary_actor_id')):
        errors.append('primary_actor_id must be 01-15')
    for field in ('author_stance','formality','narrativity','humor_level','rationality_emotionality',
                  'baseline_mood','speaker_persona','preferred_age_impression'):
        if not isinstance(profile.get(field), str) or not profile.get(field):
            errors.append(f'{field} must be nonempty')
    gender = profile.get('preferred_gender_if_relevant')
    if gender is not None and (not isinstance(gender, str) or not gender):
        errors.append('preferred_gender_if_relevant must be null or a nonempty string')
    return errors


def materialize_director_plan(compact: dict) -> dict:
    """Expand a compact reviewed sentence plan into segment-level Director Intent.

    Compact storage avoids duplicating identical sentence-level intent/focus across
    semantic parts while preserving exact segment IDs and explicit role overrides.
    """
    if not isinstance(compact, dict):
        raise ValueError('compact director plan must be an object')
    year = compact.get('year')
    article_id = compact.get('article_id')
    primary = compact.get('primary_actor_id')
    overrides = compact.get('role_overrides') or {}
    segments = []
    fields = compact.get('sentence_fields') or [
        'id','parts','director_intent','intensity','information_focus','contrast_target','sentence_role_in_article_arc'
    ]
    for raw in compact.get('sentences') or []:
        row = dict(zip(fields, raw)) if isinstance(raw, list) else raw
        sid = row.get('id')
        parts = row.get('parts')
        if not isinstance(parts, int) or parts < 1:
            raise ValueError(f'{article_id}/{sid}: parts must be positive')
        for index in range(parts):
            segment_id = f'{sid}-{index + 1:02d}'
            override = overrides.get(segment_id, {})
            segments.append({
                'sentence_id': sid,
                'segment_id': segment_id,
                'speaker_role': override.get('speaker_role', 'narrator'),
                'actor_id': override.get('actor_id', primary),
                'director_intent': row.get('director_intent'),
                'intensity': row.get('intensity'),
                'information_focus': list(row.get('information_focus') or []),
                'contrast_target': row.get('contrast_target'),
                'sentence_role_in_article_arc': row.get('sentence_role_in_article_arc'),
            })
    return {'year': year, 'article_id': article_id, 'segments': segments}


def validate_director_plan(plan: dict) -> list[str]:
    errors = []
    if not isinstance(plan, dict):
        return ['director plan must be an object']
    for field in ('year','article_id','segments'):
        if field not in plan:
            errors.append(f'missing director plan field: {field}')
    if not isinstance(plan.get('year'), int):
        errors.append('director plan year must be an integer')
    if not isinstance(plan.get('article_id'), str) or not plan.get('article_id'):
        errors.append('director plan article_id must be nonempty')
    segments = plan.get('segments')
    if not isinstance(segments, list) or not segments:
        errors.append('director plan segments must be a nonempty list')
        return errors
    intents = allowed_intents()
    seen = set()
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            errors.append(f'segment {index} must be an object')
            continue
        for field in sorted(SEGMENT_FIELDS - set(segment)):
            errors.append(f'segment {index} missing field: {field}')
        for field in sorted(FORBIDDEN_DIRECTOR_FIELDS & set(segment)):
            if field == 'exaggeration':
                errors.append(f'segment {index} exaggeration is model-specific and forbidden in Director Plan')
            else:
                errors.append(f'segment {index} {field} is model-specific and forbidden in Director Plan')
        if segment.get('director_intent') not in intents:
            errors.append(f"segment {index} unknown director_intent: {segment.get('director_intent')!r}")
        if segment.get('intensity') not in {0,1,2}:
            errors.append(f'segment {index} intensity must be 0, 1, or 2')
        if not _actor_id(segment.get('actor_id')):
            errors.append(f'segment {index} actor_id must be 01-15')
        if not isinstance(segment.get('information_focus'), list):
            errors.append(f'segment {index} information_focus must be a list')
        for field in ('sentence_id','segment_id','speaker_role','sentence_role_in_article_arc'):
            if not isinstance(segment.get(field), str) or not segment.get(field):
                errors.append(f'segment {index} {field} must be nonempty')
        target = segment.get('contrast_target')
        if target is not None and not isinstance(target, str):
            errors.append(f'segment {index} contrast_target must be null or a string')
        key = segment.get('segment_id')
        if key in seen:
            errors.append(f'duplicate segment_id: {key}')
        seen.add(key)
    return errors


def _validate_controls(controls, prefix):
    errors = []
    if not isinstance(controls, dict):
        return [f'{prefix} must be an object']
    for field in sorted(CONTROL_FIELDS - set(controls)):
        errors.append(f'{prefix} missing control: {field}')
    ranges = {
        'exaggeration': (0.20, 0.95),
        'cfg_weight': (0.20, 0.70),
        'temperature': (0.40, 1.20),
        'repetition_penalty': (1.00, 1.50),
    }
    for field, (low, high) in ranges.items():
        value = controls.get(field)
        if not isinstance(value, (int,float)) or not low <= value <= high:
            errors.append(f'{prefix} {field} must be within {low}-{high}')
    if controls.get('artificial_pause_ms', 0) != 0:
        errors.append(f'{prefix} artificial_pause_ms must be 0')
    if controls.get('post_tempo', False) is not False:
        errors.append(f'{prefix} post_tempo must be false')
    return errors


def validate_actor_calibration(profile: dict, *, require_eligible: bool = False) -> list[str]:
    errors = []
    if not isinstance(profile, dict):
        return ['actor calibration profile must be an object']
    for field in sorted(ACTOR_FIELDS - set(profile)):
        errors.append(f'missing actor calibration field: {field}')
    if not _actor_id(profile.get('actor_id')):
        errors.append('actor_id must be 01-15')
    for field in ('source_speaker','persona','benchmark_relation'):
        if not isinstance(profile.get(field), str) or not profile.get(field):
            errors.append(f'{field} must be nonempty')
    if not isinstance(profile.get('reference_variants'), dict) or not profile.get('reference_variants'):
        errors.append('reference_variants must be a nonempty object')
    if not isinstance(profile.get('eligible'), bool):
        errors.append('eligible must be boolean')
    if not isinstance(profile.get('eligible_for'), list):
        errors.append('eligible_for must be a list')
    intents = profile.get('intents')
    if not isinstance(intents, dict) or not intents:
        errors.append('intents must be a nonempty object')
        return errors
    allowed = allowed_intents()
    for intent, cfg in intents.items():
        prefix = f'intent {intent}'
        if intent not in allowed:
            errors.append(f'{prefix} is unknown')
        if not isinstance(cfg, dict):
            errors.append(f'{prefix} must be an object')
            continue
        if not isinstance(cfg.get('reference_emotion'), str) or not cfg.get('reference_emotion'):
            errors.append(f'{prefix} reference_emotion must be nonempty')
        candidates = cfg.get('candidate_controls')
        if not isinstance(candidates, list) or not candidates:
            errors.append(f'{prefix} candidate_controls must be nonempty')
        else:
            for idx, controls in enumerate(candidates, 1):
                errors.extend(_validate_controls(controls, f'{prefix} candidate {idx}'))
        if cfg.get('human_status') not in {'pending','approved','rejected'}:
            errors.append(f'{prefix} human_status invalid')
        selected = cfg.get('selected_controls')
        if selected is not None:
            errors.extend(_validate_controls(selected, f'{prefix} selected_controls'))
        if require_eligible and profile.get('eligible') and selected is None:
            errors.append(f'{prefix} selected_controls required for eligible actor')
    if require_eligible and not profile.get('eligible'):
        errors.append('actor is not eligible for production')
    return errors
