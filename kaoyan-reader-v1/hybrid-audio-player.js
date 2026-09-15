export function createHybridAudioPlayer({getWebPlayer,fallbackPlayer}={}){
  if(typeof getWebPlayer!=='function')throw new Error('web-player-provider-required');
  if(!fallbackPlayer)throw new Error('fallback-player-required');
  let active=fallbackPlayer;
  let engine='fallback';

  async function playSentence(queue,rate=1){
    const web=getWebPlayer();
    if(web){
      try{
        await web.playSentence(queue,rate);
        active=web;engine='web';return true;
      }catch{}
    }
    active=fallbackPlayer;engine='fallback';
    await Promise.resolve(fallbackPlayer.playSentence(queue,rate));
    return false;
  }
  function stop(){
    const web=getWebPlayer();
    try{web?.stop?.();}catch{}
    try{fallbackPlayer.stop?.();}catch{}
    active=fallbackPlayer;engine='fallback';
  }
  function pause(){return active?.pause?.();}
  function resume(){return active?.resume?.();}
  function setPlaybackRate(rate){return active?.setPlaybackRate?.(rate);}
  function getState(){return {...(active?.getState?.()||{}),engine};}
  return {playSentence,stop,pause,resume,setPlaybackRate,getState};
}
