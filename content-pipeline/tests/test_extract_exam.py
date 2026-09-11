import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    p = ROOT / f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

extract_exam = load('extract_exam')
normalize = load('normalize')


class ExtractExamTests(unittest.TestCase):
    def test_normalize_repairs_wrapped_lines_without_merging_paragraphs(self):
        raw = 'This is a wrapped\nline in one sentence.\n\nNew paragraph starts\nhere.'
        self.assertEqual(normalize.normalize_prose(raw), 'This is a wrapped line in one sentence.\n\nNew paragraph starts here.')

    def test_extracts_2010_plus_target_sections_and_excludes_writing(self):
        text = '''Section I Use of English
Directions:
Read the following text.
CLOZE BODY 1 ___ BODY.
1. [A] a [B] b [C] c [D] d
Section II Reading Comprehension
Part A
Text 1
READING ONE BODY.
21. Question?
[A] option
Text 2
READING TWO BODY.
26. Question?
[A] option
Part B
Directions:
Read the following text.
PART B ARTICLE BODY.
41. Item
[A] choice
Section III Translation
46. Directions:
Translate the following text into Chinese.
TRANSLATION ARTICLE BODY.
Section IV Writing
WRITING MUST NOT APPEAR.'''
        out = extract_exam.extract_sections(text, 2025)
        self.assertIn('CLOZE BODY', out['cloze'][0])
        self.assertEqual(len(out['reading']), 2)
        self.assertIn('READING ONE BODY', out['reading'][0])
        self.assertIn('PART B ARTICLE BODY', out['part_b'][0])
        self.assertIn('TRANSLATION ARTICLE BODY', out['translation'][0])
        joined = '\n'.join(sum(out.values(), []))
        self.assertNotIn('WRITING', joined)
        self.assertNotIn('[A] option', joined)

    def test_extracts_2005_2009_part_b_and_part_c_translation(self):
        text = '''Section I Use of English
Directions:
CLOZE OLD.
1. [A] x
Section II Reading Comprehension
Part A
Text 1
OLD READING.
21. question
[A] x
Part B
Directions:
OLD PART B ARTICLE.
41. heading
[A] choice
Part C
Directions:
Read the following text carefully and then translate the underlined segments into Chinese.
OLD TRANSLATION PASSAGE.
(46) UNDERLINED SENTENCE.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2009)
        self.assertIn('OLD PART B ARTICLE', out['part_b'][0])
        self.assertIn('OLD TRANSLATION PASSAGE', out['translation'][0])
        self.assertNotIn('WRITING', '\n'.join(sum(out.values(), [])))

    def test_pre_2005_part_b_is_translation_not_new_question(self):
        text = '''Section I Use of English
Directions:
OLD CLOZE.
1. [A] x
Section II Reading Comprehension
Part A
Text 1
OLD READING.
21. question
[A] x
Part B
Directions:
Read the following text carefully and then translate the underlined segments into Chinese.
TRANSLATION ONLY.
(41) A SENTENCE.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2002)
        self.assertEqual(out['part_b'], [])
        self.assertIn('TRANSLATION ONLY', out['translation'][0])

    def test_stops_before_duplicate_answer_key_section(self):
        text = '''Section I Use of English
Directions:
REAL CLOZE.
1. [A] x
Section II Reading Comprehension
Part A
Text 1
REAL READING.
21. question
[A] x
Section III Translation
46. Directions:
REAL TRANSLATION.
Section IV Writing
WRITING.
Section I Use of English
1.D 2.A 3.C
Section II Reading Comprehension
ANSWER EXPLANATIONS.'''
        out = extract_exam.extract_sections(text, 2025)
        joined = '\n'.join(sum(out.values(), []))
        self.assertNotIn('ANSWER EXPLANATIONS', joined)

    def test_normalizes_fullwidth_headings_before_matching(self):
        text = '''Ｓｅｃｔｉｏｎ Ｉ Ｕｓｅ ｏｆ Ｅｎｇｌｉｓｈ
Directions:
FULLWIDTH CLOZE.
1. [A] x
Ｓｅｃｔｉｏｎ ＩＩ Ｒｅａｄｉｎｇ Ｃｏｍｐｒｅｈｅｎｓｉｏｎ
Ｐａｒｔ Ａ
Ｔｅｘｔ １
FULLWIDTH READING.
21. Question?
[A] x
Ｐａｒｔ Ｂ
Directions:
Translate the following text.
FULLWIDTH TRANSLATION.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2001)
        self.assertIn('FULLWIDTH CLOZE', out['cloze'][0])
        self.assertIn('FULLWIDTH READING', out['reading'][0])
        self.assertIn('FULLWIDTH TRANSLATION', out['translation'][0])

    def test_tolerates_ocr_spaces_in_use_of_and_text1_heading(self):
        text = '''Section I Use o f English
Directions:
CLOZE.
1. [A] x
Section II Reading Comprehension
Part A
T e x tl
FIRST READING BODY.
21. Question?
[A] x
Text 2
SECOND READING BODY.
26. Question?
[A] x
Part B
Directions:
PART B BODY.
Part C
Directions:
TRANSLATION BODY.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2005)
        self.assertEqual(len(out['reading']), 2)
        self.assertIn('FIRST READING BODY', out['reading'][0])

    def test_part_b_removes_candidate_options_and_numbered_blanks_but_keeps_article(self):
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
[A] Candidate heading one.
[B] Candidate heading two.
[C] Candidate heading three.
ARTICLE TITLE
First article paragraph with useful prose.
41. -----
Second article paragraph must survive.
42. -----
Third article paragraph must survive too.
43. -----
Fourth paragraph.
44. -----
Fifth paragraph.
45. -----
Final paragraph.
Part C
Directions:
TRANSLATION BODY.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2009)
        body = out['part_b'][0]
        self.assertIn('First article paragraph', body)
        self.assertIn('Second article paragraph', body)
        self.assertIn('Final paragraph', body)
        self.assertNotIn('Candidate heading', body)
        self.assertNotIn('41.', body)

    def test_tolerates_section_hi_translation_ocr(self):
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
PART B BODY.
Section HI Translation
46. Directions:
TRANSLATION OCR BODY.
Section IV Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2023)
        self.assertIn('TRANSLATION OCR BODY', out['translation'][0])

    def test_detects_part_b_directions_after_question_40_when_heading_is_missing(self):
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
40. Last reading question?
[A] x
[B] y
Directions:
Read the following text and choose from the list.
[A] Candidate A.
[B] Candidate B.
PART B ARTICLE TITLE
First Part B paragraph.
41. ____
Second Part B paragraph.
42. ____
Final Part B paragraph.
Section III Translation
46. Directions:
TRANSLATION BODY.
Section IV Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2025)
        self.assertEqual(len(out['part_b']), 1)
        self.assertIn('First Part B paragraph', out['part_b'][0])
        self.assertIn('Final Part B paragraph', out['part_b'][0])
        self.assertNotIn('Candidate A', out['part_b'][0])

    def test_cloze_stops_before_spaced_or_corrupted_option_brackets(self):
        for option_row in ('1. [A ] between [B ] before', '1. [AJ between [BJ before'):
            text = f'''Section I Use of English
Directions:
ARTICLE BODY WITH 1 BLANK AND MORE PROSE.
{option_row}
2. [A ] x
Section II Reading Comprehension
Part A
Text 1
READING BODY.
21. Question?
[A ] option
Part B
Directions:
TRANSLATION BODY.
Section III Writing
WRITING.'''
            out = extract_exam.extract_sections(text, 2002)
            self.assertEqual(out['cloze'][0], 'ARTICLE BODY WITH 1 BLANK AND MORE PROSE.')

    def test_reading_stops_at_numbered_question_even_with_spaced_option_brackets(self):
        text = '''Section I Use of English
Directions:
CLOZE.
1. [A ] x
Section II Reading Comprehension
Part A
Text 1
ONLY ARTICLE PROSE SHOULD REMAIN.
21. According to the text, what is true?
[A ] option A
[B ] option B
Part B
Directions:
TRANSLATION BODY.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2002)
        self.assertEqual(out['reading'][0], 'ONLY ARTICLE PROSE SHOULD REMAIN.')

    def test_cloze_stops_when_answer_rows_have_no_space_after_number(self):
        text = '''Section I Use of English
Directions:
REAL CLOZE BODY.
1.[A] first [B] second
2.[A] x
Section II Reading Comprehension
Part A
Text 1
READING.
11. Question
[A ] x
Part B
Directions:
TRANSLATION.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2001)
        self.assertEqual(out['cloze'][0], 'REAL CLOZE BODY.')

    def test_pre_2005_reading_stops_at_question_11_without_question_mark(self):
        text = '''Section I Use of English
Directions:
CLOZE.
1.[A] x
Section II Reading Comprehension
Part A
Text 1
ARTICLE ENDS HERE.
11. The author suggests that the answer is
[A ] option one
[B ] option two
Part B
Directions:
TRANSLATION.
Section III Writing
WRITING.'''
        out = extract_exam.extract_sections(text, 2001)
        self.assertEqual(out['reading'][0], 'ARTICLE ENDS HERE.')


if __name__ == '__main__':
    unittest.main()
