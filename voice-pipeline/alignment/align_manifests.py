"""Attach real word timestamps to final C v4 sentence manifests."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from alignment.ctc_align import align_tokens
from alignment.normalize_transcript import normalize_transcript, ctc_text

ROOT=Path(__file__).resolve().parents[2]
ARTICLES_2002=("cloze","text1","text2","text3","text4","translation")


def attach_word_times(words:list[dict], char_frames:list[int], frame_seconds:float, audio_duration:float,
                      char_scores:list[float]|None=None)->list[dict]:
    needed=sum(len(w['normalized']) for w in words)
    if len(char_frames)!=needed:
        raise ValueError(f'alignment failed: expected {needed} character frames, got {len(char_frames)}')
    if char_scores is not None and len(char_scores)!=needed:
        raise ValueError('alignment failed: character score count mismatch')
    out=[];cursor=0
    for word in words:
        n=len(word['normalized']);frames=char_frames[cursor:cursor+n]
        scores=char_scores[cursor:cursor+n] if char_scores is not None else []
        start=max(0.0,frames[0]*frame_seconds)
        end=min(audio_duration,(frames[-1]+1)*frame_seconds)
        out.append({
            'word':word['source'],'char_start':word['char_start'],'char_end':word['char_end'],
            'start':round(start,3),'end':round(end,3),
            'score':round(sum(scores)/len(scores),4) if scores else 1.0,
        })
        cursor+=n
    return out


def validate_word_timeline(words:list[dict], audio_duration:float)->list[str]:
    errors=[];last_start=-1.0;last_end=-1.0
    for i,w in enumerate(words):
        start=float(w['start']);end=float(w['end'])
        if end<start:
            errors.append(f'word {i}: end before start')
        if start<last_start or end<last_end:
            errors.append(f'word {i}: nonmonotonic timestamps')
        last_start=start;last_end=end
    if words and float(words[-1]['end'])>audio_duration+.080:
        errors.append('final word end exceeds audio duration tolerance')
    return errors


def align_sentence_audio(audio_path:Path, transcript:str)->list[dict]:
    import torch
    import torchaudio
    bundle=torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
    model=bundle.get_model().eval()
    waveform,sr=torchaudio.load(str(audio_path))
    waveform=waveform.mean(dim=0,keepdim=True)
    if sr!=bundle.sample_rate:
        waveform=torchaudio.functional.resample(waveform,sr,bundle.sample_rate)
    with torch.inference_mode():
        emission,_=model(waveform)
        logp=torch.log_softmax(emission[0],dim=-1).cpu()
    labels=list(bundle.get_labels())
    label_to_id={label:i for i,label in enumerate(labels)}
    blank_id=0
    words=normalize_transcript(transcript)
    target=ctc_text(words)
    try:
        token_ids=[label_to_id[ch] for ch in target]
    except KeyError as exc:
        raise ValueError(f'alignment failed: unsupported normalized symbol {exc.args[0]!r}') from exc
    path=align_tokens(logp.tolist(),token_ids,blank_id=blank_id)
    delimiter_id=label_to_id.get('|')
    char_frames=[];char_scores=[]
    for ch,item in zip(target,path):
        if delimiter_id is not None and item['token_id']==delimiter_id:
            continue
        char_frames.append(item['frame'])
        char_scores.append(math.exp(item['score']))
    duration=waveform.shape[-1]/bundle.sample_rate
    frame_seconds=duration/logp.shape[0]
    result=attach_word_times(words,char_frames,frame_seconds,duration,char_scores)
    errors=validate_word_timeline(result,duration)
    if errors:
        raise ValueError('alignment failed: '+'; '.join(errors))
    return result


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--year',type=int,required=True)
    parser.add_argument('--root',required=True)
    args=parser.parse_args()
    if args.year!=2002:
        raise ValueError('first production scope is 2002')
    root=Path(args.root)
    failures=[]
    for article in ARTICLES_2002:
        content=json.loads((root/f'content/{args.year}/c/{article}.json').read_text(encoding='utf-8'))
        by_id={s['id']:s for s in content.get('sentences',[])}
        directory=root/f'audio/{args.year}/v4/c-{article}'
        manifest_path=directory/'manifest.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        for sid,entry in manifest.get('sentences',{}).items():
            source=by_id.get(sid)
            if source is None:
                failures.append(f'{article}/{sid}: missing source sentence')
                entry['alignment_status']='failed'
                continue
            try:
                entry['words']=align_sentence_audio(directory/f'v4-{sid}.opus',source['en'])
                entry['alignment_status']='passed'
                entry['alignment_model']='torchaudio-WAV2VEC2_ASR_BASE_960H-ctc-v1'
                entry['aligned_generation_fingerprint']=entry.get('generation_fingerprint')
            except Exception as exc:
                entry['alignment_status']='failed';entry.pop('words',None)
                failures.append(f'{article}/{sid}: {exc}')
        manifest['alignment_status']='passed' if not any(v.get('alignment_status')!='passed' for v in manifest.get('sentences',{}).values()) else 'failed'
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=root/f'reports/c-v4-{args.year}-alignment.json'
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'year':args.year,'status':'passed' if not failures else 'failed','failures':failures},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if failures:
        raise SystemExit(2)


if __name__=='__main__':
    main()
