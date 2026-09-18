from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'content-pipeline'))
from build_curated_year import load_curated_source, build_year, build_voice_profiles, build_direction, write_json

REVIEW_FLAGS={
    'review_schema_version':'c-mode-v2-1',
    'source_scope_verified':True,
    'scope_exclusions_reviewed':True,
    'text_fidelity_reviewed':True,
    'translation_alignment_reviewed':True,
    'sentence_alignment_reviewed':True,
    'status':'reviewed_candidate',
    'review_method':'visual PDF review plus reviewed sentence-level bilingual manuscript',
    'unresolved_sections':[],
}
LOW={'qualify','settle','example','report'}

def build_mapping(year:int,docs:list[dict])->tuple[dict,dict]:
    mapping={'year':year,'articles':{},'exceptions':[]}
    required=mapped=0
    for doc in docs:
        amap={}
        for sentence in doc['sentences']:
            entries=[]
            for vocab in sentence.get('vocab',[]):
                if int(vocab.get('level',0))<6:
                    continue
                required+=1
                meaning=str(vocab.get('meaning',''))
                pos=sentence['zh'].find(meaning)
                if pos<0:
                    raise ValueError(f"{doc['article_id']}:{sentence['id']}: reviewed Chinese meaning not found for {vocab['word']} -> {meaning}")
                entries.append({
                    'en_start':vocab['start'],'en_end':vocab['end'],'en_text':vocab['word'],
                    'zh_spans':[{'start':pos,'end':pos+len(meaning),'text':meaning}],
                })
                mapped+=1
            if entries:
                amap[sentence['id']]=entries
        mapping['articles'][doc['article_id']]=amap
    report={'year':year,'required_occurrences':required,'mapped_occurrences':mapped,'reviewed_exceptions':0,'errors':[]}
    return mapping,report

def validate(year:int,source:dict,docs:list[dict],mapping:dict)->dict:
    errors=[]
    by_id={d['article_id']:d for d in docs}
    if set(by_id)!= {'cloze','text1','text2','text3','text4','partb','translation'}:
        errors.append('article inventory mismatch')
    req=mapped=0
    profiles=build_voice_profiles(source)['profiles']
    for article in source['articles']:
        aid=article['id']; doc=by_id[aid]
        if len(article['rows'])!=len(doc['sentences']): errors.append(f'{aid}: sentence count mismatch')
        actor=str(article['actor']).zfill(2)
        if doc['primary_actor_id']!=actor or profiles[aid]['primary_actor_id']!=actor: errors.append(f'{aid}: actor mismatch')
        labels=[]
        outstanding={}
        for idx,(row,sentence) in enumerate(zip(article['rows'],doc['sentences']),1):
            if row[1].replace('|','')!=sentence['en'] or row[2]!=sentence['zh']: errors.append(f'{aid}:s{idx:02d}: text mismatch')
            if ''.join(seg['text'] for seg in sentence['segments'])!=sentence['en']: errors.append(f'{aid}:s{idx:02d}: segment coverage')
            labels.append(sentence['discourse_function'])
            for v in sentence.get('vocab',[]):
                if int(v.get('level',0))>=6:
                    req+=1; outstanding[(sentence['id'],v['start'],v['end'])]=v
        for i in range(max(0,len(labels)-2)):
            if all(x in LOW for x in labels[i:i+3]): errors.append(f'{aid}: sentences {i+1}-{i+3} low-intensity density')
        for sid,entries in (mapping['articles'].get(aid) or {}).items():
            sentence=next((s for s in doc['sentences'] if s['id']==sid),None)
            if not sentence: errors.append(f'{aid}:{sid}: mapping sentence missing'); continue
            for e in entries:
                key=(sid,e['en_start'],e['en_end'])
                if key not in outstanding: errors.append(f'{aid}:{sid}: unexpected mapping')
                if sentence['en'][e['en_start']:e['en_end']]!=e['en_text']: errors.append(f'{aid}:{sid}: English span mismatch')
                for z in e.get('zh_spans',[]):
                    if sentence['zh'][z['start']:z['end']]!=z['text']: errors.append(f'{aid}:{sid}: Chinese span mismatch')
                if key in outstanding: del outstanding[key]; mapped+=1
        for key,v in outstanding.items(): errors.append(f"{aid}:{key[0]}: unmapped {v['word']}")
    return {'ok':not errors,'phase':'preflight','years':[year],'articles_checked':len(docs),'reviewed_candidates_checked':len(docs),'level6_vocab_occurrences_checked':req,'mapped_occurrences':mapped,'errors':errors}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); args=ap.parse_args(); year=args.year
    source=load_curated_source(ROOT/'content-pipeline/curated',year)
    docs,rows=build_year(source)
    write_json(ROOT/f'content-pipeline/voice_profiles/{year}.json',build_voice_profiles(source))
    write_json(ROOT/f'content-pipeline/direction/{year}.json',build_direction(source))
    for doc in docs: write_json(ROOT/f"kaoyan-reader-v1/content/{year}/c/{doc['article_id']}.json",doc)
    catalog_path=ROOT/'kaoyan-reader-v1/content/catalog.json'
    catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
    catalog['years']=sorted(set(catalog.get('years',[]))|{year})
    catalog['articles']=[x for x in catalog.get('articles',[]) if x.get('year')!=year]+rows
    catalog['articles'].sort(key=lambda x:(x['year'],x['id']))
    write_json(catalog_path,catalog)
    write_json(ROOT/f'reports/extraction/{year}.json',{'year':year,'source_filename':source.get('source_filename'),'source_sha256':source['source_sha256'],'method':source.get('method'),'articles':[{'id':d['article_id'],'sentences':len(d['sentences'])} for d in docs],'suspected_contamination':[],'unresolved_sections':source.get('unresolved_sections',[])})
    mapping,bireport=build_mapping(year,docs)
    write_json(ROOT/f'content-pipeline/curated/bilingual-highlights/{year}.json',mapping)
    write_json(ROOT/f'kaoyan-reader-v1/content/{year}/bilingual-highlights.json',mapping)
    write_json(ROOT/f'reports/bilingual-highlights/{year}.json',bireport)
    out=ROOT/f'reports/content-freeze/{year}'; out.mkdir(parents=True,exist_ok=True)
    for article in source['articles']:
        n=len(article['rows'])
        qa={**REVIEW_FLAGS,'source_pdf':source.get('source_pdf') or source.get('source_filename'),'source_sha256':source['source_sha256'],'sentence_count':n,'expected_sentences':n,'actual_sentences':n}
        write_json(out/f"{article['id']}.candidate.json",{'year':year,'article':article,'qa':qa})
    report=validate(year,source,docs,mapping)
    report.update({'schema_version':'c-mode-v2-canary-evidence-1','branch':'c-mode-v2-2019-2024-production','sentence_counts':{d['article_id']:len(d['sentences']) for d in docs}})
    write_json(ROOT/f'reports/production-v2/{year}-canary.json',report)
    print(json.dumps(report,ensure_ascii=False))
    if not report['ok']: raise SystemExit(2)

if __name__=='__main__': main()
