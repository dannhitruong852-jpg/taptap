import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'content-pipeline'))
import build_curated_year
import finalize_curated_year

class FinalizeCuratedYearStudyGlossTests(unittest.TestCase):
    def _docs(self, zh):
        en='The plan fell short of expectations.'
        phrase='fell short of expectations'
        vocab=build_curated_year.vocabulary_for(en, {'fall short of expectations':[7,'未达到预期',phrase]})
        return [{'article_id':'text1','sentences':[{'id':'s01','en':en,'zh':zh,'vocab':vocab}]}]

    def test_unaligned_phrase_becomes_study_gloss_only_not_fake_chinese_span(self):
        mapping, report=finalize_curated_year.build_mapping(2027,self._docs('这项计划的结果比人们原先设想的更差。'))
        self.assertEqual(mapping['articles']['text1'], {})
        self.assertEqual(mapping['exceptions'][0]['kind'], 'study_gloss_only')
        self.assertEqual(mapping['exceptions'][0]['study_gloss'], '未达到预期')
        self.assertEqual(report['mapped_occurrences'], 0)
        self.assertEqual(report['study_gloss_only_occurrences'], 1)

    def test_exact_translation_span_still_maps_normally(self):
        mapping, report=finalize_curated_year.build_mapping(2027,self._docs('这项计划未达到预期。'))
        self.assertEqual(mapping['articles']['text1']['s01'][0]['zh_spans'][0]['text'], '未达到预期')
        self.assertEqual(mapping['exceptions'], [])
        self.assertEqual(report['mapped_occurrences'], 1)

if __name__ == '__main__':
    unittest.main()
