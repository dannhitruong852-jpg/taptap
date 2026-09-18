import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveLinkedHighlight, snippetFromRanges, semanticGroupsForYear} from '../inline-phrase-highlights.js';

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
