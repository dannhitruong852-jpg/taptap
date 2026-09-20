const DEFAULT_KEY_STORAGE='kaoyan-phrase-book-sync-key-v1';
export const DEFAULT_SYNC_ENDPOINT='https://beeayqhmdgehnkqzxlwm.supabase.co/functions/v1/phrase-book-sync';

function randomSyncKey(cryptoApi=globalThis.crypto){
  const bytes=new Uint8Array(24);
  cryptoApi.getRandomValues(bytes);
  let binary='';for(const b of bytes)binary+=String.fromCharCode(b);
  const encoded=typeof btoa==='function'?btoa(binary):Buffer.from(bytes).toString('base64');
  return encoded.replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
export function validPhraseBookSyncKey(value){return /^[A-Za-z0-9_-]{32,128}$/.test(String(value||''));}

export function createPhraseBookCloudSync({
  store,
  storage=null,
  fetchFn=globalThis.fetch,
  cryptoApi=globalThis.crypto,
  endpoint=DEFAULT_SYNC_ENDPOINT,
  keyStorage=DEFAULT_KEY_STORAGE,
  delay=700,
  setTimeoutFn=globalThis.setTimeout,
  clearTimeoutFn=globalThis.clearTimeout,
  onMerged=()=>{},
  onStatus=()=>{},
}={}){
  let memoryKey='',timer=null,syncing=false,pending=false;
  function readKey(){
    if(storage){try{const value=storage.getItem(keyStorage);if(validPhraseBookSyncKey(value))return value;}catch{}}
    return validPhraseBookSyncKey(memoryKey)?memoryKey:'';
  }
  function writeKey(value){
    memoryKey=value;
    if(storage){try{storage.setItem(keyStorage,value);}catch{}}
  }
  function ensureKey(){
    const existing=readKey();if(existing)return existing;
    const generated=randomSyncKey(cryptoApi);writeKey(generated);return generated;
  }
  function getKey(){return ensureKey();}
  function setKey(value){
    const normalized=String(value||'').trim();
    if(!validPhraseBookSyncKey(normalized))throw new Error('invalid-sync-key');
    writeKey(normalized);return normalized;
  }
  async function syncNow(){
    if(syncing){pending=true;return {queued:true};}
    if(typeof fetchFn!=='function')return {ok:false,error:'fetch-unavailable'};
    syncing=true;onStatus('syncing');
    try{
      const response=await fetchFn(endpoint,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({syncKey:ensureKey(),entries:store.snapshot()}),
        cache:'no-store',
      });
      if(!response.ok)throw new Error('sync-http-'+response.status);
      const data=await response.json();
      const result=store.merge(Array.isArray(data?.entries)?data.entries:[]);
      if(result.changed)onMerged(result.entries);
      onStatus('synced');return {ok:true,changed:result.changed,entries:result.entries};
    }catch(error){
      onStatus('offline');return {ok:false,error:String(error?.message||error)};
    }finally{
      syncing=false;
      if(pending){pending=false;void syncNow();}
    }
  }
  function schedule(){
    if(timer!==null)clearTimeoutFn(timer);
    timer=setTimeoutFn(()=>{timer=null;void syncNow();},delay);
  }
  return {getKey,setKey,syncNow,schedule};
}
