"""Deterministic, fail-closed C v4 actor calibration and approval.

The audio measurements are produced by the render/alignment jobs.  This module
only applies versioned policy and therefore never turns missing evidence into a
pass.  Thresholds inherited from the B2 voice design are kept in one auditable
policy object; the internal-silence and model-scored listening replacements are
the explicitly versioned additions for automated C v4 approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from qa import normalized_wer

REQUIRED_INTENTS = (
    "neutral_explain", "serious_analysis", "warm_explain", "narrative_build",
    "contrast", "information_peak", "restrained_irony", "quoted_character",
    "qualification", "curious_probe",
)
POLICY = {
    "id": "automated-c-v4-qa-1",
    "max_wer": 0.08,
    "min_wpm": 105.0,
    "max_wpm": 190.0,
    "max_clipping_ratio": 0.001,
    "max_edge_silence_seconds": 0.60,
    "max_internal_silence_seconds": 1.20,
    "min_speaker_similarity": 0.65,
    "min_naturalness_score": 0.75,
    "min_intent_fidelity_score": 0.75,
}


def evaluate_candidate(item: dict) -> list[str]:
    errors: list[str] = []
    required = (
        "actor_id", "reference_actor_id", "reference_sha256", "audio_sha256",
        "generation_fingerprint", "expected_fingerprint", "transcript",
        "aligned_transcript", "duration_seconds", "wpm", "clipping_ratio",
        "leading_silence_seconds", "trailing_silence_seconds",
        "max_internal_silence_seconds", "alignment_status", "words",
        "speaker_similarity", "naturalness_score", "intent_fidelity_score",
        "artificial_pause_ms", "post_tempo", "controls", "variant",
    )
    for field in required:
        if field not in item:
            errors.append(f"missing evidence: {field}")
    if errors:
        return errors
    if item["actor_id"] != item["reference_actor_id"]:
        errors.append("reference voice actor identity mismatch")
    if normalized_wer(item["transcript"], item["aligned_transcript"]) > POLICY["max_wer"]:
        errors.append("transcript WER exceeds 0.08")
    if item["alignment_status"] != "passed" or not item["words"]:
        errors.append("transcript alignment not passed")
    previous = 0.0
    duration = float(item["duration_seconds"])
    for index, word in enumerate(item["words"]):
        start, end = float(word["start"]), float(word["end"])
        if start < previous or end < start or end > duration + 0.08:
            errors.append(f"word {index}: timestamps are not monotonic/in bounds")
            break
        previous = end
    if not POLICY["min_wpm"] <= float(item["wpm"]) <= POLICY["max_wpm"]:
        errors.append("pace outside 105-190 WPM")
    if float(item["clipping_ratio"]) > POLICY["max_clipping_ratio"]:
        errors.append("clipping exceeds 0.1 percent")
    if max(float(item["leading_silence_seconds"]), float(item["trailing_silence_seconds"])) > POLICY["max_edge_silence_seconds"]:
        errors.append("edge silence exceeds 0.60 seconds")
    if float(item["max_internal_silence_seconds"]) > POLICY["max_internal_silence_seconds"]:
        errors.append("internal silence exceeds 1.20 seconds")
    if float(item["speaker_similarity"]) < POLICY["min_speaker_similarity"]:
        errors.append("speaker identity similarity below 0.65")
    if float(item["naturalness_score"]) < POLICY["min_naturalness_score"]:
        errors.append("automated naturalness score below 0.75")
    if float(item["intent_fidelity_score"]) < POLICY["min_intent_fidelity_score"]:
        errors.append("automated director-intent score below 0.75")
    if item["artificial_pause_ms"] != 0:
        errors.append("artificial pause must be zero")
    if item["post_tempo"] is not False:
        errors.append("post tempo must be false")
    if item["generation_fingerprint"] != item["expected_fingerprint"]:
        errors.append("generation fingerprint mismatch")
    return errors


def _rank(item: dict) -> tuple:
    # Quality dominates; stable variant order B, A, C is the final tie-break.
    quality = (float(item["naturalness_score"]) + float(item["intent_fidelity_score"]) + float(item["speaker_similarity"])) / 3
    return (-quality, abs(float(item["wpm"]) - 147.5), {"B": 0, "A": 1, "C": 2}.get(item["variant"], 9))


def select_actor_calibration(actor_id: str, candidates_by_intent: dict) -> tuple[dict, dict]:
    selected, rejected = {}, {}
    for intent in REQUIRED_INTENTS:
        candidates = candidates_by_intent.get(intent, [])
        passing = [item for item in candidates if not evaluate_candidate(item)]
        if not passing:
            rejected[intent] = {item.get("variant", "unknown"): evaluate_candidate(item) for item in candidates} or {"all": ["no candidates"]}
        else:
            selected[intent] = min(passing, key=_rank)
    return ({}, rejected) if rejected else (selected, {})


def validate_production_approvals(data: dict) -> list[str]:
    errors = []
    for actor_id, approval in data.get("actors", {}).items():
        if approval.get("status") == "accepted" and approval.get("approval_method") not in {"human_listening", "automated_c_v4_qa"}:
            errors.append(f"{actor_id}: accepted approval_method must identify human_listening or automated_c_v4_qa")
        if approval.get("approval_method") == "automated_c_v4_qa" and approval.get("qa_policy") != POLICY["id"]:
            errors.append(f"{actor_id}: automated approval must name qa_policy {POLICY['id']}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    selected, rejected = select_actor_calibration(args.actor, data.get("candidates", {}))
    result = {"actor_id": args.actor, "qa_policy": POLICY["id"], "status": "accepted" if selected else "failed", "selected": selected, "failures": rejected}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if rejected:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
