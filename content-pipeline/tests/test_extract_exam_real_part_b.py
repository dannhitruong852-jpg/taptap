import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('extract_exam', ROOT / 'extract_exam.py')
extract_exam = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_exam)


class RealPartBRegressionTests(unittest.TestCase):
    def test_trailing_multiline_candidate_options_are_fully_excluded(self):
        text = '''Section I Use of English
Directions:
CLOZE.
1. [A] x
Section II Reading Comprehension
Part A
Text 1
READING.
21. Question?
[A] x
Part B
Directions:
Read the following text and choose from the list.
First article paragraph.
(41)____________________
Second article paragraph.
(42)____________________
Final article paragraph.
(45)____________________
[A] Candidate A first line.
    Candidate A continuation.
[B] Candidate B first line.
    Candidate B continuation.
[G] Candidate G first line.
    Candidate G continuation one.
    Candidate G continuation two.
Part C
Directions:
TRANSLATION BODY.
Section III Writing
WRITING.'''
        body = extract_exam.extract_sections(text, 2005)['part_b'][0]
        self.assertIn('First article paragraph', body)
        self.assertIn('Final article paragraph', body)
        self.assertNotIn('Candidate A', body)
        self.assertNotIn('Candidate G', body)
        self.assertNotIn('continuation two', body)

    def test_parenthesized_numbered_blanks_are_removed_from_part_b(self):
        text = '''Section I Use of English
Directions:
CLOZE.
1. [A] x
Section II Reading Comprehension
Part A
Text 1
READING.
21. Question?
[A] x
Part B
Directions:
Read the following text.
First paragraph.
(41)____________________
Second paragraph.
( 4 2 )____________________
Final paragraph.
Part C
Directions:
TRANSLATION.
Section III Writing
WRITING.'''
        body = extract_exam.extract_sections(text, 2005)['part_b'][0]
        self.assertNotIn('(41)', body)
        self.assertNotIn('( 4 2 )', body)
        self.assertIn('Second paragraph', body)


if __name__ == '__main__':
    unittest.main()
