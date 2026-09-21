import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveLinkedHighlight, snippetFromRanges, semanticGroupsForYear, localStudyGloss, browserStudyGloss, createInlineHighlightStore, mergeInlineHighlightSnapshots} from '../inline-phrase-highlights.js';

const sentence={
  en:'He helped popularize the idea that some diseases not previously thought to have a bacterial cause were actually infections, which aroused much controversy when it was first suggested.',
  zh:'他曾推动一种观点广为人知：一些过去并不认为由细菌引起的疾病，其实属于感染性疾病；这一观点刚提出时曾引发很大争议。'
};
const pairs=[
  {en_start:130,en_end:137,en_text:'aroused',zh_spans:[{start:49,end:51,text:'引发'}]},
  {en_start:143,en_end:154,en_text:'controversy',zh_spans:[{start:53,end:55,text:'争议'}]}
];

test('semantic groups are rejected when the semantic document year differs from the selected exam year',()=>{
  const wrong={year:2002,articles:{cloze:{s04:[{en_word_start:0,en_word_end:8,zh_char_start:0,zh_char_end:17}]}}};
  assert.deepEqual(semanticGroupsForYear(wrong,2008,'cloze'),{});
});

test('full phrase selection bridges nearby reviewed Chinese anchors into one natural phrase',()=>{
  const linked=resolveLinkedHighlight({sentence,selectionStart:130,selectionEnd:154,bilingualPairs:pairs});
  assert.equal(linked.source,'bilingual-context');
  assert.deepEqual(linked.zhRanges,[{start:49,end:55}]);
  assert.equal(snippetFromRanges(sentence.zh,linked.zhRanges),'引发很大争议');
});

test('context bridge never crosses Chinese punctuation',()=>{
  const s={en:'alpha much omega',zh:'甲，很多乙'};
  const p=[
    {en_start:0,en_end:5,zh_spans:[{start:0,end:1,text:'甲'}]},
    {en_start:11,en_end:16,zh_spans:[{start:4,end:5,text:'乙'}]}
  ];
  const linked=resolveLinkedHighlight({sentence:s,selectionStart:0,selectionEnd:16,bilingualPairs:p});
  assert.deepEqual(linked.zhRanges,[{start:0,end:1},{start:4,end:5}]);
});

test('coarse semantic groups are rejected when they would paint much broader Chinese text than the selection',()=>{
  const s={en:'one two three four five six',zh:'甲乙丙丁戊己'};
  const words=[
    {char_start:0,char_end:3},{char_start:4,char_end:7},{char_start:8,char_end:13},
    {char_start:14,char_end:18},{char_start:19,char_end:23},{char_start:24,char_end:27}
  ];
  const groups=[{en_word_start:0,en_word_end:6,zh_char_start:0,zh_char_end:6}];
  const linked=resolveLinkedHighlight({sentence:s,selectionStart:14,selectionEnd:23,words,semanticGroups:groups});
  assert.equal(linked.source,'none');
  assert.deepEqual(linked.zhRanges,[]);
});


test('local study gloss uses vocabulary meaning without creating Chinese highlight ranges',()=>{
  const en='The plan fell short of expectations.';
  const phrase='fell short of expectations';const start=en.indexOf(phrase);
  const sentence={en,zh:'这项计划的结果比人们原先设想的更差。',vocab:[{start,end:start+phrase.length,meaning:'未达到预期'}]};
  const gloss=localStudyGloss({sentence,selectionStart:start,selectionEnd:start+phrase.length});
  assert.deepEqual(gloss,{text:'未达到预期',source:'vocabulary'});
  const linked=resolveLinkedHighlight({sentence,selectionStart:start,selectionEnd:start+phrase.length});
  assert.deepEqual(linked.zhRanges,[]);
});

test('local study gloss can synthesize a contextual Chinese clause without promoting it to zhRanges',()=>{
  const s={en:'alpha middle omega',zh:'甲，中间意思，乙'};
  const gloss=localStudyGloss({sentence:s,selectionStart:6,selectionEnd:12});
  assert.ok(gloss.text);
  assert.equal(gloss.source,'sentence-context-generated');
});

test('browser study gloss uses the browser Translator API when available',async()=>{
  let destroyed=false;
  const TranslatorApi={create:async options=>{
    assert.equal(options.sourceLanguage,'en');assert.equal(options.targetLanguage,'zh');
    return {translate:async input=>input==='fall short of expectations'?'未达到预期':'',destroy:()=>{destroyed=true;}};
  }};
  const gloss=await browserStudyGloss('fall short of expectations',{TranslatorApi});
  assert.equal(gloss,'未达到预期');assert.equal(destroyed,true);
});

test('marking the same phrase can upgrade an older entry with a generated study gloss',()=>{
  const store=createInlineHighlightStore();
  const base={year:2014,articleId:'2014-text1',sentenceId:'s03',enStart:1,enEnd:5,selectedText:'test'};
  assert.equal(store.add(base).added,true);
  const updated=store.add({...base,studyGloss:'测试',glossSource:'browser-translator'});
  assert.equal(updated.added,false);assert.equal(updated.updated,true);
  assert.equal(store.listYear(2014)[0].studyGloss,'测试');
});


test('cloud merge keeps the newer edit for the same phrase signature',()=>{
  const base={year:2014,articleId:'2014-text1',sentenceId:'s03',enStart:1,enEnd:5,selectedText:'test',createdAt:10};
  const merged=mergeInlineHighlightSnapshots(
    [{...base,studyGloss:'旧释义',updatedAt:20}],
    [{...base,studyGloss:'新释义',updatedAt:30}]
  );
  assert.equal(merged.length,1);
  assert.equal(merged[0].studyGloss,'新释义');
});

test('cloud merge keeps a newer deletion tombstone so deleted phrases do not reappear',()=>{
  const base={year:2014,articleId:'2014-text1',sentenceId:'s03',enStart:1,enEnd:5,selectedText:'test',createdAt:10};
  const merged=mergeInlineHighlightSnapshots(
    [{...base,studyGloss:'测试',updatedAt:20}],
    [{...base,studyGloss:'测试',updatedAt:40,deletedAt:40}]
  );
  assert.equal(merged.length,1);
  assert.equal(merged[0].deletedAt,40);
});

test('store merge preserves offline additions and hides tombstoned entries from the visible phrase book',()=>{
  let clock=100;
  const store=createInlineHighlightStore({now:()=>++clock});
  const local={year:2014,articleId:'2014-text1',sentenceId:'s03',enStart:1,enEnd:5,selectedText:'local'};
  const remote={year:2014,articleId:'2014-text2',sentenceId:'s04',enStart:2,enEnd:8,selectedText:'remote',createdAt:90,updatedAt:90};
  store.add(local);
  store.merge([remote]);
  assert.deepEqual(store.listYear(2014).map(x=>x.selectedText).sort(),['local','remote']);
  store.remove(local);
  assert.deepEqual(store.listYear(2014).map(x=>x.selectedText),['remote']);
  assert.equal(store.snapshot().some(x=>x.selectedText==='local'&&x.deletedAt),true);
});


test('phrase book lists newly added phrases first and editing an older phrase does not reorder it',()=>{
  let clock=1000;
  const store=createInlineHighlightStore({now:()=>++clock});
  const older={year:2026,articleId:'2026-text1',sentenceId:'s01',enStart:0,enEnd:5,selectedText:'older phrase',studyGloss:'旧释义'};
  const newer={year:2026,articleId:'2026-text1',sentenceId:'s02',enStart:6,enEnd:11,selectedText:'newer phrase',studyGloss:'新释义'};
  store.add(older);
  store.add(newer);

  assert.deepEqual(store.listYear(2026).map(x=>x.selectedText),['newer phrase','older phrase']);

  store.add({...older,studyGloss:'修改后的旧释义',glossSource:'user-edited'});

  const visible=store.listYear(2026);
  assert.deepEqual(visible.map(x=>x.selectedText),['newer phrase','older phrase']);
  assert.equal(visible[1].studyGloss,'修改后的旧释义');
  assert.ok(visible[0].createdAt>visible[1].createdAt);
});
