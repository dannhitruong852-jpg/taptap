"""Preserve the already approved three-source CMU ARCTIC pilot references."""
import io
import subprocess
import wave
from pathlib import Path
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
FILES={'05':'bdl-00000-of-00001-0c683a89629915f1.parquet',
       '12':'jmk-00000-of-00001-1e65c0fe4d8b0b42.parquet',
       '13':'rms-00000-of-00001-0f0762376a6ef8cc.parquet'}
OUT=ROOT/'voice-pipeline/references/generated'
OUT.mkdir(parents=True,exist_ok=True)
for actor,filename in FILES.items():
    source=Path('/tmp')/filename
    url=f'https://huggingface.co/datasets/MikhailT/cmu-arctic/resolve/main/data/{filename}?download=true'
    subprocess.run(['curl','-L','--fail','--retry','3','-o',str(source),url],check=True)
    frames=[];params=None
    for row in pq.read_table(source,columns=['audio']).slice(0,8).column('audio').to_pylist():
        with wave.open(io.BytesIO(row['bytes']),'rb') as item:
            current=(item.getnchannels(),item.getsampwidth(),item.getframerate())
            if params is not None and params!=current:raise ValueError('Reference format mismatch')
            params=current;frames.append(item.readframes(item.getnframes()))
    raw=OUT/f'{actor}-raw.wav';target=OUT/f'actor{actor}-neutral.wav'
    with wave.open(str(raw),'wb') as item:
        item.setnchannels(params[0]);item.setsampwidth(params[1]);item.setframerate(params[2]);item.writeframes(b''.join(frames))
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-t','18','-af','loudnorm=I=-20:TP=-2:LRA=7',str(target)],check=True)
    raw.unlink();source.unlink()
print('Three lawful pilot reference clips prepared; this is not the complete 15-actor library.')
