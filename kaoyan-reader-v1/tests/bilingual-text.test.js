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

test('multi-word vocabulary renders as one continuous range that contains its spaces and timing tokens', () => {
  const en='The plan fell short of expectations today.';
  const phrase='fell short of expectations';
  const start=en.indexOf(phrase);
  const html=renderEnglish({en,vocab:[{word:phrase,level:7,start,end:start+phrase.length,study_gloss:'未达到预期'}]});
  assert.equal((html.match(/class="vocab vocab-range"/g)||[]).length,1);
  assert.match(html,/class="vocab vocab-range"[^>]*>.*fell<\/span> <span class="read-token"[^>]*>short<\/span> <span class="read-token"[^>]*>of<\/span> <span class="read-token"[^>]*>expectations<\/span><\/span>/);
  assert.equal(html.replace(/<[^>]+>/g,''),en);
  assert.doesNotMatch(html,/class="read-token vocab"/);
});
