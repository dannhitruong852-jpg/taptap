import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from alignment.align_manifests import attach_word_times, validate_word_timeline


class ManifestAlignmentTests(unittest.TestCase):
    def test_word_times_preserve_source_order_and_bounds(self):
        words=[
            {'source':'Hello','char_start':0,'char_end':5,'normalized':'HELLO'},
            {'source':'world','char_start':6,'char_end':11,'normalized':'WORLD'},
        ]
        char_frames=list(range(10))
        out=attach_word_times(words,char_frames,frame_seconds=.1,audio_duration=1.2)
        self.assertEqual([w['word'] for w in out],['Hello','world'])
        self.assertLessEqual(out[-1]['end'],1.28)
        self.assertEqual(validate_word_timeline(out,1.2),[])

    def test_nonmonotonic_timeline_fails(self):
        words=[{'word':'a','start':.4,'end':.6},{'word':'b','start':.2,'end':.3}]
        errors=validate_word_timeline(words,1.0)
        self.assertTrue(any('monotonic' in e for e in errors))

    def test_audio_overrun_beyond_tolerance_fails(self):
        words=[{'word':'a','start':0.0,'end':1.2}]
        errors=validate_word_timeline(words,1.0)
        self.assertTrue(any('duration' in e for e in errors))


if __name__=='__main__':
    unittest.main()
