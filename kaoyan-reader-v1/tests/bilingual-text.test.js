import test from 'node:test';
import assert from 'node:assert/strict';
import { renderEnglish } from '../bilingual-text.js';

test('study_gloss is the wordbook meaning independently of Chinese alignment', () => {
  const en='The plan fell short of expectations.';
  const phrase='fell short of expectations';
  const start=en.indexOf(phrase);
  const html=renderEnglish({en,vocab:[{word:phrase,level:7,start,end:start+phrase.length,meaning:'legacy meaning',study_gloss:'未达到预期'}]});
  assert.match(html,/data-meaning="未达到预期"/);
  assert.doesNotMatch(html,/data-meaning="legacy meaning"/);
});
