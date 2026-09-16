import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'build_2007_2012_vocabulary.py'
spec = importlib.util.spec_from_file_location('build_vocab', MODULE)
build_vocab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_vocab)


class VocabularyBuilderContractTest(unittest.TestCase):
    def test_assign_level_tracks_shipped_frequency_bands(self):
        self.assertEqual(build_vocab.assign_level({'bnc': '4000', 'frq': '5000'}), 6)
        self.assertEqual(build_vocab.assign_level({'bnc': '9000', 'frq': '10000'}), 7)
        self.assertEqual(build_vocab.assign_level({'bnc': '16000', 'frq': '15000'}), 8)
        self.assertEqual(build_vocab.assign_level({'bnc': '30000', 'frq': '32000'}), 9)
        self.assertEqual(build_vocab.assign_level({'bnc': '0', 'frq': '0'}), 9)

    def test_clean_translation_keeps_compact_chinese_gloss(self):
        raw = 'n. 基础；根据\nv. 建立；创办'
        self.assertEqual(build_vocab.clean_translation(raw), '基础；根据')

    def test_calibrated_selector_prefers_advanced_exam_word(self):
        advanced = {
            'bnc': '12000', 'frq': '11000', 'collins': '1', 'oxford': '0',
            'tag': 'cet6 ky toefl gre', 'translation': 'adj. 复杂的；错综的'
        }
        common = {
            'bnc': '100', 'frq': '90', 'collins': '5', 'oxford': '1',
            'tag': 'zk gk cet4', 'translation': 'adj. 好的'
        }
        self.assertGreater(
            build_vocab.selection_probability('intricate', advanced),
            build_vocab.selection_probability('good', common),
        )

    def test_build_document_uses_production_schema_and_levels_6_to_9_only(self):
        records = {
            'intricate': {
                'bnc': '12000', 'frq': '11000', 'collins': '1', 'oxford': '0',
                'tag': 'cet6 ky toefl gre', 'translation': 'adj. 复杂的；错综的'
            }
        }
        doc = build_vocab.build_document(2007, {'intricate'}, records, threshold=0.0)
        self.assertEqual(doc['year'], 2007)
        self.assertEqual(doc['scale'], 'project-curated-1-9-v1')
        self.assertEqual(doc['qa']['status'], 'reviewed')
        self.assertIn('intricate', doc['vocabulary'])
        level, meaning = doc['vocabulary']['intricate'][:2]
        self.assertIn(level, range(6, 10))
        self.assertTrue(meaning)


if __name__ == '__main__':
    unittest.main()
