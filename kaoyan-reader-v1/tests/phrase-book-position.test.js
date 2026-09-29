import test from 'node:test';
import assert from 'node:assert/strict';
import {sortPhraseEntries,findNearestPhraseEntry} from '../phrase-book-position.js';

const entry=(articleId,sentenceId,enStart,createdAt,selectedText)=>({articleId,sentenceId,enStart,enEnd:enStart+2,createdAt,selectedText});

test('phrasebook display order follows catalog article order, sentence order, and source offset',()=>{
  const entries=[
    entry('2008-partb','s19',20,100,'late-in-s19'),
    entry('2008-partb','s05',10,400,'s05'),
    entry('2008-partb','s19',2,300,'early-in-s19'),
    entry('2008-text1','s01',0,500,'next-article')
  ];
  const sorted=sortPhraseEntries(entries,{
    articleOrder:['2008-partb','2008-text1'],
    sentenceOrderByArticle:{'2008-partb':['s01','s05','s19'],'2008-text1':['s01']}
  });
  assert.deepEqual(sorted.map(item=>item.selectedText),['s05','early-in-s19','late-in-s19','next-article']);
});

test('editing timestamps never change phrasebook source order',()=>{
  const entries=[
    {...entry('2008-partb','s05',0,10,'first'),updatedAt:9999},
    entry('2008-partb','s19',0,999,'second')
  ];
  const sorted=sortPhraseEntries(entries,{
    articleOrder:['2008-partb'],
    sentenceOrderByArticle:{'2008-partb':['s05','s19']}
  });
  assert.deepEqual(sorted.map(item=>item.selectedText),['first','second']);
});

test('active sentence targeting chooses its first phrase or the nearest source sentence',()=>{
  const entries=[
    entry('2008-partb','s17',8,1,'s17-b'),
    entry('2008-partb','s17',2,2,'s17-a'),
    entry('2008-partb','s21',0,3,'s21'),
    entry('2008-text1','s19',0,4,'other-article')
  ];
  const sentenceOrder=['s16','s17','s18','s19','s20','s21'];
  assert.equal(findNearestPhraseEntry(entries,{articleId:'2008-partb',sentenceId:'s17',sentenceOrder}).selectedText,'s17-a');
  assert.equal(findNearestPhraseEntry(entries,{articleId:'2008-partb',sentenceId:'s19',sentenceOrder}).selectedText,'s17-a');
});
