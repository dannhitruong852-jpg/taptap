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


SCENE_BY_INTENT = {
    "neutral_explain": "01-explanation",
    "serious_analysis": "02-analysis",
    "warm_explain": "03-warm",
    "narrative_build": "04-story",
    "contrast": "05-turn",
    "information_peak": "06-emphasis",
    "restrained_irony": "07-humor",
    # Historical human board predates curious_probe; 08-commentary is its traceable predecessor.
    "curious_probe": "08-commentary",
    "quoted_character": "09-quotation",
    "qualification": "10-long-sentence",
}


def scored(
    actor_id,
    intent,
    variant="B",
    naturalness=0.84,
    intent_score=0.86,
    speaker=0.82,
    scene_id=None,
    **overrides,
):
    item = {
        "variant": variant,
        "actor_id": actor_id,
        "reference_actor_id": actor_id,
        "reference_sha256": "r" * 64,
        "audio_sha256": "a" * 64,
        "generation_fingerprint": "f" * 64,
        "expected_fingerprint": "f" * 64,
        "transcript": "one two three four five six seven eight nine ten",
        "aligned_transcript": "one two three four five six seven eight nine ten",
        "duration_seconds": 5.0,
        "wpm": 130.0,
        "clipping_ratio": 0.0,
        "leading_silence_seconds": 0.1,
        "trailing_silence_seconds": 0.1,
        "max_internal_silence_seconds": 0.4,
        "alignment_status": "passed",
        "words": [
            {"word": "one", "start": 0.1, "end": 0.2},
            {"word": "two", "start": 0.25, "end": 0.7},
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
        "scene_id": scene_id or SCENE_BY_INTENT[intent],
    }
    item.update(overrides)
    return item


def golden_scored():
    result = {}
    for index, actor_id in enumerate(GOLDEN_ACTORS):
        by_intent = {}
        for intent in REQUIRED_INTENTS:
            # The historical board used 08-commentary/serious_analysis rather than curious_probe.
            historical_intent = "serious_analysis" if intent == "curious_probe" else intent
            scene_id = SCENE_BY_INTENT[intent]
            base = 0.78 + index * 0.01
            candidates = [
                scored(actor_id, historical_intent, "A", naturalness=0.76, intent_score=0.77, speaker=0.75, scene_id=scene_id),
                scored(actor_id, historical_intent, "B", naturalness=base, intent_score=base + 0.01, speaker=base + 0.02, scene_id=scene_id),
                scored(actor_id, historical_intent, "C", naturalness=0.77, intent_score=0.78, speaker=0.76, scene_id=scene_id),
            ]
            by_intent.setdefault(historical_intent, []).extend(candidates)
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

    def test_calibration_uses_all_human_reviewed_variants_and_keeps_b_as_default(self):
        data = golden_scored()
        # Historical accepted baselines can legitimately sit outside QA1's provisional pace/silence bands.
        data["01"]["candidates"]["neutral_explain"][1]["wpm"] = 222.7
        warm_b = next(
            item for item in data["13"]["candidates"]["warm_explain"]
            if item["variant"] == "B" and item["scene_id"] == "03-warm"
        )
        warm_b["max_internal_silence_seconds"] = 2.30
        quote_b = next(
            item for item in data["02"]["candidates"]["quoted_character"]
            if item["variant"] == "B"
        )
        quote_b["aligned_transcript"] = "one two three four five WRONG seven eight nine ten"  # WER 0.10 > QA1 0.08.

        calibration = build_golden_calibration(data, approvals())
        neutral = calibration["intents"]["neutral_explain"]
        warm = calibration["intents"]["warm_explain"]
        quote = calibration["intents"]["quoted_character"]
        self.assertEqual(neutral["pace_max_wpm"], 222.7)
        self.assertEqual(warm["max_internal_silence_seconds"], 2.30)
        self.assertGreaterEqual(quote["max_wer"], 0.10)
        self.assertAlmostEqual(neutral["naturalness_floor"], 0.76)
        self.assertAlmostEqual(neutral["intent_fidelity_floor"], 0.77)
        self.assertAlmostEqual(neutral["speaker_similarity_floor"], 0.75)
        self.assertEqual(calibration["default_variant"], "B")
        self.assertEqual(calibration["human_reviewed_variants"], ["A", "B", "C"])
        self.assertEqual(calibration["benchmark_anchor"], "05")
        self.assertEqual(calibration["golden_set"], list(GOLDEN_ACTORS))
        self.assertTrue(calibration["golden_set_digest"])

    def test_legacy_commentary_is_explicit_proxy_for_historical_missing_curious_probe(self):
        calibration = build_golden_calibration(golden_scored(), approvals())
        curious = calibration["intents"]["curious_probe"]
        self.assertEqual(curious["calibration_source"], "legacy_scene_proxy")
        self.assertEqual(curious["source_scene_id"], "08-commentary")
        self.assertEqual(curious["historical_intent"], "serious_analysis")

    def test_missing_human_approved_golden_actor_fails_closed(self):
        data = golden_scored()
        data.pop("13")
        with self.assertRaisesRegex(ValueError, "golden actor 13"):
            build_golden_calibration(data, approvals())

    def test_candidate_is_judged_against_golden_envelope_not_fixed_qa1_pace_or_point_75(self):
        data = golden_scored()
        for actor_id in GOLDEN_ACTORS:
            neutral_b = next(
                item for item in data[actor_id]["candidates"]["neutral_explain"] if item["variant"] == "B"
            )
            neutral_b["wpm"] = 200.0 + int(actor_id)
        calibration = build_golden_calibration(data, approvals())

        # 205 WPM violates QA1's 190 cap, but is inside the human-reviewed Golden Set envelope.
        inside = scored("03", "neutral_explain", wpm=205.0, naturalness=0.90, intent_score=0.90, speaker=0.90)
        self.assertEqual([], evaluate_candidate_qa2(inside, calibration))

        outside = scored("03", "neutral_explain", wpm=260.0, naturalness=0.90, intent_score=0.90, speaker=0.90)
        errors = evaluate_candidate_qa2(outside, calibration)
        self.assertTrue(any("golden-set pace envelope" in error for error in errors))

        below = scored("03", "neutral_explain", wpm=205.0, naturalness=0.759, intent_score=0.90, speaker=0.90)
        errors = evaluate_candidate_qa2(below, calibration)
        self.assertTrue(any("golden-set naturalness floor" in error for error in errors))

    def test_absolute_integrity_gates_remain_fail_closed(self):
        calibration = build_golden_calibration(golden_scored(), approvals())
        bad = scored("03", "neutral_explain", clipping_ratio=0.01, post_tempo=True)
        errors = evaluate_candidate_qa2(bad, calibration)
        self.assertTrue(any("clipping" in error for error in errors))
        self.assertTrue(any("post tempo" in error for error in errors))

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
