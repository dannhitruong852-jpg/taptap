import re

_PAGE_NOISE = re.compile(r'(?im)^\s*(?:英语[^\n]{0,40}第?\s*\d+\s*页[^\n]*|第\s*\d+\s*页[^\n]*|\d{4}-\d+)\s*$')


def normalize_prose(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\x0c', '\n')
    text = _PAGE_NOISE.sub('', text)
    text = re.sub(r'[ \t]+', ' ', text)
    lines = [line.strip() for line in text.split('\n')]
    paragraphs = []
    current = []
    for line in lines:
        if not line:
            if current:
                paragraphs.append(' '.join(current))
                current = []
            continue
        if current and current[-1].endswith('-') and re.search(r'[A-Za-z]-$', current[-1]) and re.match(r'^[a-z]', line):
            current[-1] = current[-1][:-1] + line
        else:
            current.append(line)
    if current:
        paragraphs.append(' '.join(current))
    return '\n\n'.join(p.strip() for p in paragraphs if p.strip())
