import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveLinkedHighlight, createInlineHighlightStore} from '../inline-phrase-highlights.js';

const en='The policy may come at the expense of smaller firms, in exchange for greater efficiency.';
const zh='这项政策可能会以牺牲规模较小的企业为代价，来换取更高的效率。';
const words=[...en.matchAll(/[A-Za-z]+/g)].map(m=>({char_start:m.index,char_end:m.index+m[0].length}));
const span=(text,needle)=>{const start=text.indexOf(needle);return [start,start+needle.length];};

test('semantic mapping links selected English to the matching Chinese semantic group',()=>{
  const [enStart,enEnd]=span(en,'at the expense of');
  const target='以牺牲规模较小的企业为代价';
  const zhStart=zh.indexOf(target);
  const result=resolveLinkedHighlight({sentence:{en,zh},selectionStart:enStart,selectionEnd:enEnd,words,semanticGroups:[{en_word_start:4,en_word_end:8,zh_char_start:zhStart,zh_char_end:zhStart+target.length}],bilingualPairs:[]});
  assert.equal(result.enStart,enStart);
  assert.equal(result.enEnd,enEnd);
  assert.deepEqual(result.zhRanges,[{start:zhStart,end:zhStart+target.length}]);
  assert.equal(result.source,'semantic');
});

test('bilingual mapping links overlapping words to existing Chinese spans',()=>{
  const [enStart,enEnd]=span(en,'efficiency');
  const target='效率';
  const zhStart=zh.indexOf(target);
  const result=resolveLinkedHighlight({sentence:{en,zh},selectionStart:enStart,selectionEnd:enEnd,words:[],semanticGroups:[],bilingualPairs:[{en_start:enStart,en_end:enEnd,zh_spans:[{start:zhStart,end:zhStart+target.length,text:target}]}]});
  assert.deepEqual(result.zhRanges,[{start:zhStart,end:zhStart+target.length}]);
  assert.equal(result.source,'bilingual');
});

test('fallback links to a nearby Chinese clause instead of the full sentence',()=>{
  const [enStart,enEnd]=span(en,'greater');
  const result=resolveLinkedHighlight({sentence:{en,zh},selectionStart:enStart,selectionEnd:enEnd,words:[],semanticGroups:[],bilingualPairs:[]});
  assert.equal(result.source,'context-clause');
  assert.ok(result.zhRanges[0].end-result.zhRanges[0].start<zh.length);
  assert.match(zh.slice(result.zhRanges[0].start,result.zhRanges[0].end),/换取更高的效率/);
});

function memoryStorage(){const map=new Map();return{getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,String(v))};}

test('inline highlights persist and deduplicate without a phrase-book list',()=>{
  const storage=memoryStorage();
  const store=createInlineHighlightStore({storage});
  const entry={articleId:'2002-text1',sentenceId:'s01',enStart:10,enEnd:20,zhRanges:[{start:3,end:8}],createdAt:1};
  assert.equal(store.add(entry).added,true);
  assert.equal(store.add({...entry,createdAt:2}).added,false);
  assert.equal(createInlineHighlightStore({storage}).list('2002-text1').length,1);
});