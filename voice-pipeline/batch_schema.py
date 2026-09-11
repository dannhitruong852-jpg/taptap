ALLOWED_SECTIONS = {'cloze', 'reading', 'part_b', 'translation'}
ALLOWED_ACTORS = {f'{i:02d}' for i in range(1, 16)}
ALLOWED_EMOTIONS = {'neutral', 'warm', 'lively', 'serious', 'curious', 'ironic', 'tense', 'emotional'}
ALLOWED_CONTRAST = {'low', 'micro', 'strong'}

REQUIRED_ARTICLE_FIELDS = {
    'year', 'section_type', 'article_id', 'source_sha256', 'accent',
    'primary_actor_id', 'article_context', 'sentences'
}
REQUIRED_SENTENCE_FIELDS = {
    'id', 'en', 'zh', 'vocab', 'discourse_function', 'prosody_focus',
    'contrast_level', 'segments'
}
REQUIRED_SEGMENT_FIELDS = {
    'id', 'text', 'speaker_role', 'actor_id', 'emotion', 'intensity', 'rate',
    'pause_before_ms', 'pause_after_ms', 'audio_path', 'generation_fingerprint',
    'qa_status'
}


def validate_c_mode_density(sentences):
    errors = []
    if len(sentences) < 3:
        return errors
    for i in range(len(sentences) - 2):
        window = sentences[i:i + 3]
        if all(s.get('contrast_level') == 'low' for s in window):
            errors.append(f'sentences {i + 1}-{i + 3} have no micro/strong contrast')
    return errors


def validate_article(article):
    errors = []
    missing = sorted(REQUIRED_ARTICLE_FIELDS - set(article))
    for key in missing:
        errors.append(f'missing article field: {key}')

    if article.get('section_type') not in ALLOWED_SECTIONS:
        errors.append('section_type must be one of cloze, reading, part_b, translation')
    if article.get('primary_actor_id') not in ALLOWED_ACTORS:
        errors.append('primary_actor_id must be 01-15')

    sentences = article.get('sentences') or []
    for sidx, sentence in enumerate(sentences, 1):
        for key in sorted(REQUIRED_SENTENCE_FIELDS - set(sentence)):
            errors.append(f'sentence {sidx} missing field: {key}')
        if sentence.get('contrast_level') not in ALLOWED_CONTRAST:
            errors.append(f'sentence {sidx} contrast_level invalid')
        for gidx, segment in enumerate(sentence.get('segments') or [], 1):
            for key in sorted(REQUIRED_SEGMENT_FIELDS - set(segment)):
                errors.append(f'sentence {sidx} segment {gidx} missing field: {key}')
            if segment.get('actor_id') not in ALLOWED_ACTORS:
                errors.append(f'sentence {sidx} segment {gidx} actor_id must be 01-15')
            if segment.get('emotion') not in ALLOWED_EMOTIONS:
                errors.append(f'sentence {sidx} segment {gidx} emotion invalid')
            if segment.get('intensity') not in {0, 1, 2}:
                errors.append(f'sentence {sidx} segment {gidx} intensity must be 0, 1, or 2')
            rate = segment.get('rate')
            if not isinstance(rate, (int, float)) or not (0.80 <= rate <= 1.10):
                errors.append(f'sentence {sidx} segment {gidx} rate must be 0.80-1.10')

    errors.extend(validate_c_mode_density(sentences))
    return errors
