import test from 'node:test';
import assert from 'node:assert/strict';
import {createAudioPlayer} from '../audio-player.js';
class FakeAudio {
 constructor(src){this.src=src;this.paused=true;}
 play(){this.paused=false;return Promise.resolve();}
 pause(){this.paused=true;}
}
test('late rejected play from an old selection cannot report an error in a new article',async()=>{
 let rejectOld;const errors=[];let counter=0;
 const player=createAudioPlayer({
  createAudio:src=>{const audio=new FakeAudio(src);if(counter++===0)audio.play=()=>new Promise((_,reject)=>{rejectOld=reject});return audio;},
  onError:error=>errors.push(error)
 });
 player.playSentence([{id:'old',path:'old.opus'}]);player.playSentence([{id:'new',path:'new.opus'}]);
 rejectOld(new Error('old request failed'));await Promise.resolve();assert.equal(errors.length,0);
});
