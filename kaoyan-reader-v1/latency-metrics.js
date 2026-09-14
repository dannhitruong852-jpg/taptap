export function measureLatency(label,start,end=performance.now()){
  const duration=Math.max(0,Number(end)-Number(start));
  const result={label:String(label),duration_ms:duration};
  try{
    if(typeof performance!=='undefined'&&typeof performance.measure==='function'){
      performance.measure(String(label),{start:Number(start),end:Number(end)});
    }
  }catch{}
  return result;
}
