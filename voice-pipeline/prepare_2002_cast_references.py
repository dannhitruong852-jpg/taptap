"""Prepare same-speaker expressive reference clips for the 2002 content-selected cast.

EARS is CC BY-NC 4.0. These references and derivatives are for this noncommercial
study reader. Dataset speakers are anonymous IDs; no endorsement is implied.
"""
from __future__ import annotations
import argparse, hashlib, io, json, subprocess, tempfile, urllib.request, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'voice-pipeline/config/cast_2002.json'
EARS_RAW='https://raw.githubusercontent.com/facebookresearch/ears_dataset/main/'
EARS_RELEASE='https://github.com/facebookresearch/ears_dataset/releases/download/dataset/'


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def require_distinct_speakers(actors):
    speakers=[v['speaker'] for v in actors.values()]
    if len(speakers)!=len(set(speakers)):
        raise ValueError('Every materialized actor must use a distinct source speaker')

def find_member(names, speaker, stem):
    matches=[]
    for name in names:
        p=Path(name)
        if p.suffix.lower()!='.wav' or p.stem!=stem: continue
        if speaker in p.parts or name.startswith(speaker+'/') or f'/{speaker}/' in name:
            matches.append(name)
    if len(matches)!=1:
        raise ValueError(f'Expected exactly one {speaker}/{stem}.wav, got {matches}')
    return matches[0]

def fetch(url, path):
    req=urllib.request.Request(url,headers={'User-Agent':'kaoyan-reader-reference-builder/1.0'})
    with urllib.request.urlopen(req,timeout=120) as r, path.open('wb') as f:
        while True:
            chunk=r.read(1024*1024)
            if not chunk:break
            f.write(chunk)

def prepare(actor_id: str, output: Path):
    import numpy as np
    import soundfile as sf
    cfg=json.loads(CONFIG.read_text())
    require_distinct_speakers(cfg['actors'])
    actor=cfg['actors'][actor_id];speaker=actor['speaker'];output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        stats_path=td/'speaker_statistics.json';license_path=td/'LICENSE';archive=td/f'{speaker}.zip'
        fetch(EARS_RAW+'speaker_statistics.json',stats_path);fetch(EARS_RAW+'LICENSE',license_path)
        stats=json.loads(stats_path.read_text())[speaker]
        expected={'gender':actor['gender'],'age':actor['age_group'],'native language':actor['native_language']}
        for key,value in expected.items():
            if stats.get(key)!=value:raise ValueError(f'{speaker} metadata mismatch: {key}={stats.get(key)!r}, expected {value!r}')
        license_text=license_path.read_text()
        if 'Attribution-NonCommercial 4.0' not in license_text and 'CC BY-NC' not in license_text:
            raise ValueError('Unexpected EARS license text')
        fetch(EARS_RELEASE+f'{speaker}.zip',archive)
        report={'actor_id':actor_id,'speaker':speaker,'corpus':'EARS','license':'CC BY-NC 4.0','archive_sha256':sha256_file(archive),'variants':{},'human_listening_qa':'pending'}
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            for emotion,task in cfg['reference_tasks'].items():
                member=find_member(names,speaker,task);raw=z.read(member)
                wave,sr=sf.read(io.BytesIO(raw),dtype='float32',always_2d=True)
                mono=wave.mean(axis=1)
                if not np.isfinite(mono).all():raise ValueError('Non-finite reference samples')
                voiced=np.flatnonzero(np.abs(mono)>.006)
                if not len(voiced):raise ValueError(f'Silent reference {member}')
                start=max(0,int(voiced[0]) - int(.025*sr));end=min(len(mono),int(voiced[-1])+int(.04*sr),start+int(12*sr))
                clip=mono[start:end]
                if len(clip)/sr<2.5:raise ValueError(f'Reference too short: {member}')
                peak=float(np.max(np.abs(clip)));clipped=float(np.mean(np.abs(clip)>=.999))
                if clipped>.01:raise ValueError(f'Reference clipped: {member}')
                clip=clip*(.86/max(peak,.001))
                tmp=td/'clip.wav';sf.write(tmp,clip,sr,subtype='PCM_16')
                target=output/f'actor{actor_id}-{emotion}.wav'
                subprocess.run(['ffmpeg','-v','error','-y','-i',str(tmp),'-ar','24000','-ac','1','-c:a','pcm_s16le',str(target)],check=True)
                report['variants'][emotion]={'path':target.name,'task':task,'source_member':member,'source_sha256':sha256_bytes(raw),'sha256':sha256_file(target),'duration_seconds':round(len(clip)/sr,3)}
        (output/f'actor{actor_id}.json').write_text(json.dumps(report,indent=2)+'\n')
        (output/'LICENSE.EARS.txt').write_text(license_text)
        (output/'NOTICE.txt').write_text('EARS: Expressive Anechoic Recordings of Speech (Richter et al., Interspeech 2024).\nSource: https://github.com/facebookresearch/ears_dataset\nLicense: CC BY-NC 4.0.\nModified here by selecting, trimming, peak-normalizing and resampling anonymous-speaker excerpts for noncommercial study TTS conditioning. No endorsement is implied.\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--actor',required=True);p.add_argument('--output',default='voice-pipeline/references/2002-cast')
    args=p.parse_args();prepare(args.actor,Path(args.output))
