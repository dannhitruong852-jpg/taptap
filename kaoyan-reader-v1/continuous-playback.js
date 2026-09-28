// Own only the asynchronous handoff between articles; sentence playback stays
// with the existing player. Cancellation prevents late loads from autoplaying.
export function createContinuousPlayback({enabled=false,getNext,open,play,onWaiting=()=>{},onStop=()=>{}}){
 let generation=0,pending=false;
 function cancel(){generation+=1;pending=false;}
 async function finishArticle(){
  if(pending)return;
  if(!enabled){onStop('article');return;}
  const next=getNext();
  if(!next){onStop('end');return;}
  const token=++generation;pending=true;
  try{
   const loading=open(next);onWaiting();
   const loaded=await loading;
   if(token!==generation)return;
   pending=false;
   if(loaded===true&&enabled)play();else onStop('failed');
  }catch{
   if(token!==generation)return;
   pending=false;onStop('failed');
  }
 }
 return {finishArticle,cancel,isPending:()=>pending,
  setEnabled(value){enabled=Boolean(value);if(!enabled)cancel();}
 };
}
