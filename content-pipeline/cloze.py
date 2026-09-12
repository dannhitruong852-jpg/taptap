"""Restore explicitly marked cloze blanks; absence of evidence is a hard stop."""
import re

class NeedsAnswerKey(ValueError):
    pass


def fill_cloze(article_text, answers, choices):
    answers = {int(k): v for k, v in answers.items()}
    choices = {int(k): v for k, v in choices.items()}
    pattern = re.compile(r'\{\{(\d+)\}\}')
    numbers = [int(n) for n in pattern.findall(article_text)]
    if len(set(numbers)) != len(numbers):
        raise ValueError('Duplicate cloze blank')
    if set(answers) - set(numbers):
        raise ValueError('Answer key contains blanks not present in the article')
    for n in numbers:
        if n not in answers or answers[n] not in choices.get(n, {}):
            raise NeedsAnswerKey(f'needs_answer_key: blank {n}')
        if not isinstance(choices[n][answers[n]], str) or not choices[n][answers[n]].strip():
            raise NeedsAnswerKey(f'Empty selected choice: blank {n}')
    return pattern.sub(lambda m: choices[int(m[1])][answers[int(m[1])]], article_text)
