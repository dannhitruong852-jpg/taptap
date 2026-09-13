"""Render round-seven localized C v4 QA2 repair candidates."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from calibration.repair_search_r7 import build_repair_r7_render_plan
from calibration.render_auditions import MODEL, sha256, wav_metrics


def stable_repair_r7_seed(actor_id: str, scene_id: str, variant: str) -> int:
    raw = hashlib.sha256(f"c-v4-repair-r7|{actor_id}|{scene_id}|{variant}".encode()).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def render(profile_path: Path, script_path: Path, references_dir: Path, output: Path, device: str) -> Path:
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    script = json.loads(script_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    model = ChatterboxTTS.from_pretrained(device=device)
    completed = []
    for item in build_repair_r7_render_plan(profile, script):
        reference = references_dir / item["reference"]
        if not reference.is_file():
            raise FileNotFoundError(reference)
        stem = f"actor{item['actor_id']}-{item['scene_id']}-{item['variant']}"
        wav_path = output / f"{stem}.wav"
        opus_path = output / f"{stem}.opus"
        mp3_path = output / f"{stem}.mp3"
        seed = stable_repair_r7_seed(item["actor_id"], item["scene_id"], item["variant"])
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        audio = model.generate(
            item["synthesis_text"],
            audio_prompt_path=str(reference),
            exaggeration=item["exaggeration"],
            cfg_weight=item["cfg_weight"],
            temperature=item["temperature"],
            repetition_penalty=item["repetition_penalty"],
        )
        torchaudio.save(str(wav_path), audio.cpu(), model.sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav_path), "-c:a", "libopus", "-b:a", "64k", str(opus_path)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav_path), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3_path)], check=True)
        record = {
            **item,
            "seed": seed,
            "model": MODEL,
            "reference_sha256": sha256(reference),
            **wav_metrics(wav_path, len(item["text"].split())),
        }
        record["audio"] = {
            kind: {"path": path.name, "sha256": sha256(path)}
            for kind, path in (("wav", wav_path), ("opus", opus_path), ("mp3", mp3_path))
        }
        completed.append(record)
    manifest = output / f"actor{profile['actor_id']}-repair-r7.json"
    manifest.write_text(json.dumps({
        "schema_version": "c-v4-repair-audition-7",
        "actor_id": profile["actor_id"],
        "calibration_id": profile["calibration_id"],
        "repair_round": 7,
        "eligible": False,
        "renders": completed,
    }, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--script", type=Path, default=Path("voice-pipeline/calibration/audition_script.json"))
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    render(args.profile, args.script, args.references, args.output, args.device)
