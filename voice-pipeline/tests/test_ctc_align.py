import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from alignment.ctc_align import align_tokens


class CtcAlignTests(unittest.TestCase):
    def test_repeated_letters_get_monotonic_distinct_frames(self):
        # vocab: blank=0, C=1, O=2, F=3, E=4
        emissions=[
            [0.0,5,0,0,0],
            [5,0,0,0,0],
            [0,0,5,0,0],
            [5,0,0,0,0],
            [0,0,0,5,0],
            [5,0,0,0,0],
            [0,0,0,5,0],
            [0,0,0,0,5],
            [0,0,0,0,5],
        ]
        path=align_tokens(emissions,[1,2,3,3,4,4],blank_id=0)
        frames=[p['frame'] for p in path]
        self.assertEqual(len(frames),6)
        self.assertEqual(frames,sorted(frames))
        self.assertLess(frames[2],frames[3])
        self.assertLess(frames[4],frames[5])

    def test_impossible_alignment_raises(self):
        emissions=[[5,0],[5,0]]
        with self.assertRaisesRegex(ValueError,'alignment failed'):
            align_tokens(emissions,[1,1],blank_id=0)


if __name__=='__main__':
    unittest.main()
