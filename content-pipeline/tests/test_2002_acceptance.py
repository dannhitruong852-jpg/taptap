import json
import re
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'voice-pipeline'))
from batch_schema import validate_article

class Acceptance2002Tests(unittest.TestCase):
    def test_six_canonical_articles_have_complete_aligned_content(self):
        paths = sorted((ROOT / 'kaoyan-reader-v1/content/2002/c').glob('*.json'))
        self.assertEqual(len(paths), 6)
        counts = {'cloze':13, 'text1':21, 'text2':16, 'text3':21, 'text4':15, 'translation':5}
        for path in paths:
            doc = json.loads(path.read_text())
            self.assertEqual(validate_article(doc), [], path.name)
            self.assertEqual(len(doc['sentences']), counts[path.stem])
            self.assertEqual(doc['source_sha256'], '55fb0335e629fa71d71d5220af1215345ef3cf2cc23344adc44d0373f64aaa47')
            for sentence in doc['sentences']:
                self.assertTrue(re.search(r'[\u4e00-\u9fff]', sentence['zh']))
                self.assertEqual(''.join(s['text'] for s in sentence['segments']), sentence['en'])
                self.assertNotRegex(sentence['en'], r'\[\s*[ABCD]\s*\]|ANSWER SHEET|Directions:|\{\{\d+\}\}')
                for token in sentence['vocab']:
                    self.assertIn(token['level'], range(1,10))
                    self.assertIn(token['word'].casefold(), sentence['en'].casefold())
    def test_text1_fidelity_and_narration_contrast(self):
        p = ROOT / 'kaoyan-reader-v1/content/2002/c/text1.json'
        self.assertTrue(p.is_file())
        doc = json.loads(p.read_text())
        self.assertIn('alternatively if', doc['sentences'][3]['en'])
        self.assertNotIn('alternatively, if', doc['sentences'][3]['en'])
        action = doc['sentences'][7]
        self.assertGreater(len(action['segments']), 1)
        self.assertGreater(len({(s['rate'], s['exaggeration']) for s in action['segments']}), 1)
        self.assertEqual({s['actor_id'] for s in action['segments']}, {'05'})
    def test_grade_is_stable_across_articles(self):
        grades = {}
        for p in (ROOT / 'kaoyan-reader-v1/content/2002/c').glob('*.json'):
            for sentence in json.loads(p.read_text())['sentences']:
                for token in sentence['vocab']:
                    lemma = token['lemma']
                    if lemma in grades:self.assertEqual(grades[lemma], token['level'], lemma)
                    grades[lemma] = token['level']
        self.assertGreater(len(grades), 50)
