import unittest

from calibration.golden_set_qa import (
    BENCHMARK_ANCHOR,
    GOLDEN_ACTORS,
    POLICY_ID,
    build_golden_calibration,
    evaluate_candidate_qa2,
    select_actor_calibration_qa2,
)
from calibration.automatic_qa import REQUIRED_INTENTS


def scored(actor_id, intent, variant="B", naturalness=0.84, intent_score=0.86, speaker=0.82, **overrides):
    item = {
        "variant": variant,
        "actor_id": actor_id,
        "reference_actor_id": actor_id,
        "reference_sha256": "r" * 64,
        "audio_sha256": "a" * 64,
        "generation_fingerprint": "f" * 64,
        "expected_fingerprint": "f" * 64,
        "transcript": "A reliable calibration sentence.",
        "aligned_transcript": "A reliable calibration sentence.",
        "duration_seconds": 2.0,
        "wpm": 130.0,
        "clipping_ratio": 0.0,
        "leading_silence_seconds": 0.1,
        "trailing_silence_seconds": 0.1,
        "max_internal_silence_seconds": 0.4,
        "alignment_status": "passed",
        "words": [
            {"word": "A", "start": 0.1, "end": 0.2},
            {"word": "reliable", "start": 0.25, "end": 0.7},
        ],
        "speaker_similarity": speaker,
        "naturalness_score": naturalness,
        "intent_fidelity_score": intent_score,
        "artificial_pause_ms": 0,
        "post_tempo": False,
        "controls": {
            "exaggeration": 0.5,
            "cfg_weight": 0.4,
            "temperature": 0.8,
            "repetition_penalty": 1.18,
        },
        "intent": intent,
    }
    item.update(overrides)
    return item


def golden_scored():
    result = {}
    for index, actor_id in enumerate(GOLDEN_ACTORS):
        by_intent = {}
        for intent in REQUIRED_INTENTS:
            base = 0.78 + index * 0.01
            by_intent[intent] = [
                scored(actor_id, intent, "A", naturalness=0.76, intent_score=0.77, speaker=0.75),
                scored(actor_id, intent, "B", naturalness=base, intent_score=base + 0.01, speaker=base + 0.02),
                scored(actor_id, intent, "C", naturalness=0.77, intent_score=0.78, speaker=0.76),
            ]
        result[actor_id] = {"actor_id": actor_id, "candidates": by_intent}
    return result


def approvals():
    return {
        "actors": {
            actor_id: {"status": "accepted", "approval_method": "human_listening", "default_variant": "B"}
            for actor_id in GOLDEN_ACTORS
        }
    }


class GoldenSetQa2Tests(unittest.TestCase):
    def test_policy_names_historical_golden_set_and_anchor(self):
        self.assertEqual(POLICY_ID, "automated-c-v4-qa-2")
        self.assertEqual(tuple(GOLDEN_ACTORS), ("01", "02", "04", "05", "08", "09", "12", "13"))
        self.assertEqual(BENCHMARK_ANCHOR, "05")

    def test_calibration_uses_human_approved_b_variants_and_weakest_accepted_floor(self):
        data = golden_scored()
        # A is intentionally lower than B and must not lower the benchmark floor.
        calibration = build_golden_calibration(data, approvals())
        first = REQUIRED_INTENTS[0]
        self.assertAlmostEqual(calibration["intents"][first]["naturalness_floor"], 0.78)
        self.assertAlmostEqual(calibration["intents"][first]["intent_fidelity_floor"], 0.79)
        self.assertAlmostEqual(calibration["intents"][first]["speaker_similarity_floor"], 0.80)
        self.assertEqual(calibration["benchmark_anchor"], "05")
        self.assertEqual(calibration["golden_set"], list(GOLDEN_ACTORS))
        self.assertTrue(calibration["golden_set_digest"])

    def test_missing_human_approved_golden_actor_fails_closed(self):
        data = golden_scored()
        data.pop("13")
        with self.assertRaisesRegex(ValueError, "golden actor 13"):
            build_golden_calibration(data, approvals())

    def test_candidate_is_judged_against_intent_specific_golden_floor_not_fixed_point_75(self):
        calibration = build_golden_calibration(golden_scored(), approvals())
        intent = REQUIRED_INTENTS[0]
        below = scored("03", intent, naturalness=0.779, intent_score=0.90, speaker=0.90)
        errors = evaluate_candidate_qa2(below, calibration)
        self.assertTrue(any("golden-set naturalness floor" in error for error in errors))
        above = scored("03", intent, naturalness=0.781, intent_score=0.90, speaker=0.90)
        self.assertEqual([], evaluate_candidate_qa2(above, calibration))

    def test_all_intents_required_and_best_passing_candidate_selected(self):
        calibration = build_golden_calibration(golden_scored(), approvals())
        grid = {}
        for intent in REQUIRED_INTENTS:
            grid[intent] = [
                scored("03", intent, "A", naturalness=0.80, intent_score=0.82, speaker=0.82),
                scored("03", intent, "B", naturalness=0.86, intent_score=0.87, speaker=0.85),
                scored("03", intent, "C", naturalness=0.83, intent_score=0.84, speaker=0.84),
            ]
        selected, rejected = select_actor_calibration_qa2("03", grid, calibration)
        self.assertFalse(rejected)
        self.assertEqual(set(REQUIRED_INTENTS), set(selected))
        self.assertTrue(all(item["variant"] == "B" for item in selected.values()))

        grid[REQUIRED_INTENTS[-1]] = [scored("03", REQUIRED_INTENTS[-1], "A", naturalness=0.60)]
        selected, rejected = select_actor_calibration_qa2("03", grid, calibration)
        self.assertEqual({}, selected)
        self.assertIn(REQUIRED_INTENTS[-1], rejected)


if __name__ == "__main__":
    unittest.main()
