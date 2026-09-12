"""Generic C v4 candidate renderer: Director Intent -> Actor Adapter -> Chatterbox.

This renderer creates semantic/role chunk candidates only. Final browser assets are
one seamless sentence produced by merge_c_v4.py. V4 never changes delivery with a
post-generation tempo filter and never inserts artificial silence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import time
from pathlib import Path

from adapters.chatterbox_actor_adapter import resolve_controls
from build_c_v4_voice_plan import build_voice_plan
from generate_2002 import sha, spoken_text
from render import generation_fingerprint

ROOT = Path(__file__).resolve().parents[1]
MODEL = "chatterbox-tts-0.1.7-original-english"
RENDER_VERSION = "c-v4-actor-adapter"
ARTICLES_2002 = ("cloze", "text1", "text2", "text3", "text4", "translation")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def deterministic_seed(year: int, article: str, sentence_id: str, segment_id: str) -> int:
    payload = f"c-v4:{year}:{article}:{sentence_id}:{segment_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def select_sentence_shard(sentences: list[dict], shards: int, shard: int) -> list[dict]:
    if shards < 1 or not 0 <= shard < shards:
        raise ValueError("invalid shard")
    return [row for index, row in enumerate(sentences) if index % shards == shard]


def segment_fingerprint(text: str, controls: dict, reference_sha: str, seed: int) -> str:
    return generation_fingerprint(
        text=spoken_text(text), actor=controls["actor_id"], director_intent=controls["director_intent"],
        intensity=controls["intensity"], reference_sha=reference_sha, seed=seed,
        exaggeration=controls["exaggeration"], cfg_weight=controls["cfg_weight"],
        temperature=controls["temperature"], repetition_penalty=controls["repetition_penalty"],
        profile_hash=controls["profile_hash"], calibration_id=controls["calibration_id"],
        model=MODEL, render_version=RENDER_VERSION, artificial_pause_ms=0, post_tempo=False,
    )


def build_candidate_entry(segment_id: str, text: str, controls: dict, reference_sha: str,
                          seed: int, duration: float, files: dict[str, str]) -> dict:
    return {
        "id": segment_id, "text": text, "actor_id": controls["actor_id"],
        "director_intent": controls["director_intent"], "intensity": controls["intensity"],
        "selected_variant": controls["selected_variant"], "reference_state": controls["reference_state"],
        "reference_sha256": reference_sha, "profile_hash": controls["profile_hash"],
        "calibration_id": controls["calibration_id"], "seed": seed,
        "duration_seconds": round(float(duration), 3), "files": files,
        "generation_fingerprint": segment_fingerprint(text, controls, reference_sha, seed),
        "artificial_pause_ms": 0, "post_tempo": False,
        "qa": {"technical": "passed", "voice": "pending", "c_direction": "pending"},
    }


def _load_article_profile(year: int, article: str) -> dict:
    data = load_json(ROOT / f"content-pipeline/voice_profiles/{year}.json")
    profiles = data.get("profiles", data.get("articles", data))
    if article not in profiles:
        raise KeyError(f"missing Article Voice Profile: {year}/{article}")
    return {"article_id": article, **profiles[article]}


def _load_director_plan(year: int) -> dict:
    return load_json(ROOT / f"content-pipeline/direction/{year}.json")


def _build_plan(year: int, article: str) -> dict:
    content = load_json(ROOT / f"kaoyan-reader-v1/content/{year}/c/{article}.json")
    profile = _load_article_profile(year, article)
    director = _load_director_plan(year)
    calibration = ROOT / "voice-pipeline/calibration/actors"
    return build_voice_plan(content, profile, director, calibration)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--article", required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.year != 2002 or args.article not in ARTICLES_2002:
        raise ValueError("first production scope is the six 2002 units")

    import numpy as np
    import torch
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS

    torch.set_num_threads(int(os.environ.get("TTS_THREADS", "4")))
    plan = _build_plan(args.year, args.article)
    sentences = select_sentence_shard(plan["sentences"], args.shards, args.shard)
    output = Path(args.output) if args.output else ROOT / f"kaoyan-reader-v1/audio/{args.year}/v4/c-{args.article}"
    output.mkdir(parents=True, exist_ok=True)
    ref_dir = ROOT / "voice-pipeline/references/2002-cast"
    model = ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
    manifest = {
        "year": args.year, "article": args.article, "shard": args.shard, "shards": args.shards,
        "model": MODEL, "render_version": RENDER_VERSION, "segments": {}, "failures": [],
        "qa": {"technical": "candidate", "voice": "pending", "c_direction": "pending"},
    }
    started = time.monotonic()

    for sentence in sentences:
        for segment in sentence["segments"]:
            sid = segment["id"]
            controls = segment["controls"]
            reference = ref_dir / controls["reference_path"]
            if not reference.is_file():
                raise FileNotFoundError(f"missing actor reference: {reference}")
            reference_sha = sha(reference)
            seed = deterministic_seed(args.year, args.article, sentence["id"], sid)
            try:
                random.seed(seed); np.random.seed(seed % (2**32)); torch.manual_seed(seed)
                with torch.inference_mode():
                    wav = model.generate(
                        spoken_text(segment["text"]), audio_prompt_path=str(reference),
                        exaggeration=controls["exaggeration"], cfg_weight=controls["cfg_weight"],
                        temperature=controls["temperature"], repetition_penalty=controls["repetition_penalty"],
                    )
                samples = wav.detach().float().cpu().numpy().reshape(-1)
                if not np.isfinite(samples).all() or not len(samples):
                    raise ValueError("invalid waveform")
                audible = np.flatnonzero(np.abs(samples) > .008)
                if not len(audible):
                    raise ValueError("silent waveform")
                left = max(0, int(audible[0]) - int(.020 * model.sr))
                right = min(len(samples), int(audible[-1]) + int(.035 * model.sr))
                wav = wav[:, left:right]
                duration = (right-left) / model.sr
                words = len(re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?", spoken_text(segment["text"])))
                wpm = words * 60 / duration if duration else 0
                if words >= 8 and not 70 <= wpm <= 320:
                    raise ValueError(f"suspected truncation/repetition: {wpm:.1f} words/minute")
                raw = output / f"v4-{sid}.wav"
                ta.save(str(raw), wav, model.sr)
                files = {}
                for ext, codec, bitrate in (("opus", "libopus", "64k"), ("mp3", "libmp3lame", "112k")):
                    target = output / f"v4-{sid}.{ext}"
                    subprocess.run([
                        "ffmpeg", "-v", "error", "-y", "-i", str(raw),
                        "-af", "loudnorm=I=-19:TP=-2:LRA=11", "-ar", "48000", "-ac", "1",
                        "-c:a", codec, "-b:a", bitrate, str(target)
                    ], check=True)
                    files[target.name] = sha(target)
                raw.unlink()
                actual = float(subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1", str(output / f"v4-{sid}.opus")
                ]))
                manifest["segments"][sid] = build_candidate_entry(
                    sid, segment["text"], controls, reference_sha, seed, actual, files
                )
            except Exception as exc:
                manifest["failures"].append({"id": sid, "error": str(exc)})
            save_json(output / f"v4-shard-{args.shard}.json", manifest)

    manifest["elapsed_seconds"] = round(time.monotonic() - started, 2)
    manifest["qa"]["technical"] = "passed" if not manifest["failures"] else "failed"
    save_json(output / f"v4-shard-{args.shard}.json", manifest)
    print(json.dumps({"segments": len(manifest["segments"]), "failures": len(manifest["failures"])}, indent=2))
    if manifest["failures"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
