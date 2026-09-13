import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'content-pipeline'))
sys.path.insert(0, str(ROOT / 'voice-pipeline'))

import build_curated_year
from batch_schema import validate_article


class BuildCuratedYearTests(unittest.TestCase):
    def test_compiles_non_2002_source_into_canonical_article(self):
        source = {
            'year': 2005,
            'source_sha256': 'abc',
            'vocabulary': {'underrated': [7, '被低估的']},
        }
        item = {
            'id': 'cloze', 'section_type': 'cloze', 'title': '完型', 'actor': '02',
            'context': '自然解释。',
            'rows': [
                [1, 'The human nose is underrated.| Yet it is sensitive.', '人的鼻子常被低估，但其实很敏锐。', 'contrast', ['underrated', 'sensitive']],
                [1, 'It can detect faint smells.', '它能察觉微弱的气味。', 'explain', ['detect']],
                [1, 'That matters.', '这一点很重要。', 'emphasize', ['matters']],
            ],
        }
        doc = build_curated_year.compile_article(source, item)
        self.assertEqual(doc['year'], 2005)
        self.assertEqual(doc['article_id'], 'cloze')
        self.assertEqual(doc['primary_actor_id'], '02')
        self.assertEqual(doc['sentences'][0]['segments'][0]['audio_path'], './audio/2005/c-cloze/s01-01.opus')
        self.assertEqual(doc['sentences'][0]['vocab'][0]['level'], 7)
        self.assertEqual(''.join(x['text'] for x in doc['sentences'][0]['segments']), doc['sentences'][0]['en'])
        self.assertEqual(validate_article(doc), [])

    def test_builds_year_voice_profiles_and_direction_map(self):
        source = {
            'year': 2006, 'source_sha256': 'abc', 'vocabulary': {},
            'articles': [{'id':'text1','section_type':'reading','title':'x','actor':'08','context':'科技报道',
                          'rows': [[1,'One.','一。','explain',[]],[1,'Two.','二。','contrast',[]],[1,'Three.','三。','conclude',[]]]}]
        }
        profiles = build_curated_year.build_voice_profiles(source)
        direction = build_curated_year.build_direction(source)
        self.assertEqual(profiles['year'], 2006)
        self.assertEqual(profiles['profiles']['text1']['primary_actor_id'], '08')
        self.assertEqual(direction['year'], 2006)
        self.assertEqual(direction['discourse_map']['contrast']['director_intent'], 'contrast')
        self.assertIn('neutral_explain', {x['director_intent'] for x in direction['discourse_map'].values()})

    def test_pipe_boundaries_preserve_sentence_text(self):
        source = {'year': 2003, 'source_sha256': 'abc', 'vocabulary': {}}
        item = {'id':'text1','section_type':'reading','title':'x','actor':'01','context':'x','rows':[
            [1, 'One| two.', '一句。', 'explain', []],
            [1, 'Three.', '三。', 'explain', []],
            [1, 'Four.', '四。', 'explain', []],
        ]}
        doc = build_curated_year.compile_article(source, item)
        self.assertEqual(doc['sentences'][0]['en'], 'One two.')
        self.assertEqual(''.join(x['text'] for x in doc['sentences'][0]['segments']), 'One two.')


if __name__ == '__main__':
    unittest.main()
