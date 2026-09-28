export function copyTextWithFallback(text,{clipboard=globalThis.navigator?.clipboard,legacyCopy=()=>false}={}){
  const value=String(text??'');
  if(!value.trim())return Promise.resolve(false);

  let modernPromise=null;
  try{
    if(clipboard&&typeof clipboard.writeText==='function'){
      modernPromise=Promise.resolve(clipboard.writeText(value)).then(()=>true,()=>false);
    }
  }catch{
    modernPromise=null;
  }

  let legacyOk=false;
  try{legacyOk=Boolean(legacyCopy(value));}catch{}

  if(!modernPromise)return Promise.resolve(legacyOk);
  return modernPromise.then(ok=>Boolean(ok)||legacyOk,()=>legacyOk);
}
