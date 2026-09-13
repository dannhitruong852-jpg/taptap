"""Golden-Set-calibrated automated acceptance policy for C v4 voices.

QA2 preserves hard engineering gates from automated-c-v4-qa-1, but replaces
its provisional fixed naturalness/intent thresholds with intent-specific floors
measured from the historical human-approved Golden Set. Actor 05 remains the
quality benchmark anchor for reporting; new actors are not required to imitate
its voice identity.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable

from calibration.automatic_qa import REQUIRED_INTENTS, evaluate_candidate

POLICY_ID = "automated-c-v4-qa-2"
GOLDEN_ACTORS = ("01", "02", "04", "05", "08", "09", "12", "13")
BENCHMARK_ANCHOR = "05"
_PROVISIONAL_QA1_ERRORS = {
    "automated naturalness score below 0.75",
    "automated director-intent score below 0.75",
}


def _hard_gate_errors(item: dict) -> list[str]:
    """Reuse QA1 engineering checks while removing its provisional listening proxies."""
    return [error for error in evaluate_candidate(item) if error not in _PROVISIONAL_QA1_ERRORS]


def _find_selected_candidate(actor_id: str, intent: str, candidates: Iterable[dict], variant: str) -> dict:
    matches = [item for item in candidates if item.get("variant") == variant]
    if len(matches) != 1:
        raise ValueError(
            f"golden actor {actor_id} intent {intent}: expected one human-approved {variant} candidate, got {len(matches)}"
        )
    candidate = matches[0]
    errors = _hard_gate_errors(candidate)
    if errors:
        raise ValueError(f"golden actor {actor_id} intent {intent}: approved candidate fails hard gate: {errors}")
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
        for intent in REQUIRED_INTENTS:
            candidates = actor.get("candidates", {}).get(intent, [])
            selected[actor_id][intent] = _find_selected_candidate(actor_id, intent, candidates, variant)

    intent_floors = {}
    for intent in REQUIRED_INTENTS:
        accepted = [selected[actor_id][intent] for actor_id in GOLDEN_ACTORS]
        intent_floors[intent] = {
            "naturalness_floor": min(float(item["naturalness_score"]) for item in accepted),
            "intent_fidelity_floor": min(float(item["intent_fidelity_score"]) for item in accepted),
            "speaker_similarity_floor": min(float(item["speaker_similarity"]) for item in accepted),
            "golden_values": {
                actor_id: {
                    "variant": selected[actor_id][intent]["variant"],
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
        "schema_version": "c-v4-golden-calibration-1",
        "qa_policy": POLICY_ID,
        "golden_set": list(GOLDEN_ACTORS),
        "benchmark_anchor": BENCHMARK_ANCHOR,
        "calibration_semantics": "intent-specific weakest historical human-approved B baseline after hard engineering gates",
        "intents": intent_floors,
        "golden_set_digest": digest,
    }


def evaluate_candidate_qa2(item: dict, calibration: dict) -> list[str]:
    errors = _hard_gate_errors(item)
    intent = item.get("intent")
    floor = calibration.get("intents", {}).get(intent)
    if floor is None:
        errors.append(f"missing golden-set calibration for intent {intent}")
        return errors
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
