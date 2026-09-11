import unittest
from qa import normalized_wer, pace_check, needs_cinematic_review


class QATests(unittest.TestCase):
    def test_normalized_wer_ignores_case_and_punctuation(self):
        self.assertEqual(normalized_wer('Who is that?', 'who is that'), 0.0)

    def test_normalized_wer_detects_substitution(self):
        self.assertAlmostEqual(normalized_wer('Who is that?', 'Who was that?'), 1 / 3)

    def test_pace_check_flags_extreme_speed(self):
        self.assertFalse(pace_check(word_count=30, duration_seconds=4.0)['pass'])
        self.assertTrue(pace_check(word_count=30, duration_seconds=12.0)['pass'])

    def test_cinematic_review_targets_strong_or_character_performance(self):
        self.assertTrue(needs_cinematic_review('ironic', 2, 'st-peter'))
        self.assertFalse(needs_cinematic_review('neutral', 0, 'narrator'))


if __name__ == '__main__':
    unittest.main()
