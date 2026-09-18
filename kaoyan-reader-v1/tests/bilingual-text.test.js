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

test('saved phrase highlight renders as one continuous range including spaces', () => {
  const en='Dr. Cochran suggests that the intelligence and diseases are intimately linked.';
  const phrase='suggests that the intelligence and diseases are intimately linked';
  const start=en.indexOf(phrase),end=start+phrase.length;
  const vocab=[
    {word:'suggests',level:6,start,end:start+8,meaning:'认为'},
    {word:'intelligence',level:6,start:en.indexOf('intelligence'),end:en.indexOf('intelligence')+12,meaning:'智力'},
    {word:'diseases',level:6,start:en.indexOf('diseases'),end:en.indexOf('diseases')+8,meaning:'疾病'}
  ];
  const html=renderEnglish({en,vocab},[{start,end}]);
  assert.equal((html.match(/class="phrase-mark-en"/g)||[]).length,1);
  const marked=html.match(/<span class="phrase-mark-en"[^>]*>([\s\S]*?)<\/span>\./)?.[1]||'';
  assert.equal(marked.replace(/<[^>]+>/g,''),phrase);
  assert.match(marked,/suggests/);
  assert.match(marked,/that/);
  assert.match(marked,/intelligence/);
  assert.match(marked,/diseases/);
  assert.match(marked,/intimately/);
  assert.match(marked,/linked/);
  assert.doesNotMatch(html,/class="read-token phrase-mark-en"/);
  assert.equal(html.replace(/<[^>]+>/g,''),en);
});
