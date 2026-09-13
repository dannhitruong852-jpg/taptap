import unittest

from calibration.repair_search_r3 import (
    REPAIR_R3_ACTORS,
    REPAIR_R3_TARGETS,
    REPAIR_R3_SPECS,
    build_repair_r3_profile,
    build_repair_r3_render_plan,
    total_repair_r3_renders,
)
from calibration.render_repair_auditions_r3 import stable_repair_r3_seed


SCRIPT = {
    "scenes": [
        {"id": "04-story", "intent": "narrative_build", "intensity": 1, "category": "story", "text": "Narrative text."},
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


class SixActorRepairRoundThreeTests(unittest.TestCase):
    def test_round_three_targets_only_the_four_remaining_failed_cells(self):
        self.assertEqual(REPAIR_R3_ACTORS, ("03", "14", "15"))
        self.assertEqual(
            REPAIR_R3_TARGETS,
            {
                "03": ("curious_probe",),
                "14": ("information_peak",),
                "15": ("narrative_build", "curious_probe"),
            },
        )
        self.assertEqual(4, sum(len(v) for v in REPAIR_R3_TARGETS.values()))
        self.assertEqual(72, total_repair_r3_renders())

    def test_round_three_keeps_qa2_immutable_rules(self):
        for actor_id in REPAIR_R3_ACTORS:
            repaired = build_repair_r3_profile(profile(actor_id))
            renders = build_repair_r3_render_plan(repaired, SCRIPT)
            self.assertEqual(set(REPAIR_R3_TARGETS[actor_id]), {r["intent"] for r in renders})
            for item in renders:
                self.assertEqual(0, item["artificial_pause_ms"])
                self.assertIs(False, item["post_tempo"])
                self.assertEqual(1.18, item["repetition_penalty"])
                self.assertTrue(item["variant"].startswith("T"))
                local = repaired["intent_profiles"][item["intent"]]
                self.assertEqual(local["reference_state"], item["reference_state"])
                self.assertEqual(repaired["references"][item["reference_state"]], item["reference"])

    def test_actor03_returns_to_warm_identity_reference_from_positive_same_actor_evidence(self):
        spec = REPAIR_R3_SPECS["03"]["curious_probe"]
        self.assertEqual("warm", spec["reference_state"])
        self.assertEqual(16, len(spec["controls"]))
        for ex, cfg, temp in spec["controls"]:
            self.assertGreaterEqual(ex, 0.40)
            self.assertLessEqual(ex, 0.50)
            self.assertGreaterEqual(cfg, 0.47)
            self.assertLessEqual(cfg, 0.54)
            self.assertGreaterEqual(temp, 0.70)
            self.assertLessEqual(temp, 0.76)

    def test_actor14_uses_neutral_fast_identity_region_and_dense_seeds(self):
        spec = REPAIR_R3_SPECS["14"]["information_peak"]
        self.assertEqual("neutral", spec["reference_state"])
        self.assertEqual(16, len(spec["controls"]))
        self.assertTrue(all(ex <= 0.50 for ex, _, _ in spec["controls"]))
        self.assertTrue(all(cfg >= 0.48 for _, cfg, _ in spec["controls"]))
        self.assertTrue(all(temp >= 0.73 for _, _, temp in spec["controls"]))

    def test_actor15_narrative_is_seed_dense_around_best_wer_only_region(self):
        spec = REPAIR_R3_SPECS["15"]["narrative_build"]
        self.assertEqual("neutral", spec["reference_state"])
        self.assertEqual(24, len(spec["controls"]))
        self.assertTrue(all(ex <= 0.42 for ex, _, _ in spec["controls"]))
        self.assertTrue(all(cfg >= 0.54 for _, cfg, _ in spec["controls"]))
        self.assertTrue(all(temp <= 0.70 for _, _, temp in spec["controls"]))

    def test_actor15_probe_pushes_toward_slower_more_stable_generation(self):
        spec = REPAIR_R3_SPECS["15"]["curious_probe"]
        self.assertEqual("curious", spec["reference_state"])
        self.assertEqual(16, len(spec["controls"]))
        self.assertTrue(all(ex <= 0.40 for ex, _, _ in spec["controls"]))
        self.assertTrue(all(cfg >= 0.58 for _, cfg, _ in spec["controls"]))
        self.assertTrue(all(temp <= 0.69 for _, _, temp in spec["controls"]))

    def test_round_three_seed_is_deterministic_and_round_specific(self):
        first = stable_repair_r3_seed("03", "08-probe", "T1")
        self.assertEqual(first, stable_repair_r3_seed("03", "08-probe", "T1"))
        self.assertNotEqual(first, stable_repair_r3_seed("03", "08-probe", "T2"))
        self.assertNotEqual(first, stable_repair_r3_seed("14", "08-probe", "T1"))


if __name__ == "__main__":
    unittest.main()
