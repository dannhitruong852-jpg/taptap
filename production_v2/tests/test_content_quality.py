import json
import tempfile
import unittest
from pathlib import Path

from production_v2.content_quality import validate_content_quality


def article_doc(actor='02', discourse=('example','contrast','conclude')):
    sentences=[]
    for i,label in enumerate(discourse,1):
        en=f'Sentence {i} has vocabulary.'
        zh=f'句子{i}含有词汇。'
        sentences.append({
            'id':f's{i:02d}','en':en,'zh':zh,'discourse_function':label,
            'vocab':[{'word':'vocabulary','lemma':'vocabulary','level':6,'meaning':'词汇','start':15,'end':25}],
            'segments':[{'id':f's{i:02d}-01','text':en,'actor_id':actor}],
        })
    return {'year':2013,'article_id':'text1','primary_actor_id':actor,'sentences':sentences}


def candidate(actor='02', discourse=('example','contrast','conclude'), scope=True):
    rows=[]
    for i,label in enumerate(discourse,1):
        rows.append([1,f'Sentence {i} has vocabulary.',f'句子{i}含有词汇。',label,[]])
    return {
        'year':2013,
        'article':{'id':'text1','actor':actor,'rows':rows},
        'qa':{
            'review_schema_version':'c-mode-v2-1',
            'source_scope_verified':scope,
            'scope_exclusions_reviewed':True,
            'text_fidelity_reviewed':True,
            'translation_alignment_reviewed':True,
            'sentence_alignment_reviewed':True,
            'question_stems_removed':True,
            'options_removed':True,
            'ocr_corrections_reviewed':True,
            'negation_and_comparison_reviewed':True,
            'sentence_count':len(rows),
        },
    }


def bilingual():
    article={}
    for i in range(1,4):
        article[f's{i:02d}']=[{
            'en_start':15,'en_end':25,'en_text':'vocabulary',
            'zh_spans':[{'start':5,'end':7,'text':'词汇'}],
        }]
    return {'version':1,'year':2013,'articles':{'text1':article}}


class ContentQualityTests(unittest.TestCase):
    def _write(self, root, cand=None, doc=None, mapping=None, voice_actor='02'):
        root=Path(root)
        (root/'reports/content-freeze/2013').mkdir(parents=True)
        (root/'kaoyan-reader-v1/content/2013/c').mkdir(parents=True)
        (root/'content-pipeline/voice_profiles').mkdir(parents=True)
        (root/'reports/content-freeze/2013/text1.candidate.json').write_text(json.dumps(cand or candidate()))
        (root/'kaoyan-reader-v1/content/2013/c/text1.json').write_text(json.dumps(doc or article_doc()))
        (root/'kaoyan-reader-v1/content/2013/bilingual-highlights.json').write_text(json.dumps(mapping or bilingual()))
        (root/'content-pipeline/voice_profiles/2013.json').write_text(json.dumps({
            'year':2013,'profiles':{'text1':{'primary_actor_id':voice_actor,'article_arc':['example','contrast','conclude']}}
        }))
        return {
            'batch_id':'b','pipeline_version':2,'years':[2013],
            'expected_articles':{'2013':['text1']},'source_ref':'abc','state':'validated','created_at':'x'
        }, {'articles':[{'id':'2013-text1','year':2013,'content':'./content/2013/c/text1.json'}]}

    def test_complete_review_chain_passes(self):
        with tempfile.TemporaryDirectory() as td:
            batch,catalog=self._write(td)
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertTrue(report['ok'],report)

    def test_source_scope_must_be_external_verified_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            batch,catalog=self._write(td,cand=candidate(scope=False))
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('source_scope_verified' in e for e in report['errors']))

    def test_future_batches_require_v2_review_schema(self):
        with tempfile.TemporaryDirectory() as td:
            cand=candidate()
            cand['qa'].pop('review_schema_version')
            batch,catalog=self._write(td,cand=cand)
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('review_schema_version' in e for e in report['errors']))

    def test_future_batches_require_normalized_review_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            cand=candidate()
            cand['qa']['text_fidelity_reviewed']=False
            batch,catalog=self._write(td,cand=cand)
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('text_fidelity_reviewed' in e for e in report['errors']))

    def test_candidate_and_compiled_text_must_match_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            doc=article_doc(); doc['sentences'][0]['en']='Changed.'
            batch,catalog=self._write(td,doc=doc)
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('candidate/compiled text mismatch' in e for e in report['errors']))

    def test_actor_mismatch_blocks_freeze(self):
        with tempfile.TemporaryDirectory() as td:
            batch,catalog=self._write(td,voice_actor='03')
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('actor mismatch' in e for e in report['errors']))

    def test_every_level6_vocab_occurrence_requires_exact_bilingual_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            mapping=bilingual(); mapping['articles']['text1']['s01']=[]
            batch,catalog=self._write(td,mapping=mapping)
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('missing bilingual occurrence' in e for e in report['errors']))

    def test_bilingual_offsets_must_match_both_languages(self):
        with tempfile.TemporaryDirectory() as td:
            mapping=bilingual(); mapping['articles']['text1']['s01'][0]['en_start']=14
            batch,catalog=self._write(td,mapping=mapping)
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('invalid bilingual English span' in e for e in report['errors']))

    def test_three_consecutive_low_density_discourse_rows_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            labels=('report','report','report')
            batch,catalog=self._write(td,cand=candidate(discourse=labels),doc=article_doc(discourse=labels))
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('density' in e for e in report['errors']))

    def test_unknown_discourse_function_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            labels=('example','mystery','conclude')
            batch,catalog=self._write(td,cand=candidate(discourse=labels),doc=article_doc(discourse=labels))
            report=validate_content_quality(batch,catalog,Path(td))
            self.assertFalse(report['ok'])
            self.assertTrue(any('unknown discourse' in e for e in report['errors']))


if __name__=='__main__':
    unittest.main()
