import test from 'node:test';
import assert from 'node:assert/strict';
import {pickArticle,selectArticles,highlightVocabulary,createSelectionLoader} from '../catalog.js';
const catalog={articles:[{id:'2002-cloze',year:2002,section_type:'cloze'},{id:'2002-text1',year:2002,section_type:'reading'}]};
test('selection filters the real catalog, not fabricated sections',()=>{
 assert.deepEqual(selectArticles(catalog,2002,'reading').map(x=>x.id),['2002-text1']);
 assert.deepEqual(selectArticles(catalog,2002,'part_b'),[]);
 assert.equal(pickArticle(catalog,'missing').id,'2002-cloze');
});
test('vocabulary highlighting respects token boundaries and escapes source HTML',()=>{
 const value=highlightVocabulary('Her capacities match capacity < 9.',[{word:'capacity',level:6,meaning:'storage'}],true);
 assert.equal((value.match(/class="vocab"/g)||[]).length,1);
 assert.ok(value.includes('&lt; 9.'));
 assert.ok(!highlightVocabulary('capacity',[{word:'capacity',level:5}],true).includes('<strong'));
});
test('late article response cannot replace a newer selection',async()=>{
 const pending=new Map();const loader=createSelectionLoader(url=>new Promise(resolve=>pending.set(url,resolve)));
 const old=loader({content:'a',manifest:'am'});const latest=loader({content:'b',manifest:'bm'});
 const resolve=(url,body)=>pending.get(url)({ok:true,json:async()=>body});
 resolve('b',{id:'b'});resolve('bm',{segments:{}});assert.equal((await latest).content.id,'b');
 resolve('a',{id:'a'});resolve('am',{segments:{}});assert.equal(await old,null);
});
test('missing audio manifest does not block reading content',async()=>{
 const loader=createSelectionLoader(async url=>({ok:url==='body',json:async()=>({sentences:[1]})}));
 const result=await loader({content:'body',manifest:'missing'});
 assert.equal(result.content.sentences.length,1);assert.deepEqual(result.manifest.segments,{});
});
