import unittest
from cloze import fill_cloze, NeedsAnswerKey

class ClozeTests(unittest.TestCase):
    def test_exact_insertion_preserves_punctuation_and_numbers(self):
        self.assertEqual(fill_cloze('In the 20th century, it was not {{1}} then; {{2}}.', {1:'D', 2:'A'}, {1:{'D':'until'},2:{'A':'in terms of'}}), 'In the 20th century, it was not until then; in terms of.')
    def test_missing_key_is_never_guessed(self):
        with self.assertRaises(NeedsAnswerKey):
            fill_cloze('A {{1}} B {{2}}.', {1:'A'}, {1:{'A':'test'},2:{'B':'word'}})
    def test_missing_choice_is_never_guessed(self):
        with self.assertRaises(NeedsAnswerKey):
            fill_cloze('{{1}}.', {1:'B'}, {1:{'A':'wrong'}})
    def test_duplicate_blanks_rejected(self):
        with self.assertRaises(ValueError):
            fill_cloze('{{1}} {{1}}.', {1:'A'}, {1:{'A':'word'}})
    def test_extra_answers_do_not_silently_disappear(self):
        with self.assertRaises(ValueError):
            fill_cloze('{{1}}', {1:'A',2:'A'}, {1:{'A':'one'},2:{'A':'two'}})
