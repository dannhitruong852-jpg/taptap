import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'build_2007_2012_bilingual_highlights.py'
spec = importlib.util.spec_from_file_location('build_bilingual', MODULE)
build_bilingual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_bilingual)


class BilingualOccurrenceAuthoringTest(unittest.TestCase):
    def test_collects_exact_english_occurrence_offsets(self):
        candidate = {'article': {'id': 'text1', 'rows': [[1, 'A subtle change can be subtle.', '一种细微变化也可能十分微妙。', 'report', []]]}}
        vocabulary = {'subtle': [6, '微妙的；细微的']}
        rows = build_bilingual.collect_occurrences(2007, candidate, vocabulary)
        self.assertEqual(len(rows), 2)
        self.assertEqual([x['en_text'] for x in rows], ['subtle', 'subtle'])
        self.assertEqual(rows[0]['sentence_id'], 's01')
        self.assertEqual(candidate['article']['rows'][0][1][rows[0]['en_start']:rows[0]['en_end']], 'subtle')

    def test_unique_literal_gloss_maps_to_exact_chinese_offsets(self):
        row = {'meaning': '微妙的；细微的', 'zh': '一种细微变化。'}
        self.assertEqual(build_bilingual.literal_zh_spans(row), [{'start': 2, 'end': 4, 'text': '细微'}])

    def test_ambiguous_literal_gloss_is_not_forced(self):
        row = {'meaning': '研究；调查', 'zh': '研究人员正在研究这个问题。'}
        self.assertEqual(build_bilingual.literal_zh_spans(row), [])

    def test_override_can_choose_second_identical_chinese_occurrence(self):
        row = {'zh': '领导能力很重要，领导能力也能培养。'}
        spans = build_bilingual.resolve_override_spans(row, [{'text': '领导能力', 'occurrence': 1}])
        second = row['zh'].rfind('领导能力')
        self.assertEqual(spans, [{'start': second, 'end': second + 4, 'text': '领导能力'}])

    def test_override_can_map_one_english_occurrence_to_multiple_chinese_spans(self):
        row = {'zh': '既有损智力，也有损道德品格。'}
        spans = build_bilingual.resolve_override_spans(row, [
            {'text': '有损', 'occurrence': 0}, {'text': '有损', 'occurrence': 1}
        ])
        self.assertEqual(len(spans), 2)
        self.assertEqual([x['text'] for x in spans], ['有损', '有损'])

    def test_override_rejects_missing_or_out_of_range_span(self):
        with self.assertRaises(ValueError):
            build_bilingual.resolve_override_spans({'zh': '只有一次'}, [{'text': '没有', 'occurrence': 0}])
        with self.assertRaises(ValueError):
            build_bilingual.resolve_override_spans({'zh': '只有一次'}, [{'text': '一次', 'occurrence': 1}])

    def test_build_mapping_separates_resolved_and_unresolved(self):
        candidate = {'article': {'id': 'text1', 'rows': [
            [1, 'The policy is contradictory.', '这项政策是矛盾的。', 'report', []],
            [2, 'The regime changed.', '旧制度发生了变化。', 'report', []],
        ]}}
        vocabulary = {'contradictory': [7, '矛盾的'], 'regime': [6, '政权；当权期间']}
        mapping, unresolved = build_bilingual.build_article_mapping(2007, candidate, vocabulary)
        entries = mapping['articles']['text1']['s01']
        self.assertEqual(entries[0]['en_text'], 'contradictory')
        self.assertEqual(entries[0]['zh_spans'][0]['text'], '矛盾的')
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]['lemma'], 'regime')


if __name__ == '__main__':
    unittest.main()
