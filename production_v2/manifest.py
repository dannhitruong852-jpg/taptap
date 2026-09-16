from datetime import datetime, timezone

from .pipeline_state import STATES

PIPELINE_VERSION = 2


def build_manifest(batch_id, years, source_ref, created_at=None):
    return {
        'batch_id': str(batch_id),
        'pipeline_version': PIPELINE_VERSION,
        'years': list(years),
        'source_ref': str(source_ref),
        'state': 'draft',
        'created_at': created_at or datetime.now(timezone.utc).isoformat(),
        'freeze': None,
        'artifacts': {},
    }


def validate_manifest(doc):
    errors = []
    required = ('batch_id', 'pipeline_version', 'years', 'source_ref', 'state', 'created_at')
    for key in required:
        if key not in doc or doc[key] in ('', None):
            errors.append(f'missing required field: {key}')

    if doc.get('pipeline_version') != PIPELINE_VERSION:
        errors.append(f'pipeline_version must be {PIPELINE_VERSION}')

    years = doc.get('years')
    if not isinstance(years, list) or not years or not all(isinstance(year, int) for year in years):
        errors.append('years must be a non-empty integer list')
    elif years != sorted(set(years)):
        errors.append('years must be sorted unique')

    if doc.get('state') not in STATES:
        errors.append('state must be a valid pipeline state')

    return errors
