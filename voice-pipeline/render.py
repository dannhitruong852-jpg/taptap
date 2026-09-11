import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

INTENSITY_DELTA = {0: -0.08, 1: 0.0, 2: 0.10}


def generation_fingerprint(**fields):
    payload = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def resolve_exaggeration(emotion_cfg, intensity):
    value = emotion_cfg['exaggeration'] + INTENSITY_DELTA[int(intensity)]
    return round(min(0.90, max(0.25, value)), 2)


def preflight(reference_path=None):
    result = {
        'python_ok': True,
        'ffmpeg_ok': shutil.which('ffmpeg') is not None,
        'chatterbox_ok': importlib.util.find_spec('chatterbox') is not None,
        'reference_ok': True if reference_path is None else Path(reference_path).is_file(),
        'device': 'cpu'
    }
    try:
        import torch
        if torch.cuda.is_available():
            result['device'] = 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            result['device'] = 'mps'
    except Exception:
        pass
    result['ok'] = all(result[k] for k in ('python_ok','ffmpeg_ok','chatterbox_ok','reference_ok'))
    return result


def encode_opus(input_wav, output_opus, rate):
    rate = min(1.05, max(0.80, float(rate)))
    cmd = ['ffmpeg','-y','-i',str(input_wav),'-filter:a',f'atempo={rate:.3f}','-c:a','libopus','-b:a','48k',str(output_opus)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_with_chatterbox(text, reference_path, output_wav, *, device, exaggeration, cfg_weight, seed):
    import torch
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS
    torch.manual_seed(seed)
    model = ChatterboxTTS.from_pretrained(device=device)
    wav = model.generate(text, audio_prompt_path=str(reference_path), exaggeration=exaggeration, cfg_weight=cfg_weight)
    ta.save(str(output_wav), wav, model.sr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--reference')
    args = parser.parse_args()
    if args.preflight:
        result = preflight(args.reference)
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result['ok'] else 2)

if __name__ == '__main__':
    main()
