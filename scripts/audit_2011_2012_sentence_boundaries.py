import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEARS = (2011, 2012)
UNITS = ('cloze','text1','text2','text3','text4','partb','translation')
SETS = (
    ('terminal', set('。！？')),
    ('plus_semicolon', set('。！？；')),
    ('plus_colon', set('。！？；：')),
)


def main():
    for year in YEARS:
        for unit in UNITS:
            path = ROOT / 'reports' / 'content-freeze' / str(year) / f'{unit}.candidate.json'
            doc = json.loads(path.read_text(encoding='utf-8'))
            rows = doc['article']['rows']
            qa = doc.get('qa') or {}
            expected = qa.get('sentence_count')
            en = ''.join(str(row[1]) for row in rows)
            zh = ''.join(str(row[2]) for row in rows)
            en_parts = [part for part in en.split('|') if part]
            counts = {name: sum(ch in marks for ch in zh) for name, marks in SETS}
            exact = [name for name, count in counts.items() if count == expected]
            print(json.dumps({
                'year': year,
                'unit': unit,
                'expected': expected,
                'rows': len(rows),
                'english_pipe_segments': len(en_parts),
                'zh_boundary_counts': counts,
                'exact_sets': exact,
            }, ensure_ascii=False))


if __name__ == '__main__':
    main()
