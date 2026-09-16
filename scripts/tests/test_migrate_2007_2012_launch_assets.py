import unittest

from scripts.migrate_2007_2012_launch_assets import normalize_vocabulary, choose_chinese_span


class LaunchAssetMigrationTest(unittest.TestCase):
    def test_wraps_legacy_curated_vocabulary(self):
        legacy = {
            "research": [5, "研究；调查"],
            "evidence": [5, "证据；依据"],
        }
        wrapped = normalize_vocabulary(2007, legacy)
        self.assertEqual(wrapped["year"], 2007)
        self.assertEqual(wrapped["scale"], "project-curated-1-9-v1")
        self.assertEqual(wrapped["qa"]["status"], "reviewed")
        self.assertEqual(wrapped["vocabulary"], legacy)

    def test_preserves_already_wrapped_vocabulary(self):
        wrapped = {
            "year": 2008,
            "scale": "project-curated-1-9-v1",
            "qa": {"status": "reviewed"},
            "vocabulary": {"policy": [5, "政策；方针"]},
        }
        self.assertEqual(normalize_vocabulary(2008, wrapped), wrapped)

    def test_finds_unique_literal_translation_gloss(self):
        start, end, text = choose_chinese_span("研究；调查", "这项研究提供了新的证据。")
        self.assertEqual(text, "研究")
        self.assertEqual("这项研究提供了新的证据。"[start:end], "研究")

    def test_returns_none_when_no_literal_gloss_exists(self):
        self.assertIsNone(choose_chinese_span("证据；依据", "这些结果支持这一结论。"))


if __name__ == "__main__":
    unittest.main()
