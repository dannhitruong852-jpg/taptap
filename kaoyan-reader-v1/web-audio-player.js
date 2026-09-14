export function createWebAudioPlayer({
  audioContext,
  resolveDecoded,
  onSegmentStart=()=>{},
  onTimeUpdate=()=>{},
  onSentenceEnd=()=>{},
  onError=()=>{},
  schedule=fn=>requestAnimationFrame(fn),
  cancelSchedule=id=>cancelAnimationFrame(id)
}={}){
  if(!audioContext?.createBufferSource)throw new Error('audio-context-required');
  if(typeof resolveDecoded!=='function')throw new Error('decoded-resolver-required');
  let source=null,queue=[],index=-1,speed=1,generation=0;
  let logicalOffset=0,startedAtContextTime=0,activeDuration=0,paused=false,playing=false;
  let progressHandle=null,suppressEnded=false,activeSegment=null,activeBuffer=null;

  function clearProgress(){if(progressHandle!==null){cancelSchedule(progressHandle);progressHandle=null;}}
  function mediaTime(){
    if(!playing)return logicalOffset;
    const elapsed=Math.max(0,Number(audioContext.currentTime||0)-startedAtContextTime);
    return Math.min(activeDuration,logicalOffset+elapsed*speed);
  }
  function emitProgress(ended=false){
    if(!activeSegment)return;
    onTimeUpdate({segment:activeSegment,index,currentTime:ended?activeDuration:mediaTime(),duration:activeDuration,ended});
  }
  function scheduleProgress(currentGeneration){
    clearProgress();
    const tick=()=>{
      if(currentGeneration!==generation||!playing)return;
      emitProgress(false);
      progressHandle=schedule(tick);
    };
    progressHandle=schedule(tick);
  }
  function stopSource(){
    if(!source)return;
    suppressEnded=true;
    try{source.stop();}catch{}
    source.onended=null;
    source=null;
    suppressEnded=false;
  }
  async function startResolved(segment,nextIndex,currentGeneration,offset=0,knownBuffer=null){
    if(currentGeneration!==generation)return false;
    if(audioContext.state==='suspended'&&audioContext.resume)await audioContext.resume();
    const resolved=knownBuffer?{buffer:knownBuffer}:await resolveDecoded(segment);
    if(currentGeneration!==generation)return false;
    const buffer=resolved?.buffer;
    if(!buffer)throw new Error('decoded-buffer-required');
    index=nextIndex;activeSegment=segment;activeBuffer=buffer;
    activeDuration=Number(buffer.duration||segment.duration_seconds||0);
    logicalOffset=Math.max(0,Math.min(Number(offset)||0,activeDuration||Infinity));
    const nextSource=audioContext.createBufferSource();
    nextSource.buffer=buffer;nextSource.playbackRate.value=speed;nextSource.connect(audioContext.destination);
    source=nextSource;paused=false;playing=true;startedAtContextTime=Number(audioContext.currentTime||0);
    nextSource.onended=()=>{
      if(currentGeneration!==generation||suppressEnded||source!==nextSource)return;
      emitProgress(true);clearProgress();source=null;playing=false;logicalOffset=activeDuration;
      void playAt(index+1,currentGeneration).catch(error=>{if(currentGeneration===generation)onError(error,segment);});
    };
    nextSource.start(0,logicalOffset);
    onSegmentStart(segment,index);
    scheduleProgress(currentGeneration);
    return true;
  }
  async function playAt(nextIndex,currentGeneration){
    if(currentGeneration!==generation)return false;
    if(nextIndex>=queue.length){playing=false;paused=false;source=null;onSentenceEnd();return true;}
    const segment=queue[nextIndex];
    return startResolved(segment,nextIndex,currentGeneration,0,null);
  }
  async function playSentence(nextQueue,playbackRate=1){
    stop();queue=[...(nextQueue||[])];speed=Number(playbackRate)||1;
    const currentGeneration=generation;
    if(queue.length===0){onSentenceEnd();return true;}
    try{return await playAt(0,currentGeneration);}catch(error){if(currentGeneration===generation){playing=false;paused=false;clearProgress();}throw error;}
  }
  function pause(){
    if(!playing||!source)return;
    logicalOffset=mediaTime();playing=false;paused=true;clearProgress();stopSource();
  }
  async function resume(){
    if(!paused||!activeSegment||!activeBuffer)return false;
    const currentGeneration=generation;
    return startResolved(activeSegment,index,currentGeneration,logicalOffset,activeBuffer);
  }
  function stop(){
    generation+=1;clearProgress();stopSource();queue=[];index=-1;logicalOffset=0;activeDuration=0;paused=false;playing=false;activeSegment=null;activeBuffer=null;
  }
  function setPlaybackRate(rate){
    const next=Number(rate)||1;
    if(!playing){speed=next;if(source)source.playbackRate.value=next;return;}
    const offset=mediaTime();const segment=activeSegment;const buffer=activeBuffer;const currentIndex=index;const currentGeneration=generation;
    speed=next;playing=false;clearProgress();stopSource();logicalOffset=offset;
    void startResolved(segment,currentIndex,currentGeneration,offset,buffer).catch(error=>{if(currentGeneration===generation)onError(error,segment);});
  }
  return {playSentence,pause,resume,stop,setPlaybackRate,getState:()=>({index,playing,paused,speed,currentTime:mediaTime()})};
}
