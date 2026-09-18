import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createTapArbiter} from '../reader-controls.js';

function harness(){
  let now=0;
  let nextId=1;
  const jobs=new Map();
  const setTimer=(fn,delay)=>{const id=nextId++;jobs.set(id,{at:now+delay,fn});return id;};
  const clearTimer=id=>jobs.delete(id);
  const advance=ms=>{
    const target=now+ms;
    while(true){
      const due=[...jobs.entries()].filter(([,job])=>job.at<=target).sort((a,b)=>a[1].at-b[1].at)[0];
      if(!due)break;
      now=due[1].at;
      jobs.delete(due[0]);
      due[1].fn();
    }
    now=target;
  };
  return {now:()=>now,setTimer,clearTimer,advance};
}

test('first tap is delayed and same-card second tap cancels single then fires double once',()=>{
  const h=harness();
  const actions=[];
  const arbiter=createTapArbiter({delay:300,now:h.now,setTimer:h.setTimer,clearTimer:h.clearTimer});
  arbiter.tap('4',{single:()=>actions.push('single-4'),double:()=>actions.push('double-4')});
  assert.deepEqual(actions,[],'first tap must not reveal translation immediately');
  h.advance(180);
  arbiter.tap('4',{single:()=>actions.push('single-4b'),double:()=>actions.push('double-4')});
  assert.deepEqual(actions,['double-4']);
  h.advance(500);
  assert.deepEqual(actions,['double-4'],'cancelled single must never fire after double tap');
});

test('single tap fires once after the double-tap window',()=>{
  const h=harness();
  const actions=[];
  const arbiter=createTapArbiter({delay:280,now:h.now,setTimer:h.setTimer,clearTimer:h.clearTimer});
  arbiter.tap('2',{single:()=>actions.push('single-2'),double:()=>actions.push('double-2')});
  h.advance(279);
  assert.deepEqual(actions,[]);
  h.advance(1);
  assert.deepEqual(actions,['single-2']);
});

test('tap on another card does not become a double tap and preserves both singles',()=>{
  const h=harness();
  const actions=[];
  const arbiter=createTapArbiter({delay:300,now:h.now,setTimer:h.setTimer,clearTimer:h.clearTimer});
  arbiter.tap('1',{single:()=>actions.push('single-1'),double:()=>actions.push('double-1')});
  h.advance(100);
  arbiter.tap('2',{single:()=>actions.push('single-2'),double:()=>actions.push('double-2')});
  assert.deepEqual(actions,['single-1']);
  h.advance(300);
  assert.deepEqual(actions,['single-1','single-2']);
});

test('reader wiring routes pointer double tap to existing speak() and prevents mobile double-tap zoom',()=>{
  const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
  const css=readFileSync(new URL('../styles.css',import.meta.url),'utf8');
  assert.match(app,/createTapArbiter/);
  assert.match(app,/addEventListener\('pointerup'/);
  assert.match(app,/tapArbiter\.tap\(card\.dataset\.index/);
  assert.match(app,/double:\(\)=>\{[\s\S]*?speak\(Number\(card\.dataset\.index\),\{scroll:false\}\)/);
  assert.match(css,/\.sentence-content\s*\{[^}]*touch-action\s*:\s*manipulation/s);
});
