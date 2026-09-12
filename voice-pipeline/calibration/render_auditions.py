"""Render an actor's complete C v4 audition battery with Chatterbox 0.1.7."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_grid import candidate_controls


MODEL = "chatterbox-tts==0.1.7-original-english"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_seed(actor_id: str, scene_id: str, variant: str) -> int:
    raw = hashlib.sha256(f"c-v4|{actor_id}|{scene_id}|{variant}".encode()).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def build_render_plan(profile: dict, script: dict) -> list[dict]:
    renders = []
    actor_id = profile["actor_id"]
    for scene in script["scenes"]:
        for controls in candidate_controls(profile, scene["intent"], scene["intensity"]):
            reference = profile["references"][controls["reference_state"]]
            renders.append({
                "actor_id": actor_id,
                "scene_id": scene["id"],
                "category": scene["category"],
                "intent": scene["intent"],
                "intensity": scene["intensity"],
                "text": scene["text"],
                "reference": reference,
                "seed": stable_seed(actor_id, scene["id"], controls["variant"]),
                **controls,
            })
    return renders


def wav_metrics(path: Path, word_count: int) -> dict:
    with wave.open(str(path), "rb") as audio:
        frames, rate, width = audio.getnframes(), audio.getframerate(), audio.getsampwidth()
        raw = audio.readframes(frames)
    duration = frames / rate
    peak_limit = (1 << (width * 8 - 1)) - 1
    samples = [int.from_bytes(raw[i:i + width], "little", signed=True) for i in range(0, len(raw), width)]
    clipping = sum(abs(value) >= peak_limit for value in samples) / max(1, len(samples))
    return {"duration_seconds": round(duration, 3), "wpm": round(word_count / duration * 60, 1), "clipping_ratio": round(clipping, 8)}


def render(profile_path: Path, script_path: Path, references_dir: Path, output: Path, device: str) -> Path:
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS

    profile = json.loads(profile_path.read_text())
    script = json.loads(script_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    model = ChatterboxTTS.from_pretrained(device=device)
    completed = []
    for item in build_render_plan(profile, script):
        reference = references_dir / item["reference"]
        if not reference.is_file():
            raise FileNotFoundError(reference)
        stem = f"actor{item['actor_id']}-{item['scene_id']}-{item['variant']}"
        wav_path, opus_path, mp3_path = output / f"{stem}.wav", output / f"{stem}.opus", output / f"{stem}.mp3"
        torch.manual_seed(item["seed"])
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(item["seed"])
        audio = model.generate(
            item["text"], audio_prompt_path=str(reference),
            exaggeration=item["exaggeration"], cfg_weight=item["cfg_weight"],
            temperature=item["temperature"], repetition_penalty=item["repetition_penalty"],
        )
        torchaudio.save(str(wav_path), audio.cpu(), model.sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav_path), "-c:a", "libopus", "-b:a", "64k", str(opus_path)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav_path), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3_path)], check=True)
        record = {**item, "model": MODEL, "reference_sha256": sha256(reference), **wav_metrics(wav_path, len(item["text"].split()))}
        record["audio"] = {kind: {"path": path.name, "sha256": sha256(path)} for kind, path in (("wav", wav_path), ("opus", opus_path), ("mp3", mp3_path))}
        completed.append(record)
    manifest = output / f"actor{profile['actor_id']}-auditions.json"
    manifest.write_text(json.dumps({"actor_id": profile["actor_id"], "calibration_id": profile["calibration_id"], "eligible": False, "human_voice_qa": "pending", "renders": completed}, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True)
    parser.add_argument("--profiles", type=Path, default=Path("voice-pipeline/calibration/actors"))
    parser.add_argument("--script", type=Path, default=Path("voice-pipeline/calibration/audition_script.json"))
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    render(args.profiles / f"{args.actor}.json", args.script, args.references, args.output, args.device)
