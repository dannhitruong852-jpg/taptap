import test from 'node:test';
import assert from 'node:assert/strict';
import {createUiLayerHistory} from '../ui-history.js';

function fakeHistory(){
  const calls=[];
  const h={state:{base:'kept'},calls,
    pushState(state,_title,url){this.state=state;calls.push(['push',state,url]);},
    back(){calls.push(['back']);this.state={base:'kept'};},
    replaceState(state,_title,url){this.state=state;calls.push(['replace',state,url]);}
  };
  return h;
}

test('opening a UI layer creates one browser-history entry and preserves existing state',()=>{
  const history=fakeHistory();
  let open=false;
  const ctl=createUiLayerHistory({history,location:{href:'https://reader.test/?x=1#2008-a'},layer:'phrase-book',isOpen:()=>open,closeDirect:()=>{open=false;},currentUrl:()=> '#2008-a'});
  ctl.open();
  assert.equal(history.calls.length,1);
  assert.equal(history.calls[0][0],'push');
  assert.deepEqual(history.state,{base:'kept',__kaoyanUiLayer:'phrase-book'});
  ctl.open();
  assert.equal(history.calls.length,1,'reopening must not stack duplicate history entries');
});

test('requesting close pops the owned entry so Android WebView back can consume it',()=>{
  const history=fakeHistory();
  let open=true,closed=0;
  const ctl=createUiLayerHistory({history,location:{href:'https://reader.test/#2008-a'},layer:'phrase-book',isOpen:()=>open,closeDirect:()=>{open=false;closed++;},currentUrl:()=> '#2008-a'});
  ctl.open();
  ctl.requestClose();
  assert.equal(history.calls.at(-1)[0],'back');
  assert.equal(closed,0,'visual close waits for popstate');
  ctl.handlePopState();
  assert.equal(closed,1);
  assert.equal(history.calls.at(-1)[0],'replace');
  assert.equal(history.calls.at(-1)[2],'#2008-a');
});

test('if the history marker is unavailable, close falls back to direct UI dismissal',()=>{
  const history=fakeHistory();
  let open=true,closed=0;
  const ctl=createUiLayerHistory({history,location:{href:'https://reader.test/#2008-a'},layer:'phrase-book',isOpen:()=>open,closeDirect:()=>{open=false;closed++;},currentUrl:()=> '#2008-a'});
  history.state=null;
  assert.equal(ctl.requestClose(),true);
  assert.equal(closed,1);
  assert.equal(history.calls.some(call=>call[0]==='back'),false);
});
