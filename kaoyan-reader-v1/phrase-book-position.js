function numeric(value,fallback=Number.POSITIVE_INFINITY){
  const n=Number(value);return Number.isFinite(n)?n:fallback;
}

function sentenceNumber(sentenceId){
  const match=String(sentenceId||'').match(/^s(\d+)$/i);
  return match?Number(match[1]):Number.POSITIVE_INFINITY;
}

function rankMap(values=[]){
  return new Map(values.map((value,index)=>[String(value),index]));
}

function sentenceRank(sentenceId,order=[]){
  const ranks=rankMap(order);
  const explicit=ranks.get(String(sentenceId));
  return explicit===undefined?sentenceNumber(sentenceId):explicit;
}

function entryKey(entry){
  return [entry?.articleId,entry?.sentenceId,entry?.enStart,entry?.enEnd].join('|');
}

export function sortPhraseEntries(entries,{articleOrder=[],sentenceOrderByArticle={}}={}){
  const articleRanks=rankMap(articleOrder);
  return [...entries].sort((a,b)=>{
    const ar=articleRanks.get(String(a?.articleId));
    const br=articleRanks.get(String(b?.articleId));
    const articleDiff=(ar??Number.POSITIVE_INFINITY)-(br??Number.POSITIVE_INFINITY);
    if(articleDiff)return articleDiff;
    const articleIdDiff=String(a?.articleId||'').localeCompare(String(b?.articleId||''));
    if(articleIdDiff&&ar===undefined&&br===undefined)return articleIdDiff;
    const aOrder=sentenceOrderByArticle?.[a?.articleId]||[];
    const bOrder=sentenceOrderByArticle?.[b?.articleId]||[];
    const sentenceDiff=sentenceRank(a?.sentenceId,aOrder)-sentenceRank(b?.sentenceId,bOrder);
    if(sentenceDiff)return sentenceDiff;
    const sentenceIdDiff=String(a?.sentenceId||'').localeCompare(String(b?.sentenceId||''),undefined,{numeric:true});
    if(sentenceIdDiff)return sentenceIdDiff;
    const startDiff=numeric(a?.enStart)-numeric(b?.enStart);
    if(startDiff)return startDiff;
    const endDiff=numeric(a?.enEnd)-numeric(b?.enEnd);
    if(endDiff)return endDiff;
    return entryKey(a).localeCompare(entryKey(b));
  });
}

export function findNearestPhraseEntry(entries,{articleId,sentenceId,sentenceOrder=[]}={}){
  const sameArticle=sortPhraseEntries(
    entries.filter(entry=>entry?.articleId===articleId),
    {articleOrder:[articleId],sentenceOrderByArticle:{[articleId]:sentenceOrder}}
  );
  if(!sameArticle.length)return null;
  const exact=sameArticle.find(entry=>entry?.sentenceId===sentenceId);
  if(exact)return exact;
  const targetRank=sentenceRank(sentenceId,sentenceOrder);
  if(!Number.isFinite(targetRank))return null;
  let best=null,bestDistance=Number.POSITIVE_INFINITY,bestRank=Number.POSITIVE_INFINITY;
  for(const entry of sameArticle){
    const rank=sentenceRank(entry?.sentenceId,sentenceOrder);
    if(!Number.isFinite(rank))continue;
    const distance=Math.abs(rank-targetRank);
    if(distance<bestDistance||(distance===bestDistance&&rank<bestRank)){
      best=entry;bestDistance=distance;bestRank=rank;
    }
  }
  return best;
}
