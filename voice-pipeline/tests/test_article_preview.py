import json
import unittest
from pathlib import Path

from calibration.article_preview import build_article_render_plan


class ArticlePreviewTest(unittest.TestCase):
    def test_builds_one_five_segment_plan_for_each_of_15_actors(self):
        root = Path(__file__).resolve().parents[2]
        script = json.loads((root / "voice-pipeline/calibration/article_emotion_probe.json").read_text(encoding="utf-8"))
        profiles = root / "voice-pipeline/calibration/actors"
        plans = build_article_render_plan(profiles, script)

        self.assertEqual(sorted(plans), [f"{i:02d}" for i in range(1, 16)])
        self.assertTrue(all(len(items) == 5 for items in plans.values()))
        self.assertTrue(all(item["artificial_pause_ms"] == 0 for items in plans.values() for item in items))
        self.assertTrue(all(item["post_tempo"] is False for items in plans.values() for item in items))

    def test_preview_workflow_reuses_the_correct_reference_family_and_runs_all_actors_in_parallel(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/c-v4-article-preview-full.yml").read_text(encoding="utf-8")

        self.assertIn("max-parallel: 15", workflow)
        self.assertIn("01|02|04|05|08|09|12|13", workflow)
        self.assertIn("prepare_2002_cast_references.py", workflow)
        self.assertIn("prepare_expansion_references.py", workflow)
        self.assertIn("prepare_repair_references_r4.py", workflow)


if __name__ == "__main__":
    unittest.main()
