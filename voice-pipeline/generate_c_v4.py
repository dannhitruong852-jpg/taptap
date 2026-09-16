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

from build_c_v4_voice_plan import build_voice_plan
from generate_2002 import sha, spoken_text
from generate_batch import resolve_render_paths, run_batch, select_shard
from render import generation_fingerprint

ROOT = Path(__file__).resolve().parents[1]
MODEL = "chatterbox-tts-0.1.7-original-english"
RENDER_VERSION = "c-v4-actor-adapter-batch"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def deterministic_seed(year: int, article: str, sentence_id: str, segment_id: str) -> int:
    payload = f"c-v4:{year}:{article}:{sentence_id}:{segment_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def segment_fingerprint(text: str, controls: dict, reference_sha: str, seed: int) -> str:
    return generation_fingerprint(
        text=spoken_text(text), actor=controls["actor_id"], director_intent=controls["director_intent"],
        intensity=controls["intensity"], reference_sha=reference_sha, seed=seed,
        exaggeration=controls["exaggeration"], cfg_weight=controls["cfg_weight"],
        temperature=controls["temperature"], repetition_penalty=controls["repetition_penalty"],
        profile_hash=controls["profile_hash"], calibration_id=controls["calibration_id"],
        model=MODEL, render_version=RENDER_VERSION, artificial_pause_ms=0, post_tempo=False,
    )


def _load_article_profile(path: Path, article: str) -> dict:
    data = load_json(path)
    profiles = data.get("profiles", data.get("articles", data))
    if article not in profiles:
        raise KeyError(f"missing Article Voice Profile: {article}")
    return {"article_id": article, **profiles[article]}


def _build_plan(year: int, article: str, paths: dict[str, Path]) -> dict:
    content = load_json(paths["content"])
    profile = _load_article_profile(paths["voice_profiles"], article)
    director = load_json(paths["direction"])
    return build_voice_plan(content, profile, director, paths["calibration_dir"])


def _flatten_plan(plan: dict) -> list[dict]:
    items = []
    for sentence in plan.get("sentences", []):
        for segment in sentence.get("segments", []):
            items.append({**segment, "sentence_id": sentence["id"]})
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--article", required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=3)
    parser.add_argument("--output")
    parser.add_argument("--calibration-dir")
    parser.add_argument("--references-dir")
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()

    paths = resolve_render_paths(
        ROOT,
        args.year,
        args.article,
        output=Path(args.output) if args.output else None,
        calibration_dir=Path(args.calibration_dir) if args.calibration_dir else None,
        reference_dir=Path(args.references_dir) if args.references_dir else None,
    )

    import numpy as np
    import torch
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS

    torch.set_num_threads(int(os.environ.get("TTS_THREADS", "4")))
    plan = _build_plan(args.year, args.article, paths)
    all_items = _flatten_plan(plan)
    items = select_shard(all_items, args.shard, args.shards)
    output = paths["output"]
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / f"v4-shard-{args.shard}.json"
    old_manifest = load_json(manifest_path) if manifest_path.is_file() else {"items": {}}
    model = ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
    started = time.monotonic()

    def render_one(item: dict, attempt: int, directory: Path) -> dict:
        sid = item["id"]
        controls = item["controls"]
        reference = paths["reference_dir"] / controls["reference_path"]
        if not reference.is_file():
            raise FileNotFoundError(f"missing actor reference: {reference}")
        reference_sha = sha(reference)
        base_seed = deterministic_seed(args.year, args.article, item["sentence_id"], sid)
        seed = base_seed + attempt - 1
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        with torch.inference_mode():
            wav = model.generate(
                spoken_text(item["text"]), audio_prompt_path=str(reference),
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
        duration = (right - left) / model.sr
        words = len(re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?", spoken_text(item["text"])))
        wpm = words * 60 / duration if duration else 0
        if words >= 8 and not 70 <= wpm <= 320:
            raise ValueError(f"suspected truncation/repetition: {wpm:.1f} words/minute")
        clipped = float(np.mean(np.abs(samples) >= .999))
        if clipped > .015:
            raise ValueError(f"excessive clipping: {clipped:.4f}")

        raw = directory / f"v4-{sid}.wav"
        ta.save(str(raw), wav, model.sr)
        files = {}
        for ext, codec, bitrate in (("opus", "libopus", "64k"), ("mp3", "libmp3lame", "112k")):
            target = directory / f"v4-{sid}.{ext}"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(raw),
                "-af", "loudnorm=I=-19:TP=-2:LRA=11", "-ar", "48000", "-ac", "1",
                "-c:a", codec, "-b:a", bitrate, str(target)
            ], check=True)
            files[target.name] = sha(target)
        raw.unlink()
        actual = float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(directory / f"v4-{sid}.opus")
        ]))
        return {
            "text": item["text"],
            "sentence_id": item["sentence_id"],
            "actor_id": controls["actor_id"],
            "director_intent": controls["director_intent"],
            "intensity": controls["intensity"],
            "selected_variant": controls["selected_variant"],
            "reference_state": controls["reference_state"],
            "reference_sha256": reference_sha,
            "profile_hash": controls["profile_hash"],
            "calibration_id": controls["calibration_id"],
            "seed": seed,
            "duration_seconds": round(actual, 3),
            "raw_wpm": round(wpm, 1),
            "clipped_fraction": clipped,
            "files": files,
            "generation_fingerprint": segment_fingerprint(item["text"], controls, reference_sha, seed),
            "artificial_pause_ms": 0,
            "post_tempo": False,
            "qa": {"technical": "passed", "voice": "pending", "c_direction": "pending"},
        }

    batch = run_batch(
        items,
        output,
        old_manifest,
        render_one=render_one,
        max_attempts=args.max_attempts,
    )
    manifest = {
        "year": args.year,
        "article": args.article,
        "shard": args.shard,
        "shards": args.shards,
        "model": MODEL,
        "render_version": RENDER_VERSION,
        "primary_actor_id": plan.get("primary_actor_id"),
        "items": batch["items"],
        "failures": batch["failures"],
        "cache_hits": batch["cache_hits"],
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "qa": {
            "technical": "passed" if not batch["failures"] else "partial",
            "voice": "pending",
            "c_direction": "pending",
        },
    }
    save_json(manifest_path, manifest)
    print(json.dumps({
        "year": args.year,
        "article": args.article,
        "generated": sum(1 for x in batch["items"].values() if x.get("status") == "ok"),
        "failed": len(batch["failures"]),
        "cache_hits": batch["cache_hits"],
        "seconds": manifest["elapsed_seconds"],
    }))


if __name__ == "__main__":
    main()
