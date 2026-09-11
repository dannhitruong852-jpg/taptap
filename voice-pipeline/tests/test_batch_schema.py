import importlib.util
import json
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'batch_schema.py'
spec = importlib.util.spec_from_file_location('batch_schema', MODULE_PATH)
batch_schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch_schema)


class BatchSchemaTests(unittest.TestCase):
    def make_sentence(self, sid, contrast='low', actor='05'):
        return {
            'id': sid,
            'en': f'Sentence {sid}.',
            'zh': f'句子 {sid}。',
            'vocab': [],
            'discourse_function': 'explain',
            'prosody_focus': ['Sentence'],
            'contrast_level': contrast,
            'segments': [{
                'id': f's{sid:02d}-a',
                'text': f'Sentence {sid}.',
                'speaker_role': 'narrator',
                'actor_id': actor,
                'emotion': 'neutral',
                'intensity': 0,
                'rate': 1.0,
                'pause_before_ms': 0,
                'pause_after_ms': 120,
                'audio_path': '',
                'generation_fingerprint': '',
                'qa_status': 'pending',
            }]
        }

    def make_article(self):
        return {
            'year': 2025,
            'section_type': 'reading',
            'article_id': 'text1',
            'source_sha256': 'a' * 64,
            'accent': 'en-US',
            'primary_actor_id': '05',
            'article_context': 'Practical explanation.',
            'sentences': [
                self.make_sentence(1, 'low'),
                self.make_sentence(2, 'micro'),
                self.make_sentence(3, 'low'),
                self.make_sentence(4, 'micro'),
            ],
        }

    def test_valid_article_has_no_errors(self):
        self.assertEqual(batch_schema.validate_article(self.make_article()), [])

    def test_rejects_non_content_section_and_unknown_actor(self):
        article = self.make_article()
        article['section_type'] = 'writing'
        article['sentences'][0]['segments'][0]['actor_id'] = '99'
        errors = batch_schema.validate_article(article)
        self.assertTrue(any('section_type' in e for e in errors))
        self.assertTrue(any('actor_id' in e for e in errors))

    def test_rejects_out_of_range_rate_and_intensity(self):
        article = self.make_article()
        seg = article['sentences'][0]['segments'][0]
        seg['rate'] = 1.30
        seg['intensity'] = 3
        errors = batch_schema.validate_article(article)
        self.assertTrue(any('rate' in e for e in errors))
        self.assertTrue(any('intensity' in e for e in errors))

    def test_any_three_sentence_window_requires_micro_or_strong_contrast(self):
        sentences = [self.make_sentence(i, 'low') for i in range(1, 5)]
        errors = batch_schema.validate_c_mode_density(sentences)
        self.assertEqual(errors, ['sentences 1-3 have no micro/strong contrast', 'sentences 2-4 have no micro/strong contrast'])

    def test_config_declares_natural_american_conversational_pace(self):
        cfg_path = Path(__file__).resolve().parents[1] / 'config' / 'c_mode.json'
        cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
        self.assertEqual(cfg['name'], 'C')
        self.assertEqual(cfg['default_accent'], 'en-US')
        self.assertEqual(cfg['pace'], 'natural_conversational')
        self.assertEqual(cfg['max_low_contrast_run'], 2)


if __name__ == '__main__':
    unittest.main()
