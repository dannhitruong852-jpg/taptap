import json
import unittest
from pathlib import Path

from c_v4_schema import REQUIRED_CALIBRATION_INTENTS, validate_actor_calibration
from calibration.build_expansion_profiles import build_profile


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "voice-pipeline" / "config"
EXPANSION = {"03", "06", "07", "10", "11", "14", "15"}


class ActorExpansionContractTests(unittest.TestCase):
    def test_expansion_actors_have_traceable_source_mapping(self):
        data = json.loads((CONFIG / "actor_sources.json").read_text(encoding="utf-8"))
        sources = data["actors"]
        self.assertEqual(EXPANSION, set(sources))
        for actor_id, item in sources.items():
            self.assertEqual(actor_id, item["actor_id"])
            self.assertTrue(item["source_speaker"])
            self.assertIn(item["source_corpus"], {"EARS", "VCTK"})
            self.assertTrue(item["source_license"])
            self.assertTrue(item["source_url"].startswith("https://"))
            self.assertIn(item["gender"], {"male", "female"})
            self.assertTrue(item["age_group"])
            self.assertTrue(item["native_language"])

    def test_all_seven_profiles_build_and_cover_ten_director_intents(self):
        sources = json.loads((CONFIG / "actor_sources.json").read_text(encoding="utf-8"))["actors"]
        seen_centers = set()
        for actor_id in sorted(EXPANSION):
            profile = build_profile(actor_id)
            self.assertEqual(actor_id, profile["actor_id"])
            self.assertEqual(sources[actor_id]["source_speaker"], profile["source_speaker"])
            self.assertEqual(sources[actor_id]["source_corpus"], profile["source_corpus"])
            self.assertEqual(set(REQUIRED_CALIBRATION_INTENTS), set(profile["intent_profiles"]))
            self.assertEqual([], validate_actor_calibration(profile))
            self.assertFalse(profile["eligible"])
            self.assertEqual({}, profile["selected_candidates"])
            centers = tuple(
                (name, tuple(sorted(item["center"].items())))
                for name, item in sorted(profile["intent_profiles"].items())
            )
            self.assertNotIn(centers, seen_centers)
            seen_centers.add(centers)

    def test_expansion_workflow_is_real_generation_not_manifest_only(self):
        workflow = (ROOT / ".github" / "workflows" / "c-v4-actor-expansion.yml").read_text(encoding="utf-8")
        for actor_id in sorted(EXPANSION):
            self.assertIn(f"'{actor_id}'", workflow)
        self.assertIn("chatterbox-tts==0.1.7", workflow)
        self.assertIn("render_auditions.py", workflow)
        self.assertIn("score_auditions.py", workflow)
        self.assertIn("automatic_qa.py", workflow)
        self.assertIn("210", workflow)
        self.assertIn("artificial_pause_ms", workflow)
        self.assertIn("post_tempo", workflow)


if __name__ == "__main__":
    unittest.main()
