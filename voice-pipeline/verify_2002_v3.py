"""Verify published C v3 seamless sentence assets for all 2002 units."""
from __future__ import annotations
import argparse,hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARTICLES=('cloze','text1','text2','text3','text4','translation')
VERSION='v3-content-cast'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def verify_article_manifest(content,manifest_path,decode=True):
    manifest_path=Path(manifest_path);manifest=json.loads(manifest_path.read_text())
    errors=[];sentences=manifest.get('sentences',{})
    if manifest.get('c_mode_version')!=VERSION:errors.append('wrong_c_mode_version')
    for sentence in content['sentences']:
        sid=sentence['id'];entry=sentences.get(sid)
        if not entry:
            errors.append(f'missing_sentence:{sid}');continue
        if entry.get('c_mode_version')!=VERSION:errors.append(f'wrong_sentence_version:{sid}')
        if entry.get('artificial_pause_ms')!=0:errors.append(f'artificial_pause:{sid}')
        if entry.get('post_tempo') is not False:errors.append(f'post_tempo:{sid}')
        if entry.get('actor_sequence')!=[seg.get('actor_id') for seg in sentence['segments']]:errors.append(f'actor_sequence:{sid}')
        for key in ('path','mp3_path'):
            rel=entry.get(key)
            if not rel:
                errors.append(f'missing_path:{sid}:{key}');continue
            name=Path(rel).name;path=manifest_path.parent/name
            if not path.is_file():errors.append(f'missing_file:{sid}:{name}');continue
            expected=entry.get('files',{}).get(name)
            if not expected or sha(path)!=expected:errors.append(f'hash:{sid}:{name}')
            if decode:
                try:subprocess.check_call(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                except Exception:errors.append(f'decode:{sid}:{name}')
    return {'article':content['article_id'],'sentences':len(content['sentences']),'verified_sentences':len(content['sentences'])-len({e.split(':')[1] for e in errors if e.startswith('missing_sentence:')}),'errors':errors,'complete':not errors}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(ROOT/'kaoyan-reader-v1'));parser.add_argument('--no-decode',action='store_true');args=parser.parse_args()
    reader=Path(args.root);reports=[]
    for article in ARTICLES:
        content=json.loads((reader/f'content/2002/c/{article}.json').read_text())
        report=verify_article_manifest(content,reader/f'audio/2002/c-{article}/manifest.json',decode=not args.no_decode)
        reports.append(report)
    summary={'version':'2002-c-v3-content-cast','articles':reports,'sentences':sum(r['sentences'] for r in reports),'errors':sum((r['errors'] for r in reports),[])}
    summary['complete']=not summary['errors']
    out=ROOT/'reports/qa/2002-c-v3-verification.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    if not summary['complete']:raise SystemExit(2)

if __name__=='__main__':main()
