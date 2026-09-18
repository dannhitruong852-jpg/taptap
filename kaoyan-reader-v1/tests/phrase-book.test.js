import test from 'node:test';
import assert from 'node:assert/strict';
import {resolvePhraseSnippet, createPhraseBookStore} from '../phrase-book.js';

const zh = '\u8fd9\u9879\u653f\u7b56\u53ef\u80fd\u4f1a\u4ee5\u727a\u7272\u89c4\u6a21\u8f83\u5c0f\u7684\u4f01\u4e1a\u4e3a\u4ee3\u4ef7\uff0c\u6765\u6362\u53d6\u66f4\u9ad8\u7684\u6548\u7387\u3002';
const en = 'The policy may come at the expense of smaller firms, in exchange for greater efficiency.';
const words = [...en.matchAll(/[A-Za-z]+/g)].map(m=>({char_start:m.index,char_end:m.index+m[0].length}));

function range(text, needle){ const start=text.indexOf(needle); return [start,start+needle.length]; }

test('semantic spans are the first choice for a selected phrase',()=>{
  const [start,end]=range(en,'at the expense of');
  const snippet='\u4ee5\u727a\u7272\u89c4\u6a21\u8f83\u5c0f\u7684\u4f01\u4e1a\u4e3a\u4ee3\u4ef7';
  const zs=zh.indexOf(snippet);
  const result=resolvePhraseSnippet({sentence:{en,zh},selectionStart:start,selectionEnd:end,words,semanticGroups:[{en_word_start:4,en_word_end:8,zh_char_start:zs,zh_char_end:zs+snippet.length}],bilingualPairs:[]});
  assert.equal(result.text,snippet);
  assert.equal(result.source,'semantic');
});

test('bilingual mapping is used when no semantic span covers the selection',()=>{
  const [start,end]=range(en,'efficiency');
  const snippet='\u6548\u7387';
  const zs=zh.indexOf(snippet);
  const result=resolvePhraseSnippet({sentence:{en,zh},selectionStart:start,selectionEnd:end,words:[],semanticGroups:[],bilingualPairs:[{en_start:start,en_end:end,zh_spans:[{start:zs,end:zs+snippet.length,text:snippet}]}]});
  assert.equal(result.text,snippet);
  assert.equal(result.source,'bilingual');
});

test('fallback returns a nearby Chinese clause rather than the full sentence',()=>{
  const [start,end]=range(en,'greater');
  const result=resolvePhraseSnippet({sentence:{en,zh},selectionStart:start,selectionEnd:end,words:[],semanticGroups:[],bilingualPairs:[]});
  assert.notEqual(result.text,zh);
  assert.match(result.text,/\u6362\u53d6\u66f4\u9ad8\u7684\u6548\u7387/);
  assert.equal(result.source,'context-clause');
});

function memoryStorage(){
  const map=new Map();
  return {getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k)};
}

test('phrase book persists, deduplicates same source phrase, deletes, and remembers blur state',()=>{
  const storage=memoryStorage();
  const store=createPhraseBookStore({storage});
  const base={selectedText:'at the expense of',translationSnippet:'x',sourceSentence:en,sourceSentenceZh:zh,sentenceId:'s01',articleId:'2002-text1',articleTitle:'Text 1',year:2002,selectionStart:20,selectionEnd:37,createdAt:1};
  assert.equal(store.add(base).added,true);
  assert.equal(store.add({...base,createdAt:2}).added,false);
  assert.equal(store.list().length,1);
  store.setBlurred(true);
  assert.equal(createPhraseBookStore({storage}).getBlurred(),true);
  const id=store.list()[0].id;
  assert.equal(store.remove(id),true);
  assert.equal(store.list().length,0);
});
