"""Validation contracts for the universal C v4 editorial layer."""
from __future__ import annotations

import json

MODEL_FIELDS = {
    "exaggeration", "cfg_weight", "temperature", "repetition_penalty",
    "rate", "pause_before_ms", "pause_after_ms", "artificial_pause_ms"
}
REQUIRED_CALIBRATION_INTENTS = {
    "neutral_explain", "serious_analysis", "warm_explain", "narrative_build",
    "contrast", "information_peak", "restrained_irony", "quoted_character",
    "qualification", "curious_probe",
}
REQUIRED_PROFILE_FIELDS = {
    "article_id", "domain", "author_stance", "formality", "narrativity",
    "humor_level", "rationality_emotionality", "baseline_mood",
    "speaker_persona", "preferred_age_impression", "primary_actor_id", "article_arc"
}


def validate_article_voice_profile(profile: dict) -> list[str]:
    errors = []
    missing = sorted(REQUIRED_PROFILE_FIELDS - set(profile))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if "article_arc" in profile and not profile.get("article_arc"):
        errors.append("article_arc must be nonempty")
    actor = str(profile.get("primary_actor_id", ""))
    if actor and (len(actor) != 2 or not actor.isdigit() or not 1 <= int(actor) <= 15):
        errors.append("primary_actor_id must be 01-15")
    return errors


def validate_director_plan(plan: dict, known_intents: set[str] | None = None) -> list[str]:
    errors = []
    known_intents = known_intents or set()
    if not plan.get("discourse_map"):
        errors.append("discourse_map must be nonempty")
    for label, item in plan.get("discourse_map", {}).items():
        if isinstance(item, str):
            intent = item
            payload = {}
        else:
            payload = item
            intent = payload.get("director_intent")
        illegal = sorted(MODEL_FIELDS & set(payload))
        for field in illegal:
            errors.append(f"{field} is model-specific and forbidden in Director Plan")
        if known_intents and intent not in known_intents:
            errors.append(f"unknown director intent for {label}: {intent}")
    for override in plan.get("overrides", []):
        illegal = sorted(MODEL_FIELDS & set(override))
        for field in illegal:
            errors.append(f"{field} is model-specific and forbidden in Director Plan")
        intent = override.get("director_intent")
        if intent and known_intents and intent not in known_intents:
            errors.append(f"unknown director intent in override: {intent}")
    return errors


def validate_actor_calibration(profile: dict, *, require_eligible: bool = False) -> list[str]:
    errors = []
    if not profile.get("actor_id"):
        errors.append("actor_id is required")
    if not profile.get("intent_profiles"):
        errors.append("intent_profiles are required")
    else:
        missing = sorted(REQUIRED_CALIBRATION_INTENTS - set(profile["intent_profiles"]))
        if missing:
            errors.append("missing required intents: " + ", ".join(missing))
        signatures = {
            json.dumps(value.get("center", {}), sort_keys=True)
            for value in profile["intent_profiles"].values()
        }
        if len(signatures) < 2:
            errors.append("director intents must have distinct actor-local controls")
    if require_eligible and not profile.get("eligible", False):
        errors.append("actor is not eligible")
    return errors


def validate_production_approval(approval: dict) -> list[str]:
    """Require truthful provenance for every production admission."""
    errors = []
    method = approval.get("approval_method")
    if approval.get("status") == "accepted" and method not in {
        "human_listening", "automated_c_v4_qa"
    }:
        errors.append("accepted approval requires a supported approval_method")
    if method == "automated_c_v4_qa" and not approval.get("qa_policy"):
        errors.append("automated approval requires qa_policy provenance")
    return errors
