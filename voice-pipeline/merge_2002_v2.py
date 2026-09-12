"""Merge C v2 pilot chunks into seamless per-sentence assets for cloze + Text 1."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from generate_2002_v2 import build_cues, cache_valid, render_fingerprint_v2, save

ROOT=Path(__file__).resolve().parents[1]
ARTICLES=('cloze','text1')


def probe(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]))


def concat_sentence(entries, sentence, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);listing=tmp/'concat.txt'
        listing.write_text(''.join(f"file '{Path(entry['_source_opus']).as_posix()}'\n" for entry in entries),encoding='utf-8')
        wav=tmp/f"{sentence['id']}.wav"
        subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(wav)],check=True)
        targets={}
        for ext,codec,bitrate in [('opus','libopus','64k'),('mp3','libmp3lame','112k')]:
            target=output/f"v2-{sentence['id']}.{ext}"
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-ar','48000','-ac','1','-c:a',codec,'-b:a',bitrate,str(target)],check=True)
            targets[ext]=target
    actual=probe(targets['opus'])
    raw_cues=build_cues([{**seg,'duration_seconds':entry['duration_seconds']} for seg,entry in zip(sentence['segments'],entries)])
    nominal=raw_cues[-1]['end'] if raw_cues else actual
    scale=(actual/nominal) if nominal else 1
    cues=[]
    for cue in raw_cues:
        cues.append({**cue,'start':round(cue['start']*scale,3),'end':round(cue['end']*scale,3)})
    if cues:cues[-1]['end']=round(actual,3)
    first=sentence['segments'][0]
    return {
        'id':sentence['id'],
        'path':f"./audio/2002/c-{sentence.get('article_id','')}/v2-{sentence['id']}.opus",
        'mp3_path':f"./audio/2002/c-{sentence.get('article_id','')}/v2-{sentence['id']}.mp3",
        'duration_seconds':round(actual,3),
        'cues':cues,
        'actor_id':first.get('actor_id'),
        'emotion':first.get('emotion','neutral'),
        'intensity':first.get('intensity',1),
        'c_mode_version':'v2-pilot',
        'artificial_pause_ms':0,
        'post_tempo':False,
        'qa_status':'candidate'
    }


def collect_article(doc, manifests, target):
    expected={s['id']:s for row in doc['sentences'] for s in row['segments']}
    found={};rejected=[]
    for path in manifests:
        batch=json.loads(path.read_text())
        if batch.get('article')!=doc['article_id']:continue
        for sid,entry in batch.get('segments',{}).items():
            good=sid in expected and cache_valid(entry,path.parent)
            if good:good=entry.get('fingerprint')==render_fingerprint_v2(expected[sid],entry['reference_sha256'],entry['seed'])
            if not good:rejected.append(sid);continue
            source_opus=path.parent/f'v2-{sid}.opus';source_mp3=path.parent/f'v2-{sid}.mp3'
            shutil.copyfile(source_opus,target/source_opus.name);shutil.copyfile(source_mp3,target/source_mp3.name)
            found[sid]={**entry,'_source_opus':str(source_opus.resolve())}
    missing=[sid for sid in expected if sid not in found]
    return found,missing,rejected


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--incoming',required=True);args=parser.parse_args()
    incoming=Path(args.incoming);manifests=list(incoming.rglob('v2-shard-*.json'))
    summary={'version':'2002-c-v2-pilot','articles':[],'missing_segments':0,'seamless_sentences':0,'listening_qa':'pending_user_acceptance'}
    for article in ARTICLES:
        doc=json.loads((ROOT/f'kaoyan-reader-v1/content/2002/c/{article}.json').read_text())
        target=ROOT/f'kaoyan-reader-v1/audio/2002/c-{article}';target.mkdir(parents=True,exist_ok=True)
        found,missing,rejected=collect_article(doc,manifests,target)
        existing_path=target/'manifest.json';manifest=json.loads(existing_path.read_text()) if existing_path.exists() else {'article':article,'segments':{}}
        manifest['sentences']={};manifest['c_mode_version']='v2-pilot';manifest['v2_missing_segments']=missing;manifest['v2_rejected']=rejected
        if not missing:
            for sentence in doc['sentences']:
                sentence_for_merge={**sentence,'article_id':article}
                entries=[found[s['id']] for s in sentence['segments']]
                merged=concat_sentence(entries,sentence_for_merge,target)
                merged['path']=f'./audio/2002/c-{article}/v2-{sentence["id"]}.opus'
                merged['mp3_path']=f'./audio/2002/c-{article}/v2-{sentence["id"]}.mp3'
                manifest['sentences'][sentence['id']]=merged
        manifest['v2_status']='complete_candidate' if not missing and len(manifest['sentences'])==len(doc['sentences']) else 'partial_candidate'
        save(existing_path,manifest)
        summary['articles'].append({'id':article,'segments':len(found),'missing':missing,'seamless_sentences':len(manifest['sentences']),'status':manifest['v2_status']})
        summary['missing_segments']+=len(missing);summary['seamless_sentences']+=len(manifest['sentences'])
    save(ROOT/'reports/qa/2002-c-v2-pilot.json',summary)
    print(json.dumps(summary,indent=2))
    if summary['missing_segments']:
        raise SystemExit(2)

if __name__=='__main__':main()
