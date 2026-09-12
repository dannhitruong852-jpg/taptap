import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'content-pipeline'))
sys.path.insert(0, str(ROOT / 'voice-pipeline'))

from semantic_spans import attach_semantic_times, load_semantic_spans, validate_semantic_groups


class SemanticSpanTests(unittest.TestCase):
    def test_reordered_translation_is_valid_and_times_follow_english(self):
        sentence = {
            'en': 'Alpha beta. Gamma delta.',
            'zh': '后半句，前半句。',
        }
        groups = [
            {'id': 'g01', 'en_word_start': 2, 'en_word_end': 4, 'zh_char_start': 0, 'zh_char_end': 4},
            {'id': 'g02', 'en_word_start': 0, 'en_word_end': 2, 'zh_char_start': 4, 'zh_char_end': len(sentence['zh'])},
        ]
        self.assertEqual(validate_semantic_groups(sentence, groups), [])
        words = [
            {'word':'Alpha','start':0.0,'end':0.3}, {'word':'beta','start':0.31,'end':0.6},
            {'word':'Gamma','start':1.2,'end':1.5}, {'word':'delta','start':1.51,'end':1.8},
        ]
        timed = attach_semantic_times(groups, words)
        self.assertEqual((timed[0]['start'], timed[0]['end']), (1.2, 1.8))
        self.assertEqual((timed[1]['start'], timed[1]['end']), (0.0, 0.6))

    def test_english_word_overlap_or_gap_is_rejected(self):
        sentence = {'en':'one two three', 'zh':'一二三'}
        groups = [
            {'id':'g01','en_word_start':0,'en_word_end':2,'zh_char_start':0,'zh_char_end':1},
            {'id':'g02','en_word_start':1,'en_word_end':2,'zh_char_start':1,'zh_char_end':3},
        ]
        errors = validate_semantic_groups(sentence, groups)
        self.assertTrue(any('English word' in e for e in errors), errors)

    def test_chinese_nonpunctuation_must_be_covered(self):
        sentence = {'en':'one two', 'zh':'甲，乙。'}
        groups = [
            {'id':'g01','en_word_start':0,'en_word_end':1,'zh_char_start':0,'zh_char_end':2},
            {'id':'g02','en_word_start':1,'en_word_end':2,'zh_char_start':2,'zh_char_end':2},
        ]
        errors = validate_semantic_groups(sentence, groups)
        self.assertTrue(any('Chinese character' in e for e in errors), errors)

    def test_all_91_2002_sentences_have_reviewed_semantic_groups(self):
        spans = load_semantic_spans(ROOT / 'content-pipeline/semantic_spans/2002.json')
        total = 0
        for article in ('cloze','text1','text2','text3','text4','translation'):
            doc = json.loads((ROOT / f'kaoyan-reader-v1/content/2002/c/{article}.json').read_text(encoding='utf-8'))
            article_spans = spans['articles'][article]
            self.assertEqual(set(article_spans), {s['id'] for s in doc['sentences']})
            for sentence in doc['sentences']:
                groups = article_spans[sentence['id']]
                self.assertEqual(validate_semantic_groups(sentence, groups), [], f'{article}/{sentence["id"]}')
                self.assertGreaterEqual(len(groups), 1)
                total += 1
        self.assertEqual(total, 91)

    def test_semantic_data_does_not_modify_translation_or_vocab(self):
        spans = load_semantic_spans(ROOT / 'content-pipeline/semantic_spans/2002.json')
        for article, sentences in spans['articles'].items():
            doc = json.loads((ROOT / f'kaoyan-reader-v1/content/2002/c/{article}.json').read_text(encoding='utf-8'))
            by_id = {s['id']: s for s in doc['sentences']}
            for sid, groups in sentences.items():
                sentence = by_id[sid]
                reconstructed = ''.join(sentence['zh'][g['zh_char_start']:g['zh_char_end']] for g in groups)
                self.assertEqual(reconstructed, sentence['zh'])
                self.assertIn('vocab', sentence)


class SemanticWebArtifactTests(unittest.TestCase):
    def test_built_reader_semantic_copy_matches_reviewed_source(self):
        source=json.loads((ROOT/'content-pipeline/semantic_spans/2002.json').read_text(encoding='utf-8'))
        built=json.loads((ROOT/'kaoyan-reader-v1/content/2002/semantic-spans.json').read_text(encoding='utf-8'))
        self.assertEqual(built,source)


if __name__ == '__main__':
    unittest.main()
