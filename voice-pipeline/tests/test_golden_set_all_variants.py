import unittest

from calibration.golden_set_qa import GOLDEN_ACTORS, build_golden_calibration
from calibration.automatic_qa import REQUIRED_INTENTS

SCENE_BY_INTENT = {
    "neutral_explain": ("neutral_explain", "01-explanation"),
    "serious_analysis": ("serious_analysis", "02-analysis"),
    "warm_explain": ("warm_explain", "03-warm"),
    "narrative_build": ("narrative_build", "04-story"),
    "contrast": ("contrast", "05-turn"),
    "information_peak": ("information_peak", "06-emphasis"),
    "restrained_irony": ("restrained_irony", "07-humor"),
    "curious_probe": ("serious_analysis", "08-commentary"),
    "quoted_character": ("quoted_character", "09-quotation"),
    "qualification": ("qualification", "10-long-sentence"),
}


def candidate(actor, intent, scene, variant, *, fidelity, wpm, edge=0.1):
    return {
        "actor_id": actor,
        "reference_actor_id": actor,
        "reference_sha256": "r" * 64,
        "audio_sha256": "a" * 64,
        "generation_fingerprint": "f" * 64,
        "expected_fingerprint": "f" * 64,
        "transcript": "one two three four five six",
        "aligned_transcript": "one two three four five six",
        "duration_seconds": 3.0,
        "wpm": wpm,
        "clipping_ratio": 0.0,
        "leading_silence_seconds": edge,
        "trailing_silence_seconds": 0.1,
        "max_internal_silence_seconds": 0.3,
        "alignment_status": "passed",
        "words": [{"word": "one", "start": 0.1, "end": 0.2}],
        "speaker_similarity": 0.95,
        "naturalness_score": 0.80,
        "intent_fidelity_score": fidelity,
        "artificial_pause_ms": 0,
        "post_tempo": False,
        "controls": {},
        "variant": variant,
        "intent": intent,
        "scene_id": scene,
    }


def scored_board():
    result = {}
    for actor in GOLDEN_ACTORS:
        by_intent = {}
        for target in REQUIRED_INTENTS:
            historical, scene = SCENE_BY_INTENT[target]
            by_intent.setdefault(historical, []).extend([
                candidate(actor, historical, scene, "A", fidelity=0.9771, wpm=120.0),
                candidate(actor, historical, scene, "B", fidelity=1.0, wpm=140.0),
                candidate(actor, historical, scene, "C", fidelity=0.9771, wpm=160.0),
            ])
        result[actor] = {"actor_id": actor, "candidates": by_intent}
    return result


def approvals():
    return {
        "review_basis": "User listened to the complete 8-actor A/B/C audition board and judged the set acceptable for first production. Balanced B is the first-production baseline.",
        "actors": {
            actor: {
                "status": "accepted",
                "approval_method": "human_listening",
                "default_variant": "B",
            }
            for actor in GOLDEN_ACTORS
        },
    }


class GoldenSetAllVariantsTests(unittest.TestCase):
    def test_human_reviewed_a_b_c_define_envelope_while_b_remains_default(self):
        calibration = build_golden_calibration(scored_board(), approvals())
        neutral = calibration["intents"]["neutral_explain"]
        self.assertEqual(120.0, neutral["pace_min_wpm"])
        self.assertEqual(160.0, neutral["pace_max_wpm"])
        self.assertEqual(0.9771, neutral["intent_fidelity_floor"])
        self.assertEqual("B", calibration["default_variant"])
        self.assertEqual(["A", "B", "C"], calibration["human_reviewed_variants"])

    def test_non_default_variant_that_fails_absolute_integrity_is_excluded_not_used_as_floor(self):
        data = scored_board()
        # Actor 01 C has too much edge silence. It was heard historically, but must not widen an absolute integrity gate.
        candidates = data["01"]["candidates"]["neutral_explain"]
        for item in candidates:
            if item["scene_id"] == "01-explanation" and item["variant"] == "C":
                item["leading_silence_seconds"] = 0.8
        calibration = build_golden_calibration(data, approvals())
        neutral = calibration["intents"]["neutral_explain"]
        self.assertIn("01", neutral["excluded_variants"])
        self.assertIn("C", neutral["excluded_variants"]["01"])
        self.assertEqual(160.0, neutral["pace_max_wpm"])  # other actors' C still establish the envelope

    def test_default_b_must_still_pass_absolute_integrity(self):
        data = scored_board()
        for item in data["01"]["candidates"]["neutral_explain"]:
            if item["scene_id"] == "01-explanation" and item["variant"] == "B":
                item["leading_silence_seconds"] = 0.8
        with self.assertRaisesRegex(ValueError, "default B candidate fails absolute gate"):
            build_golden_calibration(data, approvals())


if __name__ == "__main__":
    unittest.main()
