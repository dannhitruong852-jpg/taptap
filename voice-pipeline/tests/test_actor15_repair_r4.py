import unittest

from calibration.repair_search_r4_15 import (
    REPAIR_R4_15_TARGETS,
    REPAIR_R4_15_SPECS,
    build_actor15_r4_profile,
    build_actor15_r4_render_plan,
    total_actor15_r4_renders,
)
from calibration.render_repair_auditions_r4_15 import stable_actor15_r4_seed

SCRIPT = {
    "scenes": [
        {"id": "04-story", "intent": "narrative_build", "intensity": 1, "category": "story", "text": "Late one autumn evening, a young researcher found an unopened letter waiting beneath the laboratory door."},
        {"id": "08-probe", "intent": "curious_probe", "intensity": 1, "category": "probe", "text": "If the policy appears efficient on paper, why does its burden still fall so unequally on real people?"},
    ]
}


def profile():
    return {
        "actor_id": "15",
        "calibration_id": "actor-15-audition-v1",
        "references": {"neutral": "actor15-neutral.wav", "curious": "actor15-curious.wav"},
        "intent_profiles": {
            "narrative_build": {"reference_state": "neutral", "center": {"exaggeration": .4, "cfg_weight": .55, "temperature": .69, "repetition_penalty": 1.18}},
            "curious_probe": {"reference_state": "curious", "center": {"exaggeration": .38, "cfg_weight": .60, "temperature": .68, "repetition_penalty": 1.18}},
        },
        "eligible": False,
        "eligible_for": [],
        "selected_candidates": {},
    }


class Actor15RepairRoundFourTests(unittest.TestCase):
    def test_targets_only_actor15_two_remaining_cells(self):
        self.assertEqual(REPAIR_R4_15_TARGETS, ("narrative_build", "curious_probe"))
        self.assertEqual(total_actor15_r4_renders(), 32)

    def test_narrative_uses_pronunciation_aliases_but_preserves_qa_transcript(self):
        aliases = REPAIR_R4_15_SPECS["narrative_build"]["synthesis_texts"]
        self.assertEqual(4, len(aliases))
        self.assertTrue(any("lab-or" in text.lower() or "la-bor" in text.lower() for text in aliases))
        repaired = build_actor15_r4_profile(profile())
        renders = build_actor15_r4_render_plan(repaired, SCRIPT)
        narrative = [r for r in renders if r["intent"] == "narrative_build"]
        self.assertEqual(16, len(narrative))
        for item in narrative:
            self.assertEqual(SCRIPT["scenes"][0]["text"], item["text"])
            self.assertIn(item["synthesis_text"], aliases)

    def test_probe_changes_only_punctuation_prosody_not_words(self):
        aliases = REPAIR_R4_15_SPECS["curious_probe"]["synthesis_texts"]
        self.assertEqual(4, len(aliases))
        canonical = "".join(ch.lower() for ch in SCRIPT["scenes"][1]["text"] if ch.isalnum() or ch.isspace()).split()
        for text in aliases:
            words = "".join(ch.lower() for ch in text if ch.isalnum() or ch.isspace()).split()
            self.assertEqual(canonical, words)

    def test_no_pause_no_post_tempo_and_same_qa_transcript(self):
        repaired = build_actor15_r4_profile(profile())
        renders = build_actor15_r4_render_plan(repaired, SCRIPT)
        self.assertEqual(32, len(renders))
        for item in renders:
            self.assertEqual(0, item["artificial_pause_ms"])
            self.assertIs(False, item["post_tempo"])
            self.assertEqual(1.18, item["repetition_penalty"])
            self.assertTrue(item["variant"].startswith("V"))

    def test_seed_is_deterministic_and_alias_sensitive(self):
        first = stable_actor15_r4_seed("04-story", "V1", "a1")
        self.assertEqual(first, stable_actor15_r4_seed("04-story", "V1", "a1"))
        self.assertNotEqual(first, stable_actor15_r4_seed("04-story", "V1", "a2"))
        self.assertNotEqual(first, stable_actor15_r4_seed("08-probe", "V1", "a1"))


if __name__ == "__main__":
    unittest.main()
