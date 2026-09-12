import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from alignment.normalize_transcript import normalize_transcript


class TranscriptNormalizationTests(unittest.TestCase):
    def test_punctuation_is_acoustically_ignored_but_offsets_are_exact(self):
        text="Wait, don't stop."
        words=normalize_transcript(text)
        self.assertEqual([w['source'] for w in words],["Wait","don't","stop"])
        self.assertEqual(text[words[1]['char_start']:words[1]['char_end']],"don't")
        self.assertEqual(words[1]['normalized'],'DONT')

    def test_hyphenated_word_retains_one_source_span(self):
        text='A well-known result matters.'
        words=normalize_transcript(text)
        target=words[1]
        self.assertEqual(target['source'],'well-known')
        self.assertEqual(target['normalized'],'WELLKNOWN')
        self.assertEqual(text[target['char_start']:target['char_end']],'well-known')

    def test_number_expansion_is_deterministic(self):
        words=normalize_transcript('It rose 20 percent in 1960.')
        self.assertEqual(words[2]['normalized'],'TWENTY')
        self.assertEqual(words[5]['normalized'],'NINETEENSIXTY')

    def test_repeated_letters_survive_normalization(self):
        words=normalize_transcript('Coffee feels good.')
        self.assertEqual(words[0]['normalized'],'COFFEE')


if __name__=='__main__':
    unittest.main()
