import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveLinkedHighlight, snippetFromRanges, semanticGroupsForYear, localStudyGloss, browserStudyGloss, createInlineHighlightStore} from '../inline-phrase-highlights.js';

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


test('user-edited study gloss persists without changing linked Chinese ranges',()=>{
  const memory=new Map();
  const storage={
    getItem:key=>memory.has(key)?memory.get(key):null,
    setItem:(key,value)=>memory.set(key,value)
  };
  const base={year:2008,articleId:'2008-cloze',sentenceId:'s13',enStart:4,enEnd:14,selectedText:'put down to',studyGloss:'原释义',zhRanges:[{start:0,end:3}],source:'semantic'};
  const store=createInlineHighlightStore({storage});
  store.add(base);
  store.add({...base,studyGloss:'归因于；认为……是由……造成的',glossSource:'user-edited'});
  const reopened=createInlineHighlightStore({storage});
  const saved=reopened.listYear(2008)[0];
  assert.equal(saved.studyGloss,'归因于；认为……是由……造成的');
  assert.equal(saved.glossSource,'user-edited');
  assert.deepEqual(saved.zhRanges,[{start:0,end:3}]);
});
