import test from 'node:test';
import assert from 'node:assert/strict';
import {setup,flush} from './helpers/reader-dom.js';

test('actual page plays next articles across years, follows title/selectors, then stops',async()=>{
 const app=await setup();try{
  app.$('#toggle-continuous').click();await app.start();await app.finish();
  assert.deepEqual(app.started,['./a.mp3','./b.mp3']);
  assert.equal(app.$('#article-title').textContent,'b');assert.equal(app.$('#article-select').value,'2002-b');
  await app.finish();assert.equal(app.$('#year-select').value,'2003');
  await app.finish();assert.deepEqual(app.started,['./a.mp3','./b.mp3','./c.mp3']);
  assert.equal(app.$('#play-toggle').dataset.playing,'false');
 }finally{app.close();}
});
test('switch off stops at current article and the preference is stored',async()=>{
 const app=await setup({preference:true});try{
  assert.equal(app.$('#toggle-continuous').getAttribute('aria-checked'),'true');
  app.$('#toggle-continuous').click();assert.equal(app.window.localStorage.getItem('kaoyan-continuous-playback-v1'),'false');
  await app.start();await app.finish();assert.deepEqual(app.started,['./a.mp3']);
 }finally{app.close();}
});
for(const action of ['pause','disable','next','select'])test(`actual page cancels delayed autoplay on ${action}`,async()=>{
 const app=await setup({delayNext:true,preference:true});try{
  await app.start();await app.finish();
  if(action==='pause')app.$('#play-toggle').click();
  if(action==='disable')app.$('#toggle-continuous').click();
  if(action==='next')app.$('#next').click();
  if(action==='select'){
   app.$('#article-select').value='2002-a';app.$('#article-select').dispatchEvent(new app.window.Event('change'));
  }
  await app.release();assert.deepEqual(app.started,['./a.mp3']);
  assert.equal(app.$('#play-toggle').dataset.playing,'false');
 }finally{app.close();}
});
test('manual pause does not advance and resume continues the current audio',async()=>{
 const app=await setup({preference:true});try{
  await app.start();app.$('#play-toggle').click();await flush();
  assert.equal(app.$('#article-select').value,'2002-a');assert.equal(app.$('#play-toggle').dataset.playing,'false');
  await app.start();assert.deepEqual(app.started,['./a.mp3','./a.mp3']);
 }finally{app.close();}
});
