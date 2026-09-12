import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const controls = await import('../reader-controls.js').catch(() => ({}));
const text = await import('../bilingual-text.js').catch(() => ({}));

test('speed menu exposes exactly the four approved rates', () => {
  assert.equal(typeof controls.snapSpeed, 'function', 'four-stop speed controller is missing');
  assert.deepEqual(controls.SPEED_STOPS, [0.7, 1, 1.3, 1.7]);
  for (const [input, expected] of [[-2,.7],[.83,.7],[.91,1],[1.18,1.3],[1.49,1.3],[1.6,1.7],[4,1.7]]) {
    assert.equal(controls.snapSpeed(input), expected);
  }
  assert.equal(controls.formatSpeed(.7),'0.7×');
  assert.equal(controls.formatSpeed(1),'1.0×');
  assert.equal(controls.formatSpeed(1.3),'1.3×');
  assert.equal(controls.formatSpeed(1.7),'1.7×');
});

test('tap detection rejects long presses, selection, scrolling and cancelled pointers', () => {
  assert.equal(typeof controls.createTapGuard, 'function', 'native-selection-safe tap guard is missing');
  let now=0;
  const guard=controls.createTapGuard({now:()=>now});
  const pointer={pointerId:1,button:0,isPrimary:true,clientX:50,clientY:50};
  guard.down(pointer,'s01',false);now=80;guard.up(pointer);
  assert.equal(guard.accept('s01',false),true);
  guard.down(pointer,'s01',false);now+=600;guard.up(pointer);
  assert.equal(guard.accept('s01',false),false);
  guard.down(pointer,'s01',false);guard.move({...pointer,clientY:75});now+=100;guard.up(pointer);
  assert.equal(guard.accept('s01',false),false);
  guard.down(pointer,'s01',true);now+=80;guard.up(pointer);
  assert.equal(guard.accept('s01',false),false);
  guard.down(pointer,'s01',false);guard.cancel();guard.up(pointer);
  assert.equal(guard.accept('s01',false),false);
  guard.down(pointer,'s01',false);now+=80;guard.up(pointer);
  assert.equal(guard.accept('s02',false),false);
});
test('bilingual renderer uses occurrence-specific Chinese ranges and never changes plain text', () => {
  assert.equal(typeof text.renderChinese, 'function', 'bound Chinese vocabulary renderer is missing');
  const sentence={en:'sympathy',zh:'也认同他们的看法',vocab:[{word:'sympathy',start:0,end:8,level:6}]};
  const pairs=[{en_start:0,en_end:8,en_text:'sympathy',zh_spans:[{start:1,end:3,text:'认同'}]}];
  const html=text.renderChinese(sentence,pairs);
  assert.match(html,/class="vocab zh-vocab"/);
  assert.match(html,/data-pair="0:8"/);
  assert.equal(html.replace(/<[^>]+>/g,''),sentence.zh);
  assert.equal(text.renderChinese(sentence,[{...pairs[0],zh_spans:[{start:0,end:2,text:'错误'}]}]).includes('zh-vocab'),false);
});
test('every project 6-9 vocabulary occurrence in all six articles has a reviewed Chinese match', () => {
  let mappings;
  try { mappings=JSON.parse(readFileSync(new URL('../content/2002/bilingual-highlights.json',import.meta.url))); } catch {}
  assert.ok(mappings?.articles,'reviewed bilingual mappings are missing');
  for (const name of ['cloze','text1','text2','text3','text4','translation']) {
    const doc=JSON.parse(readFileSync(new URL(`../content/2002/c/${name}.json`,import.meta.url)));
    for (const s of doc.sentences) {
      const expected=(s.vocab||[]).filter(v=>v.level>=6);
      const pairs=mappings.articles[`2002-${name}`]?.[s.id]||[];
      assert.equal(pairs.length,expected.length,`${name}/${s.id} coverage`);
      for(const v of expected){
        const pair=pairs.find(p=>p.en_start===v.start&&p.en_end===v.end);
        assert.equal(pair?.en_text,s.en.slice(v.start,v.end),`${name}/${s.id}/${v.word}`);
        assert.ok(pair.zh_spans.length);
        for(const span of pair.zh_spans){
          assert.ok(Number.isInteger(span.start)&&span.start>=0&&span.end>span.start);
          assert.equal(s.zh.slice(span.start,span.end),span.text);
        }
      }
    }
  }
});

test('reordered Chinese clauses link repeated vocabulary to the right occurrence', () => {
 const data=JSON.parse(readFileSync(new URL('../content/2002/bilingual-highlights.json',import.meta.url)));
 const pairs=data.articles['2002-text4'].s08;
 assert.equal(pairs.find(p=>p.en_start===51).zh_spans[0].start,32);
 assert.equal(pairs.find(p=>p.en_start===93).zh_spans[0].start,20);
});

test('English timing tokens preserve exact text and source offsets', () => {
  const sentence={en:"Don't re-enter 20th-century rooms.",zh:'',vocab:[]};
  const html=text.renderEnglish(sentence);
  assert.equal(html.replace(/<[^>]+>/g,''),sentence.en);
  assert.match(html,/data-char-start="0" data-char-end="5"/);
  assert.match(html,/data-char-start="6" data-char-end="14"/);
});

test('Chinese semantic wrappers coexist with reviewed 6+ vocabulary emphasis', () => {
  const sentence={en:'sympathy matters',zh:'也认同他们的看法',vocab:[{word:'sympathy',start:0,end:8,level:6}]};
  const pairs=[{en_start:0,en_end:8,en_text:'sympathy',zh_spans:[{start:1,end:3,text:'认同'}]}];
  const groups=[
    {id:'g01',en_word_start:0,en_word_end:1,zh_char_start:0,zh_char_end:3},
    {id:'g02',en_word_start:1,en_word_end:2,zh_char_start:3,zh_char_end:sentence.zh.length},
  ];
  const html=text.renderChinese(sentence,pairs,groups);
  assert.equal((html.match(/semantic-group/g)||[]).length,2);
  assert.match(html,/class="vocab zh-vocab"/);
  assert.equal(html.replace(/<[^>]+>/g,''),sentence.zh);
});
