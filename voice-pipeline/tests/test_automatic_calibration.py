import unittest

from calibration.automatic_qa import (
    REQUIRED_INTENTS, evaluate_candidate, select_actor_calibration,
    validate_production_approvals,
)
from c_v4_schema import validate_actor_calibration


def candidate(variant, score=0.9, **overrides):
    data = {
        "variant": variant, "actor_id": "03", "reference_actor_id": "03",
        "reference_sha256": "r" * 64, "audio_sha256": "a" * 64,
        "generation_fingerprint": "f" * 64, "expected_fingerprint": "f" * 64,
        "transcript": "A reliable calibration sentence.",
        "aligned_transcript": "A reliable calibration sentence.",
        "duration_seconds": 2.0, "wpm": 120.0, "clipping_ratio": 0.0,
        "leading_silence_seconds": 0.1, "trailing_silence_seconds": 0.1,
        "max_internal_silence_seconds": 0.4, "alignment_status": "passed",
        "words": [{"word": "A", "start": 0.1, "end": 0.2},
                  {"word": "reliable", "start": 0.25, "end": 0.7}],
        "speaker_similarity": 0.8, "naturalness_score": score,
        "intent_fidelity_score": score, "artificial_pause_ms": 0,
        "post_tempo": False,
        "controls": {"exaggeration": .5, "cfg_weight": .4,
                     "temperature": .8, "repetition_penalty": 1.18},
    }
    data.update(overrides)
    return data


class AutomaticCalibrationTests(unittest.TestCase):
    def test_profile_requires_all_intents_and_real_intent_differentiation(self):
        profile = {"actor_id": "03", "intent_profiles": {
            intent: {"center": {"exaggeration": .5}} for intent in REQUIRED_INTENTS
        }}
        self.assertTrue(any("distinct" in error for error in validate_actor_calibration(profile)))
        del profile["intent_profiles"]["curious_probe"]
        self.assertTrue(any("curious_probe" in error for error in validate_actor_calibration(profile)))

    def test_gate_reuses_documented_project_thresholds(self):
        self.assertEqual(evaluate_candidate(candidate("A")), [])
        self.assertTrue(any("transcript" in e for e in evaluate_candidate(
            candidate("A", aligned_transcript="A broken sentence."))))
        self.assertTrue(any("speaker" in e for e in evaluate_candidate(
            candidate("A", speaker_similarity=.64))))
        self.assertTrue(any("silence" in e for e in evaluate_candidate(
            candidate("A", max_internal_silence_seconds=1.3))))

    def test_deterministic_selection_prefers_quality_then_variant_name(self):
        candidates = [candidate("C", .92), candidate("B", .92), candidate("A", .88)]
        selected, rejected = select_actor_calibration("03", {
            intent: candidates for intent in REQUIRED_INTENTS
        })
        self.assertEqual(set(selected), set(REQUIRED_INTENTS))
        self.assertTrue(all(value["variant"] == "B" for value in selected.values()))
        self.assertFalse(rejected)

    def test_actor_fails_when_any_intent_has_no_passing_candidate(self):
        grid = {intent: [candidate("A")] for intent in REQUIRED_INTENTS}
        grid["curious_probe"] = [candidate("A", post_tempo=True)]
        selected, rejected = select_actor_calibration("03", grid)
        self.assertEqual(selected, {})
        self.assertIn("curious_probe", rejected)

    def test_automated_approval_provenance_is_required(self):
        errors = validate_production_approvals({"actors": {"03": {
            "status": "accepted", "approval_method": "made_up"
        }}})
        self.assertTrue(any("approval_method" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
