import json
import subprocess
from pathlib import Path

import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

from render import generation_fingerprint, resolve_exaggeration

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'kaoyan-reader-v1/content/2002/text1.json'
EMOTIONS = ROOT / 'voice-pipeline/config/emotions.json'
SOURCES = ROOT / 'voice-pipeline/references/sources.json'
OUT_DIR = ROOT / 'kaoyan-reader-v1/audio/2002/text1'
MODEL_VERSION = 'chatterbox-tts-0.1.7-original-english'


def flatten_segments(doc):
    out = []
    for sentence in doc.get('sentences', []):
        for segment in sentence.get('segments', []):
            item = dict(segment)
            item['sentence_id'] = sentence.get('id')
            out.append(item)
    return out


def load_reference_map():
    refs = json.loads(SOURCES.read_text(encoding='utf-8'))['references']
    return {item['actor_id']: item for item in refs}


def encode_opus(input_wav, output_opus, rate):
    rate = min(1.05, max(0.80, float(rate)))
    subprocess.run([
        'ffmpeg', '-y', '-i', str(input_wav),
        '-filter:a', f'atempo={rate:.3f}',
        '-c:a', 'libopus', '-b:a', '48k', str(output_opus)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    doc = json.loads(CONTENT.read_text(encoding='utf-8'))
    emotions = json.loads(EMOTIONS.read_text(encoding='utf-8'))['emotions']
    references = load_reference_map()
    segments = flatten_segments(doc)
    if len(segments) != 24:
        raise RuntimeError(f'expected 24 segments, got {len(segments)}')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = ChatterboxTTS.from_pretrained(device=device)
    manifest = {
        'article': {'year': 2002, 'section': 'Text 1'},
        'model_version': MODEL_VERSION,
        'segments': {}
    }

    for index, segment in enumerate(segments, start=1):
        actor_id = segment['actor_id']
        reference = references[actor_id]
        reference_path = ROOT / reference['local_path']
        if not reference_path.is_file():
            raise FileNotFoundError(reference_path)

        emotion_cfg = emotions[segment['emotion']]
        exaggeration = resolve_exaggeration(emotion_cfg, segment['intensity'])
        cfg_weight = emotion_cfg['cfg_weight']
        seed = 2002000 + index
        torch.manual_seed(seed)

        wav = model.generate(
            segment['text'],
            audio_prompt_path=str(reference_path),
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )
        tmp_wav = OUT_DIR / f"{segment['id']}.wav"
        opus = OUT_DIR / f"{segment['id']}.opus"
        ta.save(str(tmp_wav), wav, model.sr)
        encode_opus(tmp_wav, opus, segment['rate'])
        tmp_wav.unlink(missing_ok=True)

        fingerprint = generation_fingerprint(
            text=segment['text'],
            actor_id=actor_id,
            reference_pack_version=reference['reference_pack_version'],
            emotion=segment['emotion'],
            intensity=segment['intensity'],
            rate=segment['rate'],
            model_version=MODEL_VERSION,
        )
        manifest['segments'][segment['id']] = {
            'path': f"./audio/2002/text1/{segment['id']}.opus",
            'actor_id': actor_id,
            'emotion': segment['emotion'],
            'intensity': segment['intensity'],
            'rate': segment['rate'],
            'seed': seed,
            'fingerprint': fingerprint,
            'qa_status': 'candidate'
        }
        print(f"[{index:02d}/24] {segment['id']} actor={actor_id} emotion={segment['emotion']}")

    (OUT_DIR / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


if __name__ == '__main__':
    main()
