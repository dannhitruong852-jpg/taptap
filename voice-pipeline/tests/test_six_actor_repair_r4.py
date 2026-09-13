import unittest

from calibration.repair_search_r4 import (
    REPAIR_R4_ACTORS,
    REPAIR_R4_TARGETS,
    REPAIR_R4_SPECS,
    build_repair_r4_profile,
    build_repair_r4_render_plan,
    total_repair_r4_renders,
)
from calibration.prepare_repair_references_r4 import EXTRA_REFERENCE_TASKS
from calibration.render_repair_auditions_r4 import stable_repair_r4_seed


SCRIPT = {
    "scenes": [
        {"id": "06-emphasis", "intent": "information_peak", "intensity": 2, "category": "emphasis", "text": "Important information."},
        {"id": "08-probe", "intent": "curious_probe", "intensity": 1, "category": "probe", "text": "A curious question."},
    ]
}


def profile(actor_id):
    refs = {state: f"actor{actor_id}-{state}.wav" for state in (
        "neutral", "warm", "lively", "serious", "curious", "ironic", "tense", "emotional"
    )}
    intents = {}
    for scene in SCRIPT["scenes"]:
        intents[scene["intent"]] = {
            "reference_state": "neutral",
            "center": {
                "exaggeration": 0.5,
                "cfg_weight": 0.5,
                "temperature": 0.75,
                "repetition_penalty": 1.18,
            },
        }
    return {
        "actor_id": actor_id,
        "calibration_id": f"actor-{actor_id}-audition-v1",
        "references": refs,
        "intent_profiles": intents,
        "eligible": False,
        "eligible_for": [],
        "selected_candidates": {},
    }


class SixActorRepairRoundFourTests(unittest.TestCase):
    def test_round_four_runs_03_and_14_in_parallel_without_waiting_for_15(self):
        self.assertEqual(REPAIR_R4_ACTORS, ("03", "14"))
        self.assertEqual(
            REPAIR_R4_TARGETS,
            {"03": ("curious_probe",), "14": ("information_peak",)},
        )
        self.assertNotIn("15", REPAIR_R4_ACTORS)
        self.assertEqual(40, total_repair_r4_renders())

    def test_round_four_changes_reference_strategy_not_qa_thresholds(self):
        self.assertEqual(
            EXTRA_REFERENCE_TASKS["03"],
            {
                "r4_lowpitch1": "rainbow_01_lowpitch",
                "r4_lowpitch2": "rainbow_02_lowpitch",
            },
        )
        self.assertEqual(
            EXTRA_REFERENCE_TASKS["14"],
            {
                "r4_fast1": "rainbow_01_fast",
                "r4_fast2": "rainbow_02_fast",
            },
        )
        self.assertEqual(
            tuple(REPAIR_R4_SPECS["03"]["curious_probe"]["reference_states"]),
            ("warm", "serious", "r4_lowpitch1", "r4_lowpitch2"),
        )
        self.assertEqual(
            tuple(REPAIR_R4_SPECS["14"]["information_peak"]["reference_states"]),
            ("r4_fast1", "r4_fast2"),
        )

    def test_round_four_is_bounded_and_has_no_post_processing(self):
        for actor_id in REPAIR_R4_ACTORS:
            repaired = build_repair_r4_profile(profile(actor_id))
            renders = build_repair_r4_render_plan(repaired, SCRIPT)
            expected = 24 if actor_id == "03" else 16
            self.assertEqual(expected, len(renders))
            self.assertEqual(set(REPAIR_R4_TARGETS[actor_id]), {r["intent"] for r in renders})
            for item in renders:
                self.assertEqual(0, item["artificial_pause_ms"])
                self.assertIs(False, item["post_tempo"])
                self.assertEqual(1.18, item["repetition_penalty"])
                self.assertTrue(item["variant"].startswith("U"))
                self.assertEqual(
                    repaired["references"][item["reference_state"]],
                    item["reference"],
                )

    def test_actor03_searches_identity_reference_space_after_three_control_only_rounds(self):
        spec = REPAIR_R4_SPECS["03"]["curious_probe"]
        self.assertEqual(4, len(spec["reference_states"]))
        self.assertEqual(6, len(spec["controls"]))
        for ex, cfg, temp in spec["controls"]:
            self.assertGreaterEqual(ex, 0.42)
            self.assertLessEqual(ex, 0.52)
            self.assertGreaterEqual(cfg, 0.49)
            self.assertLessEqual(cfg, 0.54)
            self.assertGreaterEqual(temp, 0.70)
            self.assertLessEqual(temp, 0.76)

    def test_actor14_uses_fast_same_speaker_references_instead_of_post_tempo(self):
        spec = REPAIR_R4_SPECS["14"]["information_peak"]
        self.assertEqual(("r4_fast1", "r4_fast2"), tuple(spec["reference_states"]))
        self.assertEqual(8, len(spec["controls"]))
        self.assertTrue(all(temp >= 0.76 for _, _, temp in spec["controls"]))
        self.assertTrue(all(cfg >= 0.44 for _, cfg, _ in spec["controls"]))

    def test_round_four_seed_is_deterministic_and_separate(self):
        first = stable_repair_r4_seed("03", "08-probe", "U1")
        self.assertEqual(first, stable_repair_r4_seed("03", "08-probe", "U1"))
        self.assertNotEqual(first, stable_repair_r4_seed("03", "08-probe", "U2"))
        self.assertNotEqual(first, stable_repair_r4_seed("14", "08-probe", "U1"))


if __name__ == "__main__":
    unittest.main()
