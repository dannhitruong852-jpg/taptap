import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveLinkedHighlight,createInlineHighlightStore} from '../inline-phrase-highlights.js';

const en='The policy may come at the expense of smaller firms, in exchange for greater efficiency.';
const zh='这项政策可能会以牺牲规模较小的企业为代价，来换取更高的效率。';
const span=(text,needle)=>{const start=text.indexOf(needle);return [start,start+needle.length];};
function memoryStorage(){const map=new Map();return{getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k)};}

test('unmapped English never guesses a Chinese clause',()=>{
  const [start,end]=span(en,'greater');
  const result=resolveLinkedHighlight({sentence:{en,zh},selectionStart:start,selectionEnd:end,words:[],semanticGroups:[],bilingualPairs:[]});
  assert.deepEqual(result.zhRanges,[]);
  assert.equal(result.source,'none');
});

test('one stored mark is also a year-book record with its learning context',()=>{
  const store=createInlineHighlightStore({storage:memoryStorage()});
  store.add({year:2002,articleId:'2002-text1',articleTitle:'Text 1',sentenceId:'s1',selectedText:'at the expense of',translationSnippet:'以牺牲……为代价',sourceSentence:en,sourceSentenceZh:zh,enStart:20,enEnd:37,zhRanges:[{start:7,end:18}],createdAt:1});
  const rows=store.listYear(2002);
  assert.equal(rows.length,1);
  assert.equal(rows[0].selectedText,'at the expense of');
  assert.equal(rows[0].translationSnippet,'以牺牲……为代价');
});

test('year books stay separated',()=>{
  const store=createInlineHighlightStore({storage:memoryStorage()});
  store.add({year:2002,articleId:'a',sentenceId:'s1',enStart:1,enEnd:2,createdAt:1});
  store.add({year:2003,articleId:'b',sentenceId:'s2',enStart:1,enEnd:2,createdAt:2});
  assert.equal(store.listYear(2002).length,1);
  assert.equal(store.listYear(2003).length,1);
  assert.deepEqual(store.years(),[2002,2003]);
});

test('translation blur preference is stored independently per year',()=>{
  const storage=memoryStorage();
  const store=createInlineHighlightStore({storage});
  store.setYearBlurred(2002,true);
  assert.equal(store.getYearBlurred(2002),true);
  assert.equal(store.getYearBlurred(2003),false);
});
