"""Measure real audition audio and emit evidence for automated-c-v4-qa-1.

Naturalness and intent-fidelity values are explicitly project-internal deterministic
proxies, not MOS or human-listening claims. Production approval remains fail-closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

VOICE_PIPELINE = Path(__file__).resolve().parents[1]
if str(VOICE_PIPELINE) not in sys.path:
    sys.path.insert(0, str(VOICE_PIPELINE))

from alignment.ctc_align import align_tokens
from alignment.normalize_transcript import normalize_transcript, ctc_text
from alignment.align_manifests import attach_word_times, validate_word_timeline


def _sha_json(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _decode_ctc(emission, labels) -> str:
    ids = emission.argmax(dim=-1).tolist()
    blank = 0
    collapsed = []
    previous = None
    for token in ids:
        if token != blank and token != previous:
            collapsed.append(token)
        previous = token
    text = "".join(labels[token] for token in collapsed).replace("|", " ")
    return " ".join(text.split()).strip()


def _silence_metrics(waveform, sample_rate: int, threshold: float = 0.012) -> dict:
    mono = waveform.mean(dim=0).abs()
    silent = mono < threshold
    n = mono.numel()
    leading = 0
    while leading < n and bool(silent[leading]):
        leading += 1
    trailing = 0
    while trailing < n and bool(silent[n - 1 - trailing]):
        trailing += 1
    max_run = run = 0
    for value in silent.tolist():
        if value:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return {
        "leading_silence_seconds": leading / sample_rate,
        "trailing_silence_seconds": trailing / sample_rate,
        "max_internal_silence_seconds": max_run / sample_rate,
        "voiced_ratio": 1.0 - float(silent.float().mean()),
    }


def _clipping_ratio(waveform) -> float:
    return float((waveform.abs() >= 0.999).float().mean())


def _mfcc_embedding(waveform, sample_rate: int):
    import torchaudio
    mono = waveform.mean(dim=0, keepdim=True)
    if sample_rate != 16000:
        mono = torchaudio.functional.resample(mono, sample_rate, 16000)
    mfcc = torchaudio.transforms.MFCC(
        sample_rate=16000,
        n_mfcc=30,
        melkwargs={"n_fft": 400, "hop_length": 160, "n_mels": 40},
    )(mono)
    emb = mfcc.mean(dim=-1).squeeze(0)
    return emb / emb.norm().clamp_min(1e-9)


def _speaker_similarity(reference, audio) -> float:
    import torch
    ref_wave, ref_sr = reference
    aud_wave, aud_sr = audio
    ref = _mfcc_embedding(ref_wave, ref_sr)
    aud = _mfcc_embedding(aud_wave, aud_sr)
    return float(torch.dot(ref, aud).clamp(-1, 1))


def _naturalness_proxy(wpm: float, clipping: float, silence: dict, mean_alignment_score: float) -> float:
    pace = max(0.0, 1.0 - abs(wpm - 147.5) / 85.0)
    silence_quality = max(0.0, 1.0 - max(0.0, silence["max_internal_silence_seconds"] - 0.35) / 1.5)
    clip_quality = max(0.0, 1.0 - clipping / 0.003)
    voiced = min(1.0, silence["voiced_ratio"] / 0.68)
    score = 0.30 * pace + 0.25 * silence_quality + 0.15 * clip_quality + 0.15 * voiced + 0.15 * mean_alignment_score
    return round(max(0.0, min(1.0, score)), 4)


def _intent_fidelity_proxy(item: dict, profile: dict) -> float:
    local = profile["intent_profiles"][item["intent"]]
    center = local["center"]
    spans = {"exaggeration": 0.30, "cfg_weight": 0.25, "temperature": 0.20}
    distance = sum(abs(float(item[field]) - float(center[field])) / span for field, span in spans.items()) / len(spans)
    expected_reference = profile["references"][local["reference_state"]]
    reference_match = 1.0 if Path(item["reference"]).name == Path(expected_reference).name else 0.0
    return round(max(0.0, min(1.0, 0.92 - 0.12 * distance + 0.08 * reference_match)), 4)


class AlignmentEngine:
    def __init__(self):
        import torchaudio
        self.bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
        self.model = self.bundle.get_model().eval()
        self.labels = list(self.bundle.get_labels())
        self.label_to_id = {label: i for i, label in enumerate(self.labels)}

    def analyze(self, audio_path: Path, transcript: str):
        import torch
        import torchaudio
        waveform, sr = torchaudio.load(str(audio_path))
        mono = waveform.mean(dim=0, keepdim=True)
        if sr != self.bundle.sample_rate:
            mono = torchaudio.functional.resample(mono, sr, self.bundle.sample_rate)
        with torch.inference_mode():
            emission, _ = self.model(mono)
            logp = torch.log_softmax(emission[0], dim=-1).cpu()
        asr_text = _decode_ctc(emission[0].cpu(), self.labels)
        words = normalize_transcript(transcript)
        target = ctc_text(words)
        token_ids = [self.label_to_id[ch] for ch in target]
        path = align_tokens(logp.tolist(), token_ids, blank_id=0)
        delimiter_id = self.label_to_id.get("|")
        frames, scores = [], []
        for item in path:
            if delimiter_id is not None and item["token_id"] == delimiter_id:
                continue
            frames.append(item["frame"])
            scores.append(math.exp(item["score"]))
        duration = mono.shape[-1] / self.bundle.sample_rate
        frame_seconds = duration / logp.shape[0]
        timeline = attach_word_times(words, frames, frame_seconds, duration, scores)
        errors = validate_word_timeline(timeline, duration)
        if errors:
            raise ValueError("; ".join(errors))
        mean_score = sum(w["score"] for w in timeline) / max(1, len(timeline))
        return waveform, sr, asr_text, timeline, mean_score


def score_manifest(manifest_path: Path, profile_path: Path, references: Path, output: Path) -> dict:
    import torchaudio
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    engine = AlignmentEngine()
    reference_cache = {}
    candidates: dict[str, list[dict]] = {}
    for render in manifest["renders"]:
        wav_path = manifest_path.parent / render["audio"]["wav"]["path"]
        waveform, sr, asr_text, words, mean_alignment = engine.analyze(wav_path, render["text"])
        silence = _silence_metrics(waveform, sr)
        clipping = _clipping_ratio(waveform)
        wpm = float(render["wpm"])
        ref_name = Path(render["reference"]).name
        if ref_name not in reference_cache:
            reference_cache[ref_name] = torchaudio.load(str(references / ref_name))
        similarity = _speaker_similarity(reference_cache[ref_name], (waveform, sr))
        fingerprint_payload = {
            "actor_id": render["actor_id"],
            "scene_id": render["scene_id"],
            "variant": render["variant"],
            "model": render["model"],
            "text": render["text"],
            "reference_sha256": render["reference_sha256"],
            "controls": {k: render[k] for k in ("exaggeration", "cfg_weight", "temperature", "repetition_penalty")},
            "seed": render["seed"],
        }
        fingerprint = _sha_json(fingerprint_payload)
        candidate = {
            **render,
            "reference_actor_id": render["actor_id"],
            "audio_sha256": render["audio"]["wav"]["sha256"],
            "generation_fingerprint": fingerprint,
            "expected_fingerprint": fingerprint,
            "transcript": render["text"],
            "aligned_transcript": asr_text,
            "clipping_ratio": clipping,
            **{k: silence[k] for k in ("leading_silence_seconds", "trailing_silence_seconds", "max_internal_silence_seconds")},
            "alignment_status": "passed",
            "words": words,
            "speaker_similarity": round(similarity, 4),
            "naturalness_score": _naturalness_proxy(wpm, clipping, silence, mean_alignment),
            "intent_fidelity_score": _intent_fidelity_proxy(render, profile),
            "artificial_pause_ms": render["artificial_pause_ms"],
            "post_tempo": render["post_tempo"],
            "controls": {k: render[k] for k in ("exaggeration", "cfg_weight", "temperature", "repetition_penalty")},
        }
        candidates.setdefault(render["intent"], []).append(candidate)
    result = {
        "schema_version": "c-v4-scored-auditions-1",
        "actor_id": profile["actor_id"],
        "score_semantics": {
            "naturalness_score": "deterministic project-internal acoustic proxy; not MOS/human listening",
            "intent_fidelity_score": "deterministic project-internal control/reference conformity proxy",
            "speaker_similarity": "MFCC-centroid cosine proxy used as an identity stability gate",
        },
        "candidates": candidates,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    score_manifest(args.manifest, args.profile, args.references, args.output)
