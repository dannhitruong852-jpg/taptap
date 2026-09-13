"""Prepare traceable same-speaker references for C v4 actor expansion."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "voice-pipeline/config/actor_sources.json"
EARS_RAW = "https://raw.githubusercontent.com/facebookresearch/ears_dataset/main/"
EARS_RELEASE = "https://github.com/facebookresearch/ears_dataset/releases/download/dataset/"
VCTK_P225_SAMPLE = "https://huggingface.co/voices/VCTK_British_English_Females/resolve/main/samples/VCTK_p225.wav"
STATES = ("neutral", "warm", "lively", "serious", "curious", "ironic", "tense", "emotional")
EARS_TASKS = {
    "neutral": "rainbow_01_regular",
    "warm": "emo_contentment_sentences",
    "lively": "emo_realization_sentences",
    "serious": "rainbow_02_regular",
    "curious": "emo_interest_sentences",
    "ironic": "emo_amusement_sentences",
    "tense": "emo_distress_sentences",
    "emotional": "emo_sadness_sentences",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, target: Path, attempts: int = 5) -> None:
    """Download with bounded retry for transient release/CDN resets."""
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kaoyan-c-v4-reference-builder/2.1"})
            with urllib.request.urlopen(req, timeout=180) as response, target.open("wb") as sink:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    sink.write(chunk)
            if target.stat().st_size <= 0:
                raise OSError("download produced an empty file")
            return
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionResetError, TimeoutError, OSError) as exc:
            last_error = exc
            target.unlink(missing_ok=True)
            if attempt == attempts:
                break
            time.sleep(min(12, 2 ** (attempt - 1)))
    raise RuntimeError(f"download failed after {attempts} attempts: {url}: {last_error}") from last_error


def _find_ears_member(names: list[str], speaker: str, stem: str) -> str:
    hits = []
    for name in names:
        p = Path(name)
        if p.suffix.lower() == ".wav" and p.stem == stem and (speaker in p.parts or f"/{speaker}/" in name or name.startswith(speaker + "/")):
            hits.append(name)
    if len(hits) != 1:
        raise ValueError(f"Expected one EARS member for {speaker}/{stem}, got {hits}")
    return hits[0]


def _write_reference(raw: bytes, output: Path) -> dict:
    import numpy as np
    import soundfile as sf

    wave, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
    mono = wave.mean(axis=1)
    if not np.isfinite(mono).all():
        raise ValueError("non-finite reference samples")
    voiced = np.flatnonzero(np.abs(mono) > 0.006)
    if not len(voiced):
        raise ValueError("silent reference")
    start = max(0, int(voiced[0]) - int(0.025 * sr))
    end = min(len(mono), int(voiced[-1]) + int(0.04 * sr), start + int(12 * sr))
    clip = mono[start:end]
    if len(clip) / sr < 2.0:
        raise ValueError("reference too short")
    peak = float(np.max(np.abs(clip)))
    clipping = float(np.mean(np.abs(clip) >= 0.999))
    if clipping > 0.01:
        raise ValueError("reference clipped")
    clip = clip * (0.86 / max(peak, 0.001))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        tmp = Path(handle.name)
    try:
        sf.write(tmp, clip, sr, subtype="PCM_16")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(output)], check=True)
    finally:
        tmp.unlink(missing_ok=True)
    return {"sha256": sha256_file(output), "duration_seconds": round(len(clip) / sr, 3)}


def _prepare_ears(actor_id: str, cfg: dict, output: Path) -> dict:
    speaker = cfg["source_speaker"]
    with tempfile.TemporaryDirectory() as td_raw:
        td = Path(td_raw)
        stats_path, license_path, archive = td / "speaker_statistics.json", td / "LICENSE", td / f"{speaker}.zip"
        fetch(EARS_RAW + "speaker_statistics.json", stats_path)
        fetch(EARS_RAW + "LICENSE", license_path)
        stats = json.loads(stats_path.read_text(encoding="utf-8"))[speaker]
        expected = {"gender": cfg["gender"], "age": cfg["age_group"], "native language": cfg["native_language"]}
        for key, value in expected.items():
            if stats.get(key) != value:
                raise ValueError(f"{speaker} metadata mismatch: {key}={stats.get(key)!r}, expected {value!r}")
        fetch(EARS_RELEASE + f"{speaker}.zip", archive)
        report = {"actor_id": actor_id, "speaker": speaker, "corpus": "EARS", "license": cfg["source_license"], "archive_sha256": sha256_file(archive), "variants": {}}
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            for state, task in EARS_TASKS.items():
                member = _find_ears_member(names, speaker, task)
                raw = z.read(member)
                target = output / f"actor{actor_id}-{state}.wav"
                metrics = _write_reference(raw, target)
                report["variants"][state] = {"path": target.name, "task": task, "source_member": member, "source_sha256": sha256_bytes(raw), **metrics}
        (output / "LICENSE.EARS.txt").write_text(license_path.read_text(encoding="utf-8"), encoding="utf-8")
        return report


def _prepare_vctk(actor_id: str, cfg: dict, output: Path) -> dict:
    if cfg["source_speaker"] != "p225":
        raise ValueError("Only traceable VCTK p225 is configured for this expansion")
    with tempfile.TemporaryDirectory() as td_raw:
        source = Path(td_raw) / "VCTK_p225.wav"
        fetch(VCTK_P225_SAMPLE, source)
        raw = source.read_bytes()
        report = {
            "actor_id": actor_id,
            "speaker": "p225",
            "corpus": "VCTK",
            "license": cfg["source_license"],
            "source_url": cfg["source_url"],
            "mirror_url": VCTK_P225_SAMPLE,
            "mirror_repository_license": "CC BY 4.0",
            "source_sha256": sha256_bytes(raw),
            "variants": {},
        }
        for state in STATES:
            target = output / f"actor{actor_id}-{state}.wav"
            metrics = _write_reference(raw, target)
            report["variants"][state] = {"path": target.name, "task": "VCTK_p225", **metrics}
        (output / "NOTICE.VCTK.txt").write_text(
            "CSTR VCTK Corpus v0.92, University of Edinburgh, CC BY 4.0.\n"
            "Configured speaker: p225, female, English accent, Southern England.\n"
            "The CI reference is the VCTK_p225 sample mirrored by voices/VCTK_British_English_Females on Hugging Face under CC BY 4.0.\n"
            "Official VCTK provenance remains the University of Edinburgh DataShare source recorded in actor_sources.json.\n",
            encoding="utf-8",
        )
        return report


def prepare(actor_id: str, output: Path) -> dict:
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["actors"]
    cfg = sources[actor_id]
    output.mkdir(parents=True, exist_ok=True)
    report = _prepare_ears(actor_id, cfg, output) if cfg["source_corpus"] == "EARS" else _prepare_vctk(actor_id, cfg, output)
    report["source_mapping"] = cfg
    (output / f"actor{actor_id}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.actor, args.output)
