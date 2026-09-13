"""Render the same emotion-shifting article through all 15 C v4 actors."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from calibration.build_expansion_profiles import build_profile as build_expansion_profile
from calibration.candidate_grid import candidate_controls
from calibration.render_auditions import MODEL, sha256

ACTORS = tuple(f"{i:02d}" for i in range(1, 16))
EXPANSION_ACTORS = {"03", "06", "07", "10", "11", "14", "15"}


def _load_profile(profiles_dir: Path, actor_id: str) -> dict:
    path = profiles_dir / f"{actor_id}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    if actor_id in EXPANSION_ACTORS:
        return build_expansion_profile(actor_id)
    raise FileNotFoundError(path)


def _stable_seed(actor_id: str, segment_id: str) -> int:
    raw = hashlib.sha256(f"c-v4-article-preview|{actor_id}|{segment_id}".encode()).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def _controls(profile: dict, intent: str, intensity: int) -> dict:
    selected = profile.get("selected_candidates", {}).get(intent)
    if selected:
        return {
            "variant": selected.get("variant", "selected"),
            "delivery": "production_selected",
            "reference_state": selected["reference_state"],
            "exaggeration": selected["exaggeration"],
            "cfg_weight": selected["cfg_weight"],
            "temperature": selected["temperature"],
            "repetition_penalty": selected["repetition_penalty"],
            "artificial_pause_ms": 0,
            "post_tempo": False,
        }
    return candidate_controls(profile, intent, intensity)[1]


def build_article_render_plan(profiles_dir: Path, script: dict) -> dict[str, list[dict]]:
    plans: dict[str, list[dict]] = {}
    for actor_id in ACTORS:
        profile = _load_profile(profiles_dir, actor_id)
        items = []
        for segment in script["segments"]:
            controls = _controls(profile, segment["intent"], segment["intensity"])
            reference_state = controls["reference_state"]
            reference = profile["references"][reference_state]
            items.append({
                "actor_id": actor_id,
                "segment_id": segment["id"],
                "intent": segment["intent"],
                "intensity": segment["intensity"],
                "text": segment["text"],
                "reference": reference,
                "seed": _stable_seed(actor_id, segment["id"]),
                **controls,
            })
        plans[actor_id] = items
    return plans


def render_actor(actor_id: str, profile_path: Path, script_path: Path, references_dir: Path, output: Path, device: str) -> Path:
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    script = json.loads(script_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    model = ChatterboxTTS.from_pretrained(device=device)
    segment_paths = []
    records = []

    for segment in script["segments"]:
        controls = _controls(profile, segment["intent"], segment["intensity"])
        reference = references_dir / profile["references"][controls["reference_state"]]
        if not reference.is_file():
            raise FileNotFoundError(reference)
        prompt = reference
        if actor_id == "15" and segment["intent"] == "curious_probe":
            x11 = references_dir / "actor15-08-probe-X11.wav"
            if x11.is_file():
                prompt = x11

        seed = _stable_seed(actor_id, segment["id"])
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        audio = model.generate(
            segment["text"],
            audio_prompt_path=str(prompt),
            exaggeration=controls["exaggeration"],
            cfg_weight=controls["cfg_weight"],
            temperature=controls["temperature"],
            repetition_penalty=controls["repetition_penalty"],
        )
        wav = output / f"actor{actor_id}-{segment['id']}.wav"
        torchaudio.save(str(wav), audio.cpu(), model.sr)
        segment_paths.append(wav)
        records.append({
            "segment_id": segment["id"],
            "intent": segment["intent"],
            "reference": reference.name,
            "prompt_reference": prompt.name,
            "seed": seed,
            **controls,
            "wav_sha256": sha256(wav),
        })

    concat = output / f"actor{actor_id}-concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_paths), encoding="utf-8")
    full_wav = output / f"actor{actor_id}-article.wav"
    full_mp3 = output / f"actor{actor_id}-article.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(full_wav)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full_wav), "-c:a", "libmp3lame", "-b:a", "128k", str(full_mp3)], check=True)
    concat.unlink(missing_ok=True)

    manifest = output / f"actor{actor_id}-article.json"
    manifest.write_text(json.dumps({
        "schema_version": "c-v4-article-preview-1",
        "model": MODEL,
        "actor_id": actor_id,
        "segments": records,
        "full_audio": {
            "wav": {"path": full_wav.name, "sha256": sha256(full_wav)},
            "mp3": {"path": full_mp3.name, "sha256": sha256(full_mp3)},
        },
        "artificial_pause_ms": 0,
        "post_tempo": False,
    }, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True, choices=ACTORS)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--script", type=Path, default=Path("voice-pipeline/calibration/article_emotion_probe.json"))
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    render_actor(args.actor, args.profile, args.script, args.references, args.output, args.device)
