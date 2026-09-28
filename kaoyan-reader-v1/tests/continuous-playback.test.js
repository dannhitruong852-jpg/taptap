import test from 'node:test';
import assert from 'node:assert/strict';
import {createContinuousPlayback} from '../continuous-playback.js';
import {adjacentArticle} from '../catalog.js';

function setup({open, enabled=true}={}){
 const catalog={articles:[{id:'2002-last'},{id:'2003-first'}]};
 let current=catalog.articles[0];const events=[];
 const player=createContinuousPlayback({enabled,
  getNext:()=>adjacentArticle(catalog,current.id,1),
  open:async entry=>{events.push(['open',entry.id]);if(open)await open();current=entry;return true;},
  play:()=>events.push(['play',current.id,0]),
  onWaiting:()=>events.push(['waiting']),
  onStop:reason=>events.push(['stop',reason])
 });
 return {player,events};
}
test('natural article end advances in catalog order across years and starts at sentence zero',async()=>{
 const {player,events}=setup();await player.finishArticle();
 assert.deepEqual(events,[['open','2003-first'],['waiting'],['play','2003-first',0]]);
});
test('disabled continuous playback stops at the current article',async()=>{
 const {player,events}=setup({enabled:false});await player.finishArticle();
 assert.deepEqual(events,[['stop','article']]);
});
test('last article stops without wrapping to the beginning',async()=>{
 const {player,events}=setup();await player.finishArticle();events.length=0;await player.finishArticle();
 assert.deepEqual(events,[['stop','end']]);
});
for(const action of ['cancel','disable'])test(`${action} during next article loading prevents delayed autoplay`,async()=>{
 let release;const {player,events}=setup({open:()=>new Promise(r=>{release=r;})});
 const pending=player.finishArticle();assert.equal(player.isPending(),true);
 if(action==='cancel')player.cancel();else player.setEnabled(false);
 release();await pending;assert.equal(player.isPending(),false);
 assert.equal(events.some(e=>e[0]==='play'),false);
});
test('duplicate end callbacks cannot load or play the next article twice',async()=>{
 let release;const {player,events}=setup({open:()=>new Promise(r=>{release=r;})});
 const pending=player.finishArticle();await player.finishArticle();release();await pending;
 assert.equal(events.filter(e=>e[0]==='open').length,1);
 assert.equal(events.filter(e=>e[0]==='play').length,1);
});
test('failed next article stops and releases pending state',async()=>{
 const {player,events}=setup({open:()=>{throw new Error('offline');}});await player.finishArticle();
 assert.equal(player.isPending(),false);assert.deepEqual(events.at(-1),['stop','failed']);
 assert.equal(events.some(e=>e[0]==='play'),false);
});
test('stale or unsuccessful article selection never starts playback',async()=>{
 let played=false;
 const player=createContinuousPlayback({enabled:true,getNext:()=>({id:'next'}),open:async()=>false,play:()=>{played=true;}});
 await player.finishArticle();assert.equal(played,false);
});
