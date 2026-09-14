import importlib
import tempfile
import unittest
from pathlib import Path


class BuildBilingualHighlightsTests(unittest.TestCase):
    def test_compiles_validated_mapping_to_reader_and_report_paths(self):
        module = importlib.import_module('build_bilingual_highlights')
        docs = [{
            'article_id': 'text1',
            'sentences': [{
                'id': 's01', 'en': 'A difficult term.', 'zh': '这是一个难词。',
                'vocab': [{'word': 'difficult', 'level': 6, 'start': 2, 'end': 11}],
            }],
        }]
        mapping = {
            'version': 1, 'year': 2003,
            'articles': {'text1': {'s01': [{
                'en_start': 2, 'en_end': 11, 'en_text': 'difficult',
                'zh_spans': [{'start': 4, 'end': 6, 'text': '难词'}],
            }]}},
            'exceptions': [],
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            canonical, report = module.compile_mapping(mapping, docs, root=root)
            self.assertEqual(report['errors'], [])
            self.assertEqual(report['required_occurrences'], 1)
            self.assertEqual(canonical, mapping)
            self.assertTrue((root / 'kaoyan-reader-v1/content/2003/bilingual-highlights.json').is_file())
            self.assertTrue((root / 'reports/bilingual-highlights/2003.json').is_file())

    def test_invalid_mapping_refuses_to_publish(self):
        module = importlib.import_module('build_bilingual_highlights')
        docs = [{
            'article_id': 'text1',
            'sentences': [{
                'id': 's01', 'en': 'A difficult term.', 'zh': '这是一个难词。',
                'vocab': [{'word': 'difficult', 'level': 6, 'start': 2, 'end': 11}],
            }],
        }]
        mapping = {'version': 1, 'year': 2003, 'articles': {'text1': {'s01': []}}, 'exceptions': []}
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                module.compile_mapping(mapping, docs, root=Path(td))


if __name__ == '__main__':
    unittest.main()
