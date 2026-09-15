import argparse, json, tarfile
from pathlib import Path, PurePosixPath

ALLOWED_YEARS={'2011','2012'}
ALLOWED_UNITS={'cloze','text1','text2','text3','text4','partb','translation'}

def safe_member(name:str):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or len(p.parts)!=2:
        return None
    year,filename=p.parts
    if year not in ALLOWED_YEARS or not filename.endswith('.candidate.json'):
        return None
    unit=filename.removesuffix('.candidate.json')
    if unit not in ALLOWED_UNITS:
        return None
    return year,unit,filename

def safe_directory(name:str):
    p=PurePosixPath(name)
    return not p.is_absolute() and '..' not in p.parts and len(p.parts)==1 and p.parts[0] in ALLOWED_YEARS

def materialize(bundle:Path, root:Path):
    written=[]
    with tarfile.open(bundle,'r:gz') as tf:
        members=tf.getmembers(); seen=set()
        for m in members:
            if m.isdir():
                if not safe_directory(m.name): raise ValueError(f'unsafe/unexpected member: {m.name}')
                continue
            info=safe_member(m.name)
            if not info or not m.isfile(): raise ValueError(f'unsafe/unexpected member: {m.name}')
            year,unit,filename=info; key=(year,unit)
            if key in seen: raise ValueError(f'duplicate member: {m.name}')
            seen.add(key); data=tf.extractfile(m).read().decode('utf-8'); doc=json.loads(data)
            if int(doc.get('year',-1))!=int(year): raise ValueError(f'bad year: {m.name}')
            art=doc.get('article') or {}; qa=doc.get('qa') or {}
            if art.get('id')!=unit or not art.get('rows'): raise ValueError(f'bad article: {m.name}')
            if qa.get('source_scope_verified') is not True or qa.get('translation_alignment_reviewed') is not True: raise ValueError(f'candidate not reviewed: {m.name}')
            if not all(len(r)>=3 and r[1] and r[2] for r in art['rows']): raise ValueError(f'empty bilingual row: {m.name}')
            dst=root/year/filename; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_text(data,encoding='utf-8'); written.append(dst)
    expected={(y,u) for y in ALLOWED_YEARS for u in ALLOWED_UNITS}
    if seen!=expected: raise ValueError(f'bundle coverage mismatch: missing={sorted(expected-seen)} extra={sorted(seen-expected)}')
    return written

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('bundle',type=Path); ap.add_argument('root',type=Path); a=ap.parse_args()
    w=materialize(a.bundle,a.root); print(json.dumps({'written':[str(x) for x in w],'count':len(w)}))
if __name__=='__main__': main()
