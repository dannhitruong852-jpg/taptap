const STATE_KEY='__kaoyanUiLayer';

function cloneState(state){
  return state && typeof state==='object' && !Array.isArray(state) ? {...state} : {};
}

export function createUiLayerHistory({history,location,layer,isOpen,closeDirect,currentUrl}){
  const ownsCurrentEntry=()=>history?.state?.[STATE_KEY]===layer;
  const open=()=>{
    if(ownsCurrentEntry())return false;
    const nextState=cloneState(history?.state);
    nextState[STATE_KEY]=layer;
    history.pushState(nextState,'',location.href);
    return true;
  };
  const requestClose=()=>{
    if(!isOpen())return false;
    if(ownsCurrentEntry()){
      history.back();
      return true;
    }
    closeDirect();
    return true;
  };
  const handlePopState=()=>{
    if(!isOpen())return false;
    closeDirect();
    const url=currentUrl?.();
    if(url)history.replaceState(history.state,'',url);
    return true;
  };
  return {open,requestClose,handlePopState,ownsCurrentEntry};
}
