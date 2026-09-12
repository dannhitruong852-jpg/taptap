"""Merge C v4 semantic/role chunks into one final sentence asset."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from generate_2002 import sha

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_2002 = ("cloze", "text1", "text2", "text3", "text4", "translation")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ]))


def merge_status(articles: dict[str, dict]) -> str:
    required = set(ARTICLES_2002)
    if set(articles) != required:
        return "partial_candidate"
    if any(v.get("missing") or not v.get("sentences") for v in articles.values()):
        return "partial_candidate"
    return "complete_candidate"


def _collect_segments(incoming: Path, article: str) -> dict[str, dict]:
    found = {}
    for path in incoming.rglob("v4-shard-*.json"):
        data = load_json(path)
        if data.get("article") != article:
            continue
        for sid, entry in data.get("segments", {}).items():
            opus = path.parent / f"v4-{sid}.opus"
            mp3 = path.parent / f"v4-{sid}.mp3"
            if not opus.is_file() or not mp3.is_file():
                continue
            files = entry.get("files", {})
            if files.get(opus.name) != sha(opus) or files.get(mp3.name) != sha(mp3):
                continue
            found[sid] = {**entry, "_opus": opus, "_mp3": mp3}
    return found


def _merge_sentence(year: int, article: str, sentence: dict, entries: list[dict], target: Path) -> dict:
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        listing = tmp / "concat.txt"
        listing.write_text("".join(f"file '{entry['_opus'].resolve().as_posix()}'\n" for entry in entries), encoding="utf-8")
        wav = tmp / f"{sentence['id']}.wav"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)
        ], check=True)
        outputs = {}
        for ext, codec, bitrate in (("opus", "libopus", "64k"), ("mp3", "libmp3lame", "112k")):
            out = target / f"v4-{sentence['id']}.{ext}"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ar", "48000", "-ac", "1",
                "-c:a", codec, "-b:a", bitrate, str(out)
            ], check=True)
            outputs[ext] = out
    duration = probe(outputs["opus"])
    source_segments = sentence.get("segments", [])
    return {
        "id": sentence["id"],
        "path": f"./audio/{year}/v4/c-{article}/v4-{sentence['id']}.opus",
        "mp3_path": f"./audio/{year}/v4/c-{article}/v4-{sentence['id']}.mp3",
        "duration_seconds": round(duration, 3),
        "files": {p.name: sha(p) for p in outputs.values()},
        "actor_sequence": [s.get("actor_id") for s in source_segments],
        "segment_fingerprints": [e.get("generation_fingerprint") for e in entries],
        "generation_fingerprint": sha(outputs["opus"]),
        "artificial_pause_ms": 0,
        "post_tempo": False,
        "qa": {"technical": "passed", "voice": "pending", "c_direction": "pending"},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--incoming", required=True)
    parser.add_argument("--root", default=str(ROOT / "kaoyan-reader-v1"))
    args = parser.parse_args()
    if args.year != 2002:
        raise ValueError("first production scope is 2002")
    incoming = Path(args.incoming)
    reader_root = Path(args.root)
    summary = {"year": args.year, "articles": {}, "qa": {"technical": "candidate", "voice": "pending", "c_direction": "pending"}}

    for article in ARTICLES_2002:
        content = load_json(reader_root / f"content/{args.year}/c/{article}.json")
        found = _collect_segments(incoming, article)
        expected = [seg["id"] for sent in content.get("sentences", []) for seg in sent.get("segments", [])]
        missing = [sid for sid in expected if sid not in found]
        target = reader_root / f"audio/{args.year}/v4/c-{article}"
        manifest = {
            "year": args.year, "article": article, "c_mode_version": "v4",
            "sentences": {}, "missing_segments": missing,
            "qa": {"technical": "passed" if not missing else "failed", "voice": "pending", "c_direction": "pending"},
        }
        if not missing:
            for sentence in content.get("sentences", []):
                entries = [found[seg["id"]] for seg in sentence.get("segments", [])]
                manifest["sentences"][sentence["id"]] = _merge_sentence(args.year, article, sentence, entries, target)
        save_json(target / "manifest.json", manifest)
        summary["articles"][article] = {"missing": missing, "sentences": len(manifest["sentences"])}

    summary["status"] = merge_status(summary["articles"])
    summary["qa"]["technical"] = "passed" if summary["status"] == "complete_candidate" else "failed"
    save_json(reader_root / f"reports/c-v4-{args.year}-merge.json", summary)
    print(json.dumps(summary, indent=2))
    if summary["status"] != "complete_candidate":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
