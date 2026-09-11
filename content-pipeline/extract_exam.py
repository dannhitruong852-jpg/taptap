import re
import unicodedata
try:
    from normalize import normalize_prose
except ImportError:
    import importlib.util
    from pathlib import Path
    p = Path(__file__).with_name('normalize.py')
    spec = importlib.util.spec_from_file_location('normalize', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    normalize_prose = mod.normalize_prose

SECTION_I = re.compile(r'(?im)^\s*Section\s+I\s+Use\s+o\s*f\s+English\s*$')
SECTION_II = re.compile(r'(?im)^\s*Section\s+(?:II|Ⅱ)\s+Reading\s+Comprehension\s*$')
TRANSLATION_SECTION = re.compile(r'(?im)^\s*Section\s+(?:III|HI|Ⅲ)\s+Translation\s*$')
WRITING_SECTION = re.compile(r'(?im)^\s*Section\s+(?:III|IV|Ⅳ)\s+(?:Writing|Written\s+Expression)\s*$')
PART_A = re.compile(r'(?im)^\s*Part\s*A\s*$')
PART_B = re.compile(r'(?im)^\s*Part\s*B\s*$')
PART_C = re.compile(r'(?im)^\s*Part\s*C\s*$')
TEXT_HEADING = re.compile(r'(?im)^\s*T\s*e\s*x\s*t\s*(?:[1lI]|[2-9])\s*$')
QUESTION_LINE = re.compile(r'(?im)^\s*(?:1[1-9]|2[0-9]|3[0-9]|40)\s*\.')
OPTION_LINE = re.compile(r'(?im)^\s*\[?[A-D]\]\s+')
DIRECTIONS_START = re.compile(r'(?im)^\s*(?:\d+\.\s*)?Directions:\s*$')


def _canonicalize_for_matching(text):
    return unicodedata.normalize('NFKC', text)


def _drop_directions(block):
    block = block.strip()
    m = DIRECTIONS_START.search(block)
    if not m:
        return block
    tail = block[m.end():]
    parts = re.split(r'\n\s*\n', tail, maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    lines = [x.strip() for x in tail.splitlines() if x.strip()]
    skip_prefixes = ('Read ', 'Choose ', 'Mark ', 'Answer ', 'Translate ', 'Write ', 'For each ', 'In this section')
    while lines and (lines[0].startswith(skip_prefixes) or 'ANSWER SHEET' in lines[0]):
        lines.pop(0)
    return '\n'.join(lines)


def _prose_before_questions(block):
    block = _drop_directions(block)
    m = QUESTION_LINE.search(block)
    if m:
        block = block[:m.start()]
    return normalize_prose(block)


def _extract_cloze(text, s1_start, s2_start):
    block = _drop_directions(text[s1_start:s2_start])
    m = re.search(r'(?im)^\s*1\s*[\.\)]\s*', block)
    if m:
        block = block[:m.start()]
    return normalize_prose(block)


def _extract_readings(reading_block):
    part_a = PART_A.search(reading_block)
    if not part_a:
        return []
    pa_start = part_a.end()
    pb = PART_B.search(reading_block, pa_start)
    pc = PART_C.search(reading_block, pa_start)
    trans = TRANSLATION_SECTION.search(reading_block, pa_start)
    end = min([m.start() for m in (pb, pc, trans) if m] or [len(reading_block)])
    pa = reading_block[pa_start:end]
    heads = list(TEXT_HEADING.finditer(pa))
    out = []
    for i, h in enumerate(heads):
        seg_end = heads[i+1].start() if i + 1 < len(heads) else len(pa)
        prose = _prose_before_questions(pa[h.end():seg_end])
        if prose:
            out.append(prose)
    return out


def _strip_leading_part_b_choices(block):
    lines = block.splitlines()
    a_idx = next((i for i, line in enumerate(lines) if re.match(r'^\s*\[A\]\s*', line)), None)
    if a_idx is None:
        return block
    g_idx = next((i for i in range(a_idx, len(lines)) if re.match(r'^\s*\[G\]\s*', lines[i])), None)
    if g_idx is not None:
        end = g_idx + 1
    else:
        end = a_idx
        while end < len(lines) and re.match(r'^\s*\[[A-G]\]\s*', lines[end]):
            end += 1
    if end < len(lines) and not lines[end].strip():
        end += 1
    return '\n'.join(lines[:a_idx] + lines[end:])


def _clean_part_b(block):
    block = _drop_directions(block)
    block = _strip_leading_part_b_choices(block)
    marker = re.compile(r'(?im)^\s*(?:4\s*[1IlL]|4[2-5])\s*[\.]?\s*(?:[-_—–]+\s*)?$')
    block = marker.sub('', block)
    return normalize_prose(block)


def _fallback_part_b(reading_block):
    q40 = re.search(r'(?im)^\s*40\s*\.', reading_block)
    if not q40:
        return None
    directions = DIRECTIONS_START.search(reading_block, q40.end())
    if not directions:
        return None
    trans = TRANSLATION_SECTION.search(reading_block, directions.end())
    pc = PART_C.search(reading_block, directions.end())
    end = min([m.start() for m in (trans, pc) if m] or [len(reading_block)])
    return reading_block[directions.start():end]


def _extract_part_b(reading_block, year):
    if year < 2005:
        return []
    pb = PART_B.search(reading_block)
    if pb:
        pc = PART_C.search(reading_block, pb.end())
        trans = TRANSLATION_SECTION.search(reading_block, pb.end())
        end = min([m.start() for m in (pc, trans) if m] or [len(reading_block)])
        block = reading_block[pb.end():end]
    else:
        block = _fallback_part_b(reading_block)
        if block is None:
            return []
    prose = _clean_part_b(block)
    return [prose] if prose else []


def _extract_translation(text, year, reading_block):
    if year >= 2010:
        m = TRANSLATION_SECTION.search(text)
        if not m:
            return []
        w = WRITING_SECTION.search(text, m.end())
        block = text[m.end():w.start() if w else len(text)]
        prose = _drop_directions(block)
        prose = re.sub(r'(?m)^\s*46\.\s*$', '', prose, count=1)
        prose = normalize_prose(prose)
        return [prose] if prose else []
    if year >= 2005:
        pc = PART_C.search(reading_block)
        if not pc:
            return []
        block = reading_block[pc.end():]
    else:
        pb = PART_B.search(reading_block)
        if not pb:
            return []
        block = reading_block[pb.end():]
    prose = normalize_prose(_drop_directions(block))
    return [prose] if prose else []


def extract_sections(text, year):
    text = _canonicalize_for_matching(text)
    s1 = SECTION_I.search(text)
    s2 = SECTION_II.search(text, s1.end() if s1 else 0)
    if not s1 or not s2:
        return {'cloze': [], 'reading': [], 'part_b': [], 'translation': []}
    w = WRITING_SECTION.search(text, s2.end())
    exam_end = w.start() if w else len(text)
    core = text[:exam_end]
    s1 = SECTION_I.search(core)
    s2 = SECTION_II.search(core, s1.end())
    reading_block = core[s2.end():]
    cloze = _extract_cloze(core, s1.end(), s2.start())
    return {
        'cloze': [cloze] if cloze else [],
        'reading': _extract_readings(reading_block),
        'part_b': _extract_part_b(reading_block, year),
        'translation': _extract_translation(core, year, reading_block),
    }
