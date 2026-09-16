STATES = (
    'draft',
    'validated',
    'frozen',
    'rendering',
    'merged',
    'release_candidate',
    'published',
)

_TRANSITIONS = {current: target for current, target in zip(STATES, STATES[1:])}


def can_transition(current, target):
    return _TRANSITIONS.get(current) == target


def next_state(current):
    if current not in STATES:
        raise ValueError(f'unknown state: {current}')
    if current == 'published':
        return None
    return _TRANSITIONS[current]
