import importlib
import unittest


class BilingualHighlightContractTests(unittest.TestCase):
    def _module(self):
        try:
            return importlib.import_module('bilingual_highlights')
        except ModuleNotFoundError:
            return None

    def test_validator_module_exports_contract(self):
        module = self._module()
        self.assertIsNotNone(module, 'bilingual_highlights module must exist')
        self.assertTrue(hasattr(module, 'validate_bilingual_highlights'))

    def test_missing_level6_occurrence_is_an_error(self):
        module = self._module()
        self.assertIsNotNone(module)
        article = {
            'article_id': 'text1',
            'sentences': [{
                'id': 's01',
                'en': 'A difficult term.',
                'zh': '一个难词。',
                'vocab': [{'word': 'difficult', 'level': 6, 'start': 2, 'end': 11}],
            }],
        }
        mapping = {'version': 1, 'year': 2003, 'articles': {'text1': {'s01': []}}, 'exceptions': []}
        report = module.validate_bilingual_highlights(mapping, [article])
        self.assertEqual(report['required_occurrences'], 1)
        self.assertEqual(report['mapped_occurrences'], 0)
        self.assertTrue(any(e['code'] == 'unmapped_required_occurrence' for e in report['errors']))

    def test_exact_mapping_satisfies_required_occurrence(self):
        module = self._module()
        self.assertIsNotNone(module)
        article = {
            'article_id': 'text1',
            'sentences': [{
                'id': 's01',
                'en': 'A difficult term.',
                'zh': '这是一个难词。',
                'vocab': [{'word': 'difficult', 'level': 6, 'start': 2, 'end': 11}],
            }],
        }
        mapping = {
            'version': 1,
            'year': 2003,
            'articles': {'text1': {'s01': [{
                'en_start': 2, 'en_end': 11, 'en_text': 'difficult',
                'zh_spans': [{'start': 4, 'end': 6, 'text': '难词'}],
            }]}},
            'exceptions': [],
        }
        report = module.validate_bilingual_highlights(mapping, [article])
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['mapped_occurrences'], 1)
        self.assertEqual(report['reviewed_exceptions'], 0)

    def test_stale_chinese_span_is_rejected(self):
        module = self._module()
        self.assertIsNotNone(module)
        article = {
            'article_id': 'text1',
            'sentences': [{
                'id': 's01', 'en': 'A difficult term.', 'zh': '这是一个难词。',
                'vocab': [{'word': 'difficult', 'level': 6, 'start': 2, 'end': 11}],
            }],
        }
        mapping = {
            'version': 1, 'year': 2003,
            'articles': {'text1': {'s01': [{
                'en_start': 2, 'en_end': 11, 'en_text': 'difficult',
                'zh_spans': [{'start': 4, 'end': 6, 'text': '错误'}],
            }]}},
            'exceptions': [],
        }
        report = module.validate_bilingual_highlights(mapping, [article])
        self.assertTrue(any(e['code'] == 'stale_chinese_span' for e in report['errors']))

    def test_reviewed_exception_can_cover_unmappable_occurrence(self):
        module = self._module()
        self.assertIsNotNone(module)
        article = {
            'article_id': 'text1',
            'sentences': [{
                'id': 's01', 'en': 'A difficult term.', 'zh': '意思被重组。',
                'vocab': [{'word': 'difficult', 'level': 6, 'start': 2, 'end': 11}],
            }],
        }
        mapping = {
            'version': 1, 'year': 2003, 'articles': {'text1': {'s01': []}},
            'exceptions': [{
                'article_id': 'text1', 'sentence_id': 's01',
                'en_start': 2, 'en_end': 11,
                'reason': 'translation restructures the concept without a clean contiguous Chinese span',
            }],
        }
        report = module.validate_bilingual_highlights(mapping, [article])
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['reviewed_exceptions'], 1)


    def test_study_gloss_only_exception_covers_unaligned_occurrence_without_chinese_span(self):
        module = self._module()
        phrase = 'fell short of expectations'
        en = 'The plan fell short of expectations.'
        start = en.index(phrase)
        article = {'article_id':'text1','sentences':[{
            'id':'s01','en':en,'zh':'这项计划的结果比人们原先设想的更差。',
            'vocab':[{'word':phrase,'level':7,'start':start,'end':start+len(phrase),'meaning':'未达到预期','study_gloss':'未达到预期'}],
        }]}
        mapping = {'version':1,'year':2027,'articles':{'text1':{}},'exceptions':[{
            'kind':'study_gloss_only','article_id':'text1','sentence_id':'s01',
            'en_start':start,'en_end':start+len(phrase),'en_text':phrase,
            'study_gloss':'未达到预期','reason':'translation restructures the concept without a clean exact Chinese span',
        }]}
        report = module.validate_bilingual_highlights(mapping, [article])
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['mapped_occurrences'], 0)
        self.assertEqual(report['reviewed_exceptions'], 1)
        self.assertEqual(report['study_gloss_only_occurrences'], 1)


if __name__ == '__main__':
    unittest.main()
