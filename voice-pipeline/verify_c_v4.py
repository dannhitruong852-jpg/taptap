"""Technical verifier for C v4 candidate manifests. Human QA remains pending."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ARTICLES_2002=("cloze","text1","text2","text3","text4","translation")


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _probe(path: Path) -> tuple[str,float]:
    codec=subprocess.check_output([
        'ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_name',
        '-of','default=nw=1:nk=1',str(path)
    ], text=True).strip()
    duration=float(subprocess.check_output([
        'ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)
    ], text=True).strip())
    return codec,duration


def verify_manifest(manifest: dict, *, base_dir: Path | None=None, require_files: bool=True) -> list[str]:
    errors=[]
    if manifest.get('c_mode_version')!='v4':
        errors.append('manifest is not c_mode_version v4')
    for sid,entry in manifest.get('sentences',{}).items():
        qa=entry.get('qa',{})
        if qa.get('technical')!='passed':
            errors.append(f'{sid}: technical QA not passed')
        if qa.get('voice')!='pending' or qa.get('c_direction')!='pending':
            errors.append(f'{sid}: human QA must remain pending')
        if entry.get('artificial_pause_ms')!=0:
            errors.append(f'{sid}: artificial pause must be zero')
        if entry.get('post_tempo') is not False:
            errors.append(f'{sid}: post tempo must be false')
        if not entry.get('generation_fingerprint'):
            errors.append(f'{sid}: missing generation fingerprint')
        if not entry.get('actor_sequence'):
            errors.append(f'{sid}: missing actor sequence')
        if require_files:
            if base_dir is None:
                errors.append(f'{sid}: base_dir required for file verification')
                continue
            for name,digest in entry.get('files',{}).items():
                path=base_dir/name
                if not path.is_file():
                    errors.append(f'{sid}: missing file {name}')
                    continue
                if sha(path)!=digest:
                    errors.append(f'{sid}: hash mismatch {name}')
                    continue
                codec,duration=_probe(path)
                if path.suffix=='.opus' and codec!='opus':
                    errors.append(f'{sid}: wrong codec for {name}: {codec}')
                if path.suffix=='.mp3' and codec!='mp3':
                    errors.append(f'{sid}: wrong codec for {name}: {codec}')
                if duration<=0:
                    errors.append(f'{sid}: nonpositive duration {name}')
    return errors


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--year',type=int,required=True)
    parser.add_argument('--root',required=True)
    args=parser.parse_args()
    if args.year!=2002:
        raise ValueError('first production scope is 2002')
    root=Path(args.root)
    summary={'year':args.year,'articles':{},'errors':[],'qa':{'technical':'candidate','voice':'pending','c_direction':'pending'}}
    for article in ARTICLES_2002:
        directory=root/f'audio/{args.year}/v4/c-{article}'
        path=directory/'manifest.json'
        if not path.is_file():
            summary['errors'].append(f'{article}: missing manifest')
            summary['articles'][article]={'status':'missing'}
            continue
        manifest=json.loads(path.read_text(encoding='utf-8'))
        errors=verify_manifest(manifest,base_dir=directory,require_files=True)
        if manifest.get('missing_segments'):
            errors.append(f"{article}: missing source coverage {manifest['missing_segments']}")
        summary['articles'][article]={'status':'passed' if not errors else 'failed','sentences':len(manifest.get('sentences',{})),'errors':errors}
        summary['errors'].extend(errors)
    summary['qa']['technical']='passed' if not summary['errors'] else 'failed'
    report=root/f'reports/c-v4-{args.year}-verify.json'
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    if summary['errors']:
        raise SystemExit(2)


if __name__=='__main__':
    main()
