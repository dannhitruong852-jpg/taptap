import re

WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _tokens(text):
    return [m.group(0).lower() for m in WORD_RE.finditer(text or '')]


def normalized_wer(reference, hypothesis):
    ref = _tokens(reference)
    hyp = _tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, rw in enumerate(ref, start=1):
        cur = [i]
        for j, hw in enumerate(hyp, start=1):
            cur.append(min(
                cur[-1] + 1,
                prev[j] + 1,
                prev[j - 1] + (rw != hw),
            ))
        prev = cur
    return prev[-1] / len(ref)


def pace_check(word_count, duration_seconds, min_wpm=105.0, max_wpm=190.0):
    if word_count < 0 or duration_seconds <= 0:
        return {'pass': False, 'wpm': 0.0}
    wpm = (word_count / duration_seconds) * 60.0
    return {'pass': min_wpm <= wpm <= max_wpm, 'wpm': round(wpm, 2)}


def needs_cinematic_review(emotion, intensity, speaker_role):
    return (
        intensity == 2
        or speaker_role != 'narrator'
        or emotion in {'ironic', 'tense', 'emotional'}
    )
