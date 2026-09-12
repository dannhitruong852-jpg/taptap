"""C-mode v2 pilot renderer for 2002 cloze + Text 1.
Keeps semantic performance chunks, removes all artificial silence/post-tempo,
and writes isolated chunks that are later assembled into seamless sentence assets.
"""
import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import time
from pathlib import Path

from batching import select_shard
from generate_2002 import sha, save, spoken_text
from render import generation_fingerprint

ROOT=Path(__file__).resolve().parents[1]
MODEL='chatterbox-tts-0.1.7-original-english'
RENDER_VERSION='2002-c-v2-pilot'

PERFORMANCE={
    'neutral': (.48,.48),
    'warm': (.66,.36),
    'lively': (.72,.33),
    'serious': (.64,.39),
    'curious': (.70,.34),
    'ironic': (.80,.29),
    'tense': (.74,.33),
    'emotional': (.76,.31),
}


def performance_controls(segment):
    emotion=segment.get('emotion','neutral')
    exaggeration,cfg=PERFORMANCE.get(emotion,PERFORMANCE['neutral'])
    if int(segment.get('intensity',1)) >= 2:
        exaggeration=min(.88,exaggeration+.05)
        cfg=max(.24,cfg-.03)
    return {
        'exaggeration':round(exaggeration,3),
        'cfg_weight':round(cfg,3),
        'post_tempo':False,
        'artificial_pause_ms':0,
    }


def build_cues(segments):
    cursor=0.0
    cues=[]
    for segment in segments:
        duration=float(segment['duration_seconds'])
        cue={
            'id':segment['id'],
            'text':segment.get('text',''),
            'emotion':segment.get('emotion','neutral'),
            'intensity':int(segment.get('intensity',1)),
            'start':round(cursor,3),
            'end':round(cursor+duration,3),
        }
        cues.append(cue)
        cursor+=duration
    return cues


def render_fingerprint_v2(segment,reference_sha,seed):
    controls=performance_controls(segment)
    return generation_fingerprint(
        text=spoken_text(segment['text']),actor=segment['actor_id'],reference_sha=reference_sha,seed=seed,
        rate=1.0,exaggeration=controls['exaggeration'],cfg_weight=controls['cfg_weight'],
        pause_before_ms=0,pause_after_ms=0,model=MODEL,render_version=RENDER_VERSION,
        temperature=.8,repetition_penalty=1.2)


def cache_valid(entry,output):
    files=entry.get('files',{})
    return bool(files) and all((Path(output)/name).is_file() and sha(Path(output)/name)==digest for name,digest in files.items())


def run_segments(segments,output,render_one,references,article,max_attempts=2,shard=0):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    manifest_path=output/f'v2-shard-{shard}.json'
    old=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'segments':{}}
    report={'article':article,'model':MODEL,'render_version':RENDER_VERSION,'shard':shard,
            'segments':{},'failures':[],'cache_hits':0,'elapsed_seconds':0,
            'asr_qa':'not_performed','speaker_qa':'not_performed','listening_qa':'pending_user_acceptance'}
    started=time.monotonic()
    for segment in segments:
        sid=segment['id'];base_seed=int(hashlib.sha256(f'2002:v2:{article}:{sid}'.encode()).hexdigest()[:8],16)
        ref_sha=references[segment['actor_id']];cached=old['segments'].get(sid)
        if cached and any(cached.get('fingerprint')==render_fingerprint_v2(segment,ref_sha,base_seed+a) for a in range(max_attempts)) and cache_valid(cached,output):
            report['segments'][sid]=cached;report['cache_hits']+=1;continue
        for attempt in range(max_attempts):
            seed=base_seed+attempt
            try:
                result=render_one(segment,seed,output)
                files={f'v2-{sid}.{ext}':sha(output/f'v2-{sid}.{ext}') for ext in ('opus','mp3')}
                controls=performance_controls(segment)
                result.update({'path':f'./audio/2002/c-{article}/v2-{sid}.opus',
                               'mp3_path':f'./audio/2002/c-{article}/v2-{sid}.mp3',
                               'actor_id':segment['actor_id'],'emotion':segment['emotion'],
                               'intensity':segment['intensity'],'seed':seed,'attempts':attempt+1,
                               'reference_sha256':ref_sha,'fingerprint':render_fingerprint_v2(segment,ref_sha,seed),
                               'files':files,**controls})
                report['segments'][sid]=result
                print(f'v2 {article}/{sid} generated on attempt {attempt+1}',flush=True);break
            except Exception as exc:
                print(f'v2 {article}/{sid} attempt {attempt+1}: {exc}',flush=True)
                if attempt+1==max_attempts:report['failures'].append({'id':sid,'error':str(exc),'attempts':max_attempts})
        report['elapsed_seconds']=round(time.monotonic()-started,2);save(manifest_path,report)
    report['elapsed_seconds']=round(time.monotonic()-started,2);save(manifest_path,report);return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--article',required=True,choices=['cloze','text1'])
    parser.add_argument('--shard',type=int,default=0);parser.add_argument('--shards',type=int,default=3);args=parser.parse_args()
    import numpy as np
    import torch
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS
    torch.set_num_threads(int(os.environ.get('TTS_THREADS','4')))
    doc=json.loads((ROOT/f'kaoyan-reader-v1/content/2002/c/{args.article}.json').read_text())
    source_segments=[s for row in doc['sentences'] for s in row['segments']]
    segments=select_shard(source_segments,args.shards,args.shard)
    references=json.loads((ROOT/'voice-pipeline/references/sources.json').read_text())['references']
    ref_paths={x['actor_id']:ROOT/x['local_path'] for x in references};ref_hashes={actor:sha(path) for actor,path in ref_paths.items()}
    model=ChatterboxTTS.from_pretrained(device='cuda' if torch.cuda.is_available() else 'cpu')
    output=ROOT/f'kaoyan-reader-v1/audio/2002/c-{args.article}'

    def render_one(segment,seed,directory):
        random.seed(seed);np.random.seed(seed%(2**32));torch.manual_seed(seed)
        controls=performance_controls(segment)
        with torch.inference_mode():
            wav=model.generate(spoken_text(segment['text']),audio_prompt_path=str(ref_paths[segment['actor_id']]),
                               exaggeration=controls['exaggeration'],cfg_weight=controls['cfg_weight'],
                               temperature=.8,repetition_penalty=1.2)
        samples=wav.detach().float().cpu().numpy().reshape(-1);duration=len(samples)/model.sr
        if not np.isfinite(samples).all() or duration<.25:raise ValueError('Invalid/nonfinite/empty waveform')
        audible=np.flatnonzero(np.abs(samples)>.008)
        if not len(audible):raise ValueError('Silent waveform')
        left=max(0,int(audible[0])-int(.020*model.sr));right=min(len(samples),int(audible[-1])+int(.035*model.sr))
        wav=wav[:,left:right];duration=(right-left)/model.sr
        words=len(re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?",spoken_text(segment['text'])));wpm=words*60/duration
        if words>=8 and not 70<=wpm<=320:raise ValueError(f'Suspected truncation/repetition: {wpm:.1f} words/minute')
        clipped=float(np.mean(np.abs(samples)>=.999))
        if clipped>.015:raise ValueError(f'Excessive clipping: {clipped:.4f}')
        sid=segment['id'];raw=Path(directory)/f'v2-{sid}.wav';ta.save(str(raw),wav,model.sr)
        filters='loudnorm=I=-19:TP=-2:LRA=11'
        for ext,codec,bitrate in [('opus','libopus','64k'),('mp3','libmp3lame','112k')]:
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-af',filters,'-ar','48000','-ac','1','-c:a',codec,'-b:a',bitrate,str(Path(directory)/f'v2-{sid}.{ext}')],check=True)
        raw.unlink()
        actual=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(Path(directory)/f'v2-{sid}.opus')]))
        return {'duration_seconds':round(actual,3),'raw_wpm':round(wpm,1),'clipped_fraction':clipped,
                'technical_qa':'passed','qa_status':'candidate','c_mode_version':'v2-pilot'}

    result=run_segments(segments,output,render_one,ref_hashes,args.article,shard=args.shard)
    print(json.dumps({'generated':len(result['segments']),'failed':len(result['failures']),'cache_hits':result['cache_hits'],'seconds':result['elapsed_seconds']}))

if __name__=='__main__':main()
