"""Actor-local A/B/C search grids for C v4 listening auditions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


DELIVERIES = (("A", "restrained", -1), ("B", "balanced", 0), ("C", "expressive", 1))


def _bounded(value: float, bounds: list[float]) -> float:
    return round(max(bounds[0], min(bounds[1], value)), 3)


def candidate_controls(actor_profile: dict, intent: str, intensity: int) -> list[dict]:
    """Resolve three candidates from one actor's profile, never a shared final table."""
    if intensity not in (0, 1, 2):
        raise ValueError("intensity must be 0, 1, or 2")
    try:
        local = actor_profile["intent_profiles"][intent]
    except KeyError as exc:
        raise ValueError(f"Actor {actor_profile.get('actor_id')} has no profile for {intent}") from exc
    center, bounds = local["center"], local["bounds"]
    intensity_scale = intensity - 1
    candidates = []
    for variant, delivery, direction in DELIVERIES:
        candidates.append({
            "variant": variant,
            "delivery": delivery,
            "exaggeration": _bounded(
                center["exaggeration"] + direction * local["step"]["exaggeration"]
                + intensity_scale * local.get("intensity_shift", {}).get("exaggeration", 0),
                bounds["exaggeration"],
            ),
            "cfg_weight": _bounded(
                center["cfg_weight"] + direction * local["step"]["cfg_weight"]
                + intensity_scale * local.get("intensity_shift", {}).get("cfg_weight", 0),
                bounds["cfg_weight"],
            ),
            "temperature": _bounded(center["temperature"] + direction * local["step"]["temperature"], bounds["temperature"]),
            "repetition_penalty": _bounded(center["repetition_penalty"], bounds["repetition_penalty"]),
            "reference_state": local["reference_state"],
            "artificial_pause_ms": 0,
            "post_tempo": False,
        })
    return candidates


def build_actor_profile(actor_id: str, cast_cfg: dict, registry: dict) -> dict:
    """Build the immutable identity portion of a new, deliberately ineligible profile."""
    actor = cast_cfg["actors"][actor_id]
    identity = next(item for item in registry["actors"] if item["id"] == actor_id)
    return {
        "schema_version": "c-v4-actor-calibration-1",
        "calibration_id": f"actor-{actor_id}-audition-v1",
        "actor_id": actor_id,
        "source_speaker": actor["speaker"],
        "persona": identity["name"],
        "role": identity["role"],
        "voice_character": identity["style_note"],
        "eligible": False,
        "eligible_for": [],
        "selected_candidates": {},
        "human_listening_qa": {"status": "pending", "reviewed_by": None, "reviewed_at": None},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("intent")
    parser.add_argument("--intensity", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(candidate_controls(json.loads(args.profile.read_text()), args.intent, args.intensity), indent=2))
