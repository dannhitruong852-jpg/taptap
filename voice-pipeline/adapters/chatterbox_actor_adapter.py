"""Resolve C v4 Director Intent through one actor's approved calibration profile."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_VARIANTS = {"A": -1, "B": 0, "C": 1}


def _bounded(value: float, bounds: list[float]) -> float:
    return round(max(bounds[0], min(bounds[1], value)), 3)


def _profile_hash(profile: dict) -> str:
    payload = json.dumps(profile, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _approval(profile_dir: Path, actor_id: str) -> dict | None:
    path = Path(profile_dir) / "production_approvals.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("actors", {}).get(actor_id)


def resolve_controls(actor_id: str, director_intent: str, intensity: int, profile_dir: Path, *, require_eligible: bool = True) -> dict:
    """Resolve approved actor-local calibration into Chatterbox controls.

    V4 deliberately has no fallback to legacy global emotion/PERFORMANCE tables.
    A separate production approval layer may promote an audition profile without
    mutating the immutable audition JSON.
    """
    if intensity not in (0, 1, 2):
        raise ValueError("intensity must be 0, 1, or 2")
    profile_dir = Path(profile_dir)
    path = profile_dir / f"{actor_id}.json"
    if not path.is_file():
        raise ValueError(f"missing actor calibration profile: {actor_id}")
    profile = json.loads(path.read_text(encoding="utf-8"))
    approval = _approval(profile_dir, actor_id)
    approved = bool(approval and approval.get("status") == "accepted")
    if require_eligible and not (profile.get("eligible", False) or approved):
        raise ValueError(f"actor {actor_id} is not eligible for production")
    intents = profile.get("intent_profiles", {})
    if director_intent not in intents:
        raise ValueError(f"unknown director intent for actor {actor_id}: {director_intent}")
    selected = profile.get("selected_candidates", {}).get(director_intent)
    if not selected and approved:
        selected = approval.get("intent_variants", {}).get(director_intent) or approval.get("default_variant")
    if not selected:
        raise ValueError(f"actor {actor_id} has no selected calibration for {director_intent}")
    variant = selected.get("variant") if isinstance(selected, dict) else selected
    if variant not in _VARIANTS:
        raise ValueError(f"invalid selected calibration variant for actor {actor_id}: {variant}")
    local = intents[director_intent]
    center, bounds = local["center"], local["bounds"]
    direction = _VARIANTS[variant]
    intensity_scale = intensity - 1
    step, shift = local.get("step", {}), local.get("intensity_shift", {})
    reference_state = local["reference_state"]
    try:
        reference_path = profile["references"][reference_state]
    except KeyError as exc:
        raise ValueError(f"actor {actor_id} has no reference for state {reference_state}") from exc
    return {
        "actor_id": actor_id,
        "director_intent": director_intent,
        "intensity": intensity,
        "selected_variant": variant,
        "reference_state": reference_state,
        "reference_path": reference_path,
        "exaggeration": _bounded(center["exaggeration"] + direction * step.get("exaggeration", 0) + intensity_scale * shift.get("exaggeration", 0), bounds["exaggeration"]),
        "cfg_weight": _bounded(center["cfg_weight"] + direction * step.get("cfg_weight", 0) + intensity_scale * shift.get("cfg_weight", 0), bounds["cfg_weight"]),
        "temperature": _bounded(center["temperature"] + direction * step.get("temperature", 0), bounds["temperature"]),
        "repetition_penalty": _bounded(center["repetition_penalty"], bounds["repetition_penalty"]),
        "artificial_pause_ms": 0,
        "post_tempo": False,
        "calibration_id": profile["calibration_id"],
        "profile_hash": _profile_hash(profile),
        "approval_status": approval.get("status") if approval else profile.get("human_listening_qa", {}).get("status", "pending"),
    }
