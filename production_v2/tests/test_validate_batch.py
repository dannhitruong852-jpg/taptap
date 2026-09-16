import json
import tempfile
import unittest
from pathlib import Path

from production_v2.validate_batch import validate_batch


class ValidateBatchTests(unittest.TestCase):
    def _fixture(self, root, missing_segments=None):
        content_path = root / 'content/2013/c/text1.json'
        manifest_path = root / 'audio/2013/v4/c-text1/manifest.json'
        content_path.parent.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)

        content = {
            'sentences': [
                {'id': 's01', 'en': 'Hello', 'segments': [{'text': 'Hello'}]},
            ],
        }
        content_path.write_text(json.dumps(content))

        audio_manifest = {
            'sentences': {
                's01': {
                    'path': './audio/2013/v4/c-text1/s01.opus',
                    'mp3_path': './audio/2013/v4/c-text1/s01.mp3',
                },
            },
            'missing_segments': missing_segments or [],
        }
        manifest_path.write_text(json.dumps(audio_manifest))
        (manifest_path.parent / 's01.opus').write_bytes(b'x')
        (manifest_path.parent / 's01.mp3').write_bytes(b'x')

        catalog = {'articles': [
            {
                'id': '2013-text1',
                'year': 2013,
                'content': './content/2013/c/text1.json',
                'manifest': './audio/2013/v4/c-text1/manifest.json',
                'sentences': 1,
            },
        ]}
        batch = {
            'batch_id': 'b',
            'pipeline_version': 2,
            'years': [2013],
            'expected_articles': {'2013': ['text1']},
            'source_ref': 'abc',
            'state': 'validated',
            'created_at': 'x',
        }
        return batch, catalog

    def test_preflight_accepts_complete_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            batch, catalog = self._fixture(Path(temp_dir))
            report = validate_batch(batch, catalog, Path(temp_dir), 'preflight')
            self.assertTrue(report['ok'])

    def test_release_rejects_missing_segments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            batch, catalog = self._fixture(Path(temp_dir), missing_segments=['s01-01'])
            report = validate_batch(batch, catalog, Path(temp_dir), 'release')
            self.assertFalse(report['ok'])
            self.assertTrue(any('missing_segments' in error for error in report['errors']))

    def test_preflight_rejects_missing_expected_article(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content_path = root / 'content/2013/c/text1.json'
            content_path.parent.mkdir(parents=True)
            content_path.write_text(json.dumps({
                'sentences': [{'id': 's01', 'en': 'x', 'segments': [{'text': 'x'}]}],
            }))
            batch = {
                'batch_id': 'b',
                'pipeline_version': 2,
                'years': [2013],
                'expected_articles': {'2013': ['text1', 'text2']},
                'source_ref': 'abc',
                'state': 'validated',
                'created_at': 'x',
            }
            catalog = {'articles': [
                {
                    'id': '2013-text1',
                    'year': 2013,
                    'content': './content/2013/c/text1.json',
                    'sentences': 1,
                },
            ]}
            report = validate_batch(batch, catalog, root, 'preflight')
            self.assertFalse(report['ok'])
            self.assertTrue(any('article inventory mismatch' in error for error in report['errors']))


if __name__ == '__main__':
    unittest.main()
