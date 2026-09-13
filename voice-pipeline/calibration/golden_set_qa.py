"""Golden-Set-calibrated automated acceptance policy for C v4 voices.

QA2 preserves absolute integrity gates, but calibrates quality-shape metrics
against the historical human-approved Golden Set instead of treating QA1's
provisional fixed numbers as universal truth. Actor 05 remains the benchmark
anchor for reporting; new actors are not required to imitate its voice identity.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable

from calibration.automatic_qa import REQUIRED_INTENTS, evaluate_candidate
from qa import normalized_wer

POLICY_ID = "automated-c-v4-qa-2"
GOLDEN_ACTORS = ("01", "02", "04", "05", "08", "09", "12", "13")
BENCHMARK_ANCHOR = "05"

# The historical audition board was rendered before curious_probe replaced the
# second serious-analysis scene. Preserve that provenance explicitly instead of
# pretending the old scene was human-reviewed as curious_probe.
_HISTORICAL_SCENES = {
    "neutral_explain": ("neutral_explain", "01-explanation", "direct"),
    "serious_analysis": ("serious_analysis", "02-analysis", "direct"),
    "warm_explain": ("warm_explain", "03-warm", "direct"),
    "narrative_build": ("narrative_build", "04-story", "direct"),
    "contrast": ("contrast", "05-turn", "direct"),
    "information_peak": ("information_peak", "06-emphasis", "direct"),
    "restrained_irony": ("restrained_irony", "07-humor", "direct"),
    "curious_probe": ("serious_analysis", "08-commentary", "legacy_scene_proxy"),
    "quoted_character": ("quoted_character", "09-quotation", "direct"),
    "qualification": ("qualification", "10-long-sentence", "direct"),
}

# These are true integrity failures rather than style/quality-shape judgments.
# WER, pace and internal silence are intentionally calibrated below because the
# already-human-approved Golden Set proves QA1's provisional values were not
# valid universal cutoffs for this project.
_CALIBRATED_QA1_ERRORS = {
    "transcript WER exceeds 0.08",
    "pace outside 105-190 WPM",
    "internal silence exceeds 1.20 seconds",
    "speaker identity similarity below 0.65",
    "automated naturalness score below 0.75",
    "automated director-intent score below 0.75",
}


def _absolute_gate_errors(item: dict) -> list[str]:
    """Reuse QA1 integrity checks while removing Golden-Set-calibrated dimensions."""
    return [error for error in evaluate_candidate(item) if error not in _CALIBRATED_QA1_ERRORS]


def _find_selected_candidate(
    actor_id: str,
    target_intent: str,
    candidates: Iterable[dict],
    variant: str,
    scene_id: str,
) -> dict:
    matches = [
        item for item in candidates
        if item.get("variant") == variant and item.get("scene_id") == scene_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"golden actor {actor_id} intent {target_intent}: expected one human-approved "
            f"{variant} candidate for {scene_id}, got {len(matches)}"
        )
    candidate = matches[0]
    errors = _absolute_gate_errors(candidate)
    if errors:
        raise ValueError(
            f"golden actor {actor_id} intent {target_intent}: approved candidate fails absolute gate: {errors}"
        )
    return candidate


def build_golden_calibration(scored_by_actor: dict, production_approvals: dict) -> dict:
    approvals = production_approvals.get("actors", {})
    selected: dict[str, dict[str, dict]] = {}
    for actor_id in GOLDEN_ACTORS:
        approval = approvals.get(actor_id)
        if not approval or approval.get("status") != "accepted" or approval.get("approval_method") != "human_listening":
            raise ValueError(f"golden actor {actor_id}: missing historical human approval")
        actor = scored_by_actor.get(actor_id)
        if not actor:
            raise ValueError(f"golden actor {actor_id}: missing scored evidence")
        variant = approval.get("default_variant", "B")
        selected[actor_id] = {}
        for target_intent in REQUIRED_INTENTS:
            historical_intent, scene_id, _ = _HISTORICAL_SCENES[target_intent]
            candidates = actor.get("candidates", {}).get(historical_intent, [])
            selected[actor_id][target_intent] = _find_selected_candidate(
                actor_id, target_intent, candidates, variant, scene_id
            )

    intent_floors = {}
    for intent in REQUIRED_INTENTS:
        historical_intent, scene_id, source_kind = _HISTORICAL_SCENES[intent]
        accepted = [selected[actor_id][intent] for actor_id in GOLDEN_ACTORS]
        intent_floors[intent] = {
            "calibration_source": source_kind,
            "source_scene_id": scene_id,
            "historical_intent": historical_intent,
            "pace_min_wpm": min(float(item["wpm"]) for item in accepted),
            "pace_max_wpm": max(float(item["wpm"]) for item in accepted),
            "max_wer": max(normalized_wer(item["transcript"], item["aligned_transcript"]) for item in accepted),
            "max_internal_silence_seconds": max(float(item["max_internal_silence_seconds"]) for item in accepted),
            "naturalness_floor": min(float(item["naturalness_score"]) for item in accepted),
            "intent_fidelity_floor": min(float(item["intent_fidelity_score"]) for item in accepted),
            "speaker_similarity_floor": min(float(item["speaker_similarity"]) for item in accepted),
            "golden_values": {
                actor_id: {
                    "variant": selected[actor_id][intent]["variant"],
                    "wpm": float(selected[actor_id][intent]["wpm"]),
                    "wer": normalized_wer(
                        selected[actor_id][intent]["transcript"],
                        selected[actor_id][intent]["aligned_transcript"],
                    ),
                    "max_internal_silence_seconds": float(selected[actor_id][intent]["max_internal_silence_seconds"]),
                    "naturalness_score": float(selected[actor_id][intent]["naturalness_score"]),
                    "intent_fidelity_score": float(selected[actor_id][intent]["intent_fidelity_score"]),
                    "speaker_similarity": float(selected[actor_id][intent]["speaker_similarity"]),
                }
                for actor_id in GOLDEN_ACTORS
            },
        }

    digest_payload = {
        "policy": POLICY_ID,
        "golden_set": list(GOLDEN_ACTORS),
        "benchmark_anchor": BENCHMARK_ANCHOR,
        "intents": intent_floors,
    }
    digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "c-v4-golden-calibration-2",
        "qa_policy": POLICY_ID,
        "golden_set": list(GOLDEN_ACTORS),
        "benchmark_anchor": BENCHMARK_ANCHOR,
        "calibration_semantics": (
            "intent-specific envelope from historical human-approved B baselines; "
            "absolute integrity failures remain fail-closed"
        ),
        "intents": intent_floors,
        "golden_set_digest": digest,
    }


def evaluate_candidate_qa2(item: dict, calibration: dict) -> list[str]:
    errors = _absolute_gate_errors(item)
    intent = item.get("intent")
    floor = calibration.get("intents", {}).get(intent)
    if floor is None:
        errors.append(f"missing golden-set calibration for intent {intent}")
        return errors

    wpm = float(item.get("wpm", -1.0))
    if not float(floor["pace_min_wpm"]) <= wpm <= float(floor["pace_max_wpm"]):
        errors.append("pace outside intent-specific golden-set pace envelope")
    if normalized_wer(item.get("transcript", ""), item.get("aligned_transcript", "")) > float(floor["max_wer"]):
        errors.append("transcript WER exceeds intent-specific golden-set WER envelope")
    if float(item.get("max_internal_silence_seconds", float("inf"))) > float(floor["max_internal_silence_seconds"]):
        errors.append("internal silence exceeds intent-specific golden-set silence envelope")
    if float(item.get("naturalness_score", -1.0)) < float(floor["naturalness_floor"]):
        errors.append("naturalness below intent-specific golden-set naturalness floor")
    if float(item.get("intent_fidelity_score", -1.0)) < float(floor["intent_fidelity_floor"]):
        errors.append("intent fidelity below intent-specific golden-set intent floor")
    if float(item.get("speaker_similarity", -1.0)) < float(floor["speaker_similarity_floor"]):
        errors.append("speaker similarity below intent-specific golden-set identity floor")
    return errors


def _rank(item: dict) -> tuple:
    quality = (
        float(item["naturalness_score"])
        + float(item["intent_fidelity_score"])
        + float(item["speaker_similarity"])
    ) / 3.0
    return (-quality, abs(float(item["wpm"]) - 147.5), {"B": 0, "A": 1, "C": 2}.get(item["variant"], 9))


def select_actor_calibration_qa2(actor_id: str, candidates_by_intent: dict, calibration: dict) -> tuple[dict, dict]:
    selected, rejected = {}, {}
    for intent in REQUIRED_INTENTS:
        candidates = candidates_by_intent.get(intent, [])
        passing = [item for item in candidates if not evaluate_candidate_qa2(item, calibration)]
        if not passing:
            rejected[intent] = {
                item.get("variant", "unknown"): evaluate_candidate_qa2(item, calibration)
                for item in candidates
            } or {"all": ["no candidates"]}
        else:
            selected[intent] = min(passing, key=_rank)
    return ({}, rejected) if rejected else (selected, {})
