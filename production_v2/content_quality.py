import json
from pathlib import Path

REQUIRED_REVIEW_FLAGS = (
    'source_scope_verified',
    'question_stems_removed',
    'options_removed',
    'ocr_corrections_reviewed',
    'negation_and_comparison_reviewed',
    'sentence_alignment_reviewed',
)

CANONICAL_DISCOURSE = {
    'compare','contrast','explain','sequence','qualify','emphasize','advance','conclude',
    'story','settle','action_turn','dialogue','irony','warning','resolve','encourage',
    'playful','example','ask','statistic','report','explain_quote','qualify_quote',
    'evaluation_quote',
}

LEGACY_DISCOURSE_ALIASES = {
    'analogy':'compare','evidence':'explain','turn':'contrast','opening':'advance',
    'quote':'dialogue','consequence':'conclude','correct':'contrast','history':'sequence',
    'detail':'explain','comparison':'compare','define':'explain','transition':'advance',
}

LOW_DENSITY_DISCOURSE = {'qualify','settle','example','report'}
VALID_ACTORS = {f'{number:02d}' for number in range(1,16)}


def _read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _canonical(label):
    return LEGACY_DISCOURSE_ALIASES.get(label,label)


def _article_slug(entry):
    year=entry['year']
    prefix=f'{year}-'
    article_id=entry['id']
    return article_id[len(prefix):] if article_id.startswith(prefix) else article_id


def _validate_mapping(article_id, sentences, article_mapping, errors):
    sentence_by_id={sentence['id']:sentence for sentence in sentences}
    for sentence_id, mappings in article_mapping.items():
        sentence=sentence_by_id.get(sentence_id)
        if sentence is None:
            errors.append(f'{article_id}:{sentence_id}: bilingual mapping references unknown sentence')
            continue
        en=sentence.get('en',''); zh=sentence.get('zh','')
        for mapping in mappings or []:
            start=mapping.get('en_start'); end=mapping.get('en_end'); text=mapping.get('en_text')
            if not isinstance(start,int) or not isinstance(end,int) or en[start:end] != text:
                errors.append(f'{article_id}:{sentence_id}: invalid bilingual English span')
            zh_spans=mapping.get('zh_spans') or []
            if not zh_spans:
                errors.append(f'{article_id}:{sentence_id}: bilingual mapping missing Chinese span')
            for span in zh_spans:
                zstart=span.get('start'); zend=span.get('end'); ztext=span.get('text')
                if not isinstance(zstart,int) or not isinstance(zend,int) or zh[zstart:zend] != ztext:
                    errors.append(f'{article_id}:{sentence_id}: invalid bilingual Chinese span')

    for sentence in sentences:
        sentence_id=sentence['id']
        mappings=article_mapping.get(sentence_id) or []
        mapped={(m.get('en_start'),m.get('en_end'),m.get('en_text')) for m in mappings}
        for occurrence in sentence.get('vocab') or []:
            if int(occurrence.get('level',0)) < 6:
                continue
            key=(occurrence.get('start'),occurrence.get('end'),occurrence.get('word'))
            if key not in mapped:
                errors.append(
                    f"{article_id}:{sentence_id}: missing bilingual occurrence "
                    f"{occurrence.get('word')}@{occurrence.get('start')}:{occurrence.get('end')}"
                )


def validate_content_quality(manifest, catalog, root):
    root=Path(root)
    errors=[]
    years=set(manifest.get('years',[]))
    entries=[row for row in catalog.get('articles',[]) if row.get('year') in years]
    reviewed=0
    occurrences=0

    bilingual_by_year={}
    voice_by_year={}
    for year in sorted(years):
        bilingual_path=root/f'kaoyan-reader-v1/content/{year}/bilingual-highlights.json'
        if not bilingual_path.is_file():
            errors.append(f'year {year}: missing bilingual-highlights.json')
            bilingual_by_year[year]={'articles':{}}
        else:
            try:
                doc=_read_json(bilingual_path)
                if int(doc.get('year',-1)) != year:
                    errors.append(f'year {year}: bilingual year mismatch')
                bilingual_by_year[year]=doc
            except Exception as exc:
                errors.append(f'year {year}: invalid bilingual-highlights.json: {exc}')
                bilingual_by_year[year]={'articles':{}}

        voice_path=root/f'content-pipeline/voice_profiles/{year}.json'
        if not voice_path.is_file():
            errors.append(f'year {year}: missing voice profile plan')
            voice_by_year[year]={'profiles':{}}
        else:
            try:
                voice=_read_json(voice_path)
                if int(voice.get('year',-1)) != year:
                    errors.append(f'year {year}: voice profile year mismatch')
                voice_by_year[year]=voice
            except Exception as exc:
                errors.append(f'year {year}: invalid voice profile plan: {exc}')
                voice_by_year[year]={'profiles':{}}

    for entry in entries:
        year=entry['year']; article=_article_slug(entry); full_id=entry['id']
        candidate_path=root/f'reports/content-freeze/{year}/{article}.candidate.json'
        compiled_path=root/'kaoyan-reader-v1'/str(entry.get('content','')).removeprefix('./')

        if not candidate_path.is_file():
            errors.append(f'{full_id}: missing reviewed candidate evidence')
            continue
        if not compiled_path.is_file():
            errors.append(f'{full_id}: missing compiled content')
            continue
        try:
            candidate=_read_json(candidate_path); compiled=_read_json(compiled_path)
        except Exception as exc:
            errors.append(f'{full_id}: invalid candidate/compiled json: {exc}')
            continue

        qa=candidate.get('qa') or {}
        for flag in REQUIRED_REVIEW_FLAGS:
            if qa.get(flag) is not True:
                errors.append(f'{full_id}: review evidence {flag} must be true')
        carticle=candidate.get('article') or {}
        rows=carticle.get('rows') or []
        if int(candidate.get('year',-1)) != year or carticle.get('id') != article:
            errors.append(f'{full_id}: candidate identity mismatch')
        if not rows:
            errors.append(f'{full_id}: reviewed candidate has no rows')
        if qa.get('sentence_count') is not None and int(qa['sentence_count']) != len(rows):
            errors.append(f'{full_id}: candidate sentence_count mismatch')

        sentences=compiled.get('sentences') or []
        if len(rows) != len(sentences):
            errors.append(f'{full_id}: candidate/compiled sentence count mismatch')
        for index,(row,sentence) in enumerate(zip(rows,sentences),1):
            expected_en=row[1].replace('|',''); expected_zh=row[2]
            if sentence.get('en') != expected_en or sentence.get('zh') != expected_zh:
                errors.append(f'{full_id}:s{index:02d}: candidate/compiled text mismatch')
            expected_discourse=_canonical(row[3])
            if expected_discourse not in CANONICAL_DISCOURSE:
                errors.append(f'{full_id}:s{index:02d}: unknown discourse {row[3]}')
            elif sentence.get('discourse_function') != expected_discourse:
                errors.append(f'{full_id}:s{index:02d}: compiled discourse mismatch')

        canonical_labels=[_canonical(row[3]) for row in rows]
        for i in range(max(0,len(canonical_labels)-2)):
            window=canonical_labels[i:i+3]
            if all(label in LOW_DENSITY_DISCOURSE for label in window):
                errors.append(f'{full_id}: sentences {i+1}-{i+3} low-intensity discourse density violation')

        candidate_actor=str(carticle.get('actor','')).zfill(2)
        compiled_actor=str(compiled.get('primary_actor_id','')).zfill(2)
        voice_actor=str((voice_by_year.get(year,{}).get('profiles',{}).get(article,{}) or {}).get('primary_actor_id','')).zfill(2)
        segment_actors={str(seg.get('actor_id','')).zfill(2) for sentence in sentences for seg in (sentence.get('segments') or [])}
        if candidate_actor not in VALID_ACTORS:
            errors.append(f'{full_id}: invalid primary actor {candidate_actor}')
        if not (candidate_actor == compiled_actor == voice_actor):
            errors.append(f'{full_id}: actor mismatch candidate={candidate_actor} compiled={compiled_actor} voice={voice_actor}')
        invalid_segment_actors=sorted(actor for actor in segment_actors if actor not in VALID_ACTORS)
        if invalid_segment_actors:
            errors.append(f'{full_id}: invalid segment actors {invalid_segment_actors}')

        mapping=(bilingual_by_year.get(year,{}).get('articles',{}) or {}).get(article)
        if not isinstance(mapping,dict):
            errors.append(f'{full_id}: missing bilingual article mapping')
            mapping={}
        _validate_mapping(full_id,sentences,mapping,errors)
        occurrences += sum(1 for sentence in sentences for v in (sentence.get('vocab') or []) if int(v.get('level',0)) >= 6)
        reviewed += 1

    return {
        'ok':not errors,
        'years':sorted(years),
        'articles_checked':len(entries),
        'reviewed_candidates_checked':reviewed,
        'level6_vocab_occurrences_checked':occurrences,
        'errors':errors,
    }
