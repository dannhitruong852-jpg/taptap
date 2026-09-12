"""Publish only hash-verified assets matching this exact directed manuscript."""
import argparse
import json
import shutil
from pathlib import Path
from generate_2002 import cache_valid, render_fingerprint, save

ROOT=Path(__file__).resolve().parents[1]


def merge_article(doc,manifests,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    expected={s['id']:s for row in doc['sentences'] for s in row['segments']}
    result={'article':doc['article_id'],'segments':{},'missing':[],'rejected':[],
            'qa_status':'candidate','asr_qa':'not_performed','speaker_qa':'not_performed',
            'listening_qa':'pending_user_acceptance'}
    for path in manifests:
        batch=json.loads(path.read_text())
        if batch.get('article')!=doc['article_id']:continue
        for sid,entry in batch['segments'].items():
            good=sid in expected and cache_valid(entry,path.parent)
            if good:
                good=entry['fingerprint']==render_fingerprint(expected[sid],entry['reference_sha256'],entry['seed'])
            if not good:
                result['rejected'].append(sid);continue
            for ext in ('opus','mp3'):
                filename=f'{sid}.{ext}'
                if filename not in entry['files']:raise ValueError('Missing audio format')
                shutil.copyfile(path.parent/filename,output/filename)
            entry={**entry,'path':f"./audio/2002/c-{doc['article_id']}/{sid}.opus",
                   'mp3_path':f"./audio/2002/c-{doc['article_id']}/{sid}.mp3"}
            result['segments'][sid]=entry
    result['segments']={sid:result['segments'][sid] for sid in expected if sid in result['segments']}
    result['missing']=[sid for sid in expected if sid not in result['segments']]
    result['status']='complete_candidate' if not result['missing'] else 'partial_candidate'
    save(output/'manifest.json',result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--incoming',required=True);args=p.parse_args()
    files=list(Path(args.incoming).rglob('shard-*.json'))
    summary={'articles':[],'generated_segments':0,'missing_segments':0,
             'asr_qa':'not_performed','speaker_qa':'not_performed','c_listening_acceptance':'pending'}
    for path in sorted((ROOT/'kaoyan-reader-v1/content/2002/c').glob('*.json')):
        doc=json.loads(path.read_text())
        result=merge_article(doc,files,ROOT/f"kaoyan-reader-v1/audio/2002/c-{doc['article_id']}")
        summary['articles'].append({'id':doc['article_id'],'available':len(result['segments']),
                                    'missing':result['missing'],'status':result['status']})
        summary['generated_segments']+=len(result['segments']);summary['missing_segments']+=len(result['missing'])
    save(ROOT/'reports/qa/2002-audio.json',summary)
    save(ROOT/'kaoyan-reader-v1/content/2002/audio-status.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
