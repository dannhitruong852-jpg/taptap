import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const doc = JSON.parse(fs.readFileSync(new URL('../content/2002/text1.json', import.meta.url)));
const allowedEmotions = new Set(['neutral','warm','lively','serious','curious','ironic','tense','emotional']);

test('2002 Text 1 has 21 complete sentences and valid B2 segments', () => {
  assert.equal(doc.article.year, 2002);
  assert.equal(doc.article.section, 'Text 1');
  assert.equal(doc.sentences.length, 21);
  for (const sentence of doc.sentences) {
    assert.ok(sentence.en.length > 0);
    assert.ok(sentence.zh.length > 0);
    assert.ok(sentence.segments.length > 0);
    for (const segment of sentence.segments) {
      assert.match(segment.id, /^s\d{2}-[a-z]$/);
      assert.ok(['05','12','13'].includes(segment.actor_id));
      assert.ok(allowedEmotions.has(segment.emotion));
      assert.ok([0,1,2].includes(segment.intensity));
      assert.ok(segment.rate >= 0.80 && segment.rate <= 1.05);
    }
  }
});

test('sentences 9 and 10 use intra-sentence B2 role switching', () => {
  assert.deepEqual(doc.sentences[8].segments.map(s => s.actor_id), ['12','05']);
  assert.deepEqual(doc.sentences[9].segments.map(s => s.actor_id), ['13','05','13']);
  assert.equal(doc.sentences[9].segments[2].emotion, 'ironic');
  assert.equal(doc.sentences[9].segments[2].intensity, 2);
});
