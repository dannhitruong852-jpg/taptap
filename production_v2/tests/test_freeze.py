import json
import tempfile
import unittest
from pathlib import Path

from production_v2.freeze import build_freeze_report


class FreezeTests(unittest.TestCase):
    def _fixture(self, temp_dir):
        repo = Path(temp_dir)
        reader = repo / 'kaoyan-reader-v1'
        content = reader / 'content/2013/c/text1.json'
        candidate = repo / 'reports/content-freeze/2013/text1.candidate.json'
        curated = repo / 'content-pipeline/curated/2013.json'
        voice = repo / 'content-pipeline/voice_profiles/2013.json'
        bilingual = reader / 'content/2013/bilingual-highlights.json'
        for path in (content, candidate, curated, voice, bilingual):
            path.parent.mkdir(parents=True, exist_ok=True)
        content.write_text('{"sentences":[]}', encoding='utf-8')
        candidate.write_text('{"qa":{"source_scope_verified":true}}', encoding='utf-8')
        curated.write_text('{"year":2013,"articles":[]}', encoding='utf-8')
        voice.write_text('{"year":2013,"profiles":{}}', encoding='utf-8')
        bilingual.write_text('{"year":2013,"articles":{}}', encoding='utf-8')

        catalog = {'articles': [
            {'id': '2013-text1', 'year': 2013, 'content': './content/2013/c/text1.json'},
        ]}
        manifest = {
            'batch_id': 'b',
            'pipeline_version': 2,
            'years': [2013],
            'source_ref': 'abc',
        }
        return repo, reader, catalog, manifest, {
            'content': content,
            'candidate': candidate,
            'curated': curated,
            'voice': voice,
            'bilingual': bilingual,
        }

    def test_freeze_report_hashes_selected_content_deterministically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo, reader, catalog, manifest, _ = self._fixture(temp_dir)
            first = build_freeze_report(manifest, catalog, reader)
            second = build_freeze_report(manifest, catalog, reader)
            self.assertEqual(first['freeze_id'], second['freeze_id'])
            self.assertEqual(first['article_count'], 1)
            self.assertEqual(len(first['articles']['2013-text1']['content_sha256']), 64)
            self.assertEqual(len(first['articles']['2013-text1']['candidate_sha256']), 64)
            self.assertEqual(len(first['years_meta']['2013']['bilingual_sha256']), 64)
            self.assertEqual(len(first['years_meta']['2013']['voice_profile_sha256']), 64)
            self.assertEqual(len(first['years_meta']['2013']['curated_inputs']), 1)

    def test_freeze_id_changes_when_any_reviewed_input_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo, reader, catalog, manifest, paths = self._fixture(temp_dir)
            baseline = build_freeze_report(manifest, catalog, reader)['freeze_id']
            for key in ('candidate', 'curated', 'voice', 'bilingual', 'content'):
                original = paths[key].read_text(encoding='utf-8')
                paths[key].write_text(original + '\n', encoding='utf-8')
                changed = build_freeze_report(manifest, catalog, reader)['freeze_id']
                self.assertNotEqual(baseline, changed, key)
                paths[key].write_text(original, encoding='utf-8')

    def test_missing_reviewed_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo, reader, catalog, manifest, paths = self._fixture(temp_dir)
            paths['candidate'].unlink()
            with self.assertRaises(FileNotFoundError):
                build_freeze_report(manifest, catalog, reader)


if __name__ == '__main__':
    unittest.main()
