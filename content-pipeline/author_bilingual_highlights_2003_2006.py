"""One-time audited authoring data for 2003-2006 bilingual vocabulary highlights.

This script never runs in the browser. It converts reviewed occurrence-specific editorial
choices into canonical JSON, then the strict bilingual_highlights validator verifies all
source offsets before publication.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEARS = (2003, 2004, 2005, 2006)

MANUAL_PHRASES = {
    (2003,'cloze','s04',135,149):'格外在意自我',(2003,'cloze','s06',120,128):'有效互动',(2003,'cloze','s11',40,47):'培养',
    (2003,'text1','s03',77,86):'刺探情报',(2003,'text1','s08',97,108):'影响',(2003,'text1','s10',119,126):'熟练驾驭',
    (2003,'text2','s02',32,42):'生物医学',(2003,'text2','s04',45,55):'生物医学',(2003,'text2','s05',73,82):'困惑',(2003,'text2','s05',101,113):'故意',
    (2003,'text2','s09',28,37):'传染病',(2003,'text2','s11',61,74):'富有同理心',(2003,'text2','s11',136,145):'分子',
    (2003,'text2','s16',112,119):'披上一层',(2003,'text2','s16',122,131):'貌似真实',(2003,'text2','s17',88,94):'人道照护',
    (2003,'text2','s19',74,83):'公众群体',(2003,'text2','s19',89,99):'熄灭',(2003,'text2','s19',113,119):'火种',
    (2003,'text3','s03',29,36):'兼并',(2003,'text3','s03',144,152):'铁路承运商',(2003,'text3','s04',52,59):'兼并',
    (2003,'text3','s06',47,58):'大宗重货',(2003,'text3','s08',33,40):'受制',(2003,'text3','s10',23,37):'差别定价',(2003,'text3','s10',46,53):'受制',
    (2003,'text3','s12',144,152):'兴旺',(2003,'text3','s14',5,12):'受制',(2003,'text3','s15',163,170):'激增',(2003,'text3','s20',5,12):'受制',
    (2003,'text4','s01',56,66):'不可避免',(2003,'text4','s14',29,42):'不可持续',(2003,'text4','s17',81,87):'体弱',
    (2003,'text4','s19',21,30):'常常',(2003,'text4','s19',77,87):'惊人',(2003,'text4','s25',68,79):'无效',(2003,'text4','s27',39,44):'治愈方案',
    (2003,'translation','s02',149,161):'客观冷静',(2003,'translation','s05',96,104):'抽象',(2003,'translation','s05',134,141):'大量',
    (2004,'cloze','s01',155,167):'影响因素',(2004,'cloze','s02',145,153):'过错',(2004,'cloze','s03',126,139):'社会经济',(2004,'cloze','s04',68,81):'弱势',
    (2004,'cloze','s06',27,36):'暂时性',(2004,'cloze','s13',6,18):'可以识别',(2004,'cloze','s13',151,160):'现象',(2004,'cloze','s14',110,116):'因果关系',
    (2004,'text1','s03',58,66):'求职条件',(2004,'text1','s07',109,120):'低效',(2004,'text1','s10',15,23):'搜索条件',(2004,'text1','s13',30,38):'隐含',
    (2004,'text1','s20',62,72):'很有价值',(2004,'text2','s02',8,17):'隐蔽',(2004,'text2','s07',6,18):'可疑',
    (2004,'text2','s13',74,87):'字母排序上吃亏',(2004,'text2','s16',31,44):'字母排序上吃亏',(2004,'text2','s20',149,159):'人们',(2004,'text2','s20',182,196):'费力看下去',
    (2004,'text3','s03',17,26):'经济走软',(2004,'text3','s06',85,93):'郊区',(2004,'text3','s09',53,60):'乏力',(2004,'text3','s10',138,145):'关键时刻',
    (2004,'text3','s13',156,171):'勒紧裤腰带',(2004,'text3','s16',89,102):'主要',(2004,'text3','s17',50,58):'疯狂',(2004,'text3','s20',15,29):'好的一面',(2004,'text3','s23',124,133):'持续繁荣',
    (2004,'text4','s07',162,176):'制衡',(2004,'text4','s09',60,70):'更容易受到利用和控制',(2004,'text4','s15',83,91):'严格',(2004,'text4','s15',120,130):'束缚',
    (2004,'text4','s22',92,102):'斗志昂扬',(2004,'text4','s22',118,127):'敌视',(2004,'translation','s04',146,154):'习惯性思维',(2004,'translation','s05',142,153):'语法模式',(2004,'translation','s05',189,201):'深远影响',
    (2005,'cloze','s02',31,42):'迟钝',(2005,'partb','s02',94,108):'药品',(2005,'partb','s07',22,37):'跨省',(2005,'partb','s20',140,152):'权限范围',
    (2005,'text1','s17',116,126):'心生不满',(2005,'text2','s02',22,34):'尚无定论',(2005,'text2','s12',38,45):'谨慎',(2005,'text2','s18',37,48):'立法',
    (2005,'text3','s09',57,63):'边缘系统',(2005,'text3','s09',127,137):'前额叶',(2005,'text4','s12',209,215):'表达',
    (2006,'cloze','s02',8,20):'无家可归',(2006,'cloze','s13',92,105):'综合',(2006,'partb','s20',86,98):'病理性',(2006,'partb','s21',119,124):'道德失败',
    (2006,'text1','s02',97,106):'恭顺',(2006,'text3','s22',54,65):'可持续',(2006,'translation','s01',142,147):'道德',(2006,'translation','s02',16,25):'类似',
    (2006,'translation','s03',89,94):'道德',(2006,'translation','s04',47,52):'道德准则',(2006,'translation','s05',152,157):'道德判断',
}

# Literal glossary matches that occur more than once in the same Chinese sentence need an
# occurrence-specific reviewed index instead of a generic first-match rule.
POSITION_OVERRIDES = {
    (2004,'text2','s08',52,60): 12,
    (2004,'text2','s08',161,169): 52,
    (2004,'text4','s12',110,130): 30,
    (2004,'text4','s12',195,215): 78,
    (2004,'text4','s22',131,140): 45,
    (2005,'text4','s12',209,215): 53,
    (2006,'text3','s08',52,59): 20,
    (2006,'text3','s08',178,185): 30,
}

# Literal glossary match where two alternative glosses both appear; editorially choose the one
# corresponding to this specific occurrence.
PHRASE_OVERRIDES = {
    (2003,'cloze','s11',59,69): '投入',
}


def gloss_candidates(meaning: str, zh: str) -> list[str]:
    values=[]
    for value in re.split(r'[；;，,、/]', meaning or ''):
        value=re.sub(r'[（(].*?[)）]', '', value).strip()
        if value and value in zh and value not in values:
            values.append(value)
    return values


def collect_occurrences() -> list[dict]:
    rows=[]
    for year in YEARS:
        for path in sorted((ROOT / f'kaoyan-reader-v1/content/{year}/c').glob('*.json')):
            doc=json.loads(path.read_text(encoding='utf-8'))
            for sentence in doc['sentences']:
                for vocab in sentence.get('vocab',[]):
                    if int(vocab.get('level',0)) < 6:
                        continue
                    rows.append({
                        'year':year,'article_id':doc['article_id'],'sentence_id':sentence['id'],
                        'en_start':vocab['start'],'en_end':vocab['end'],
                        'en_text':sentence['en'][vocab['start']:vocab['end']],
                        'meaning':vocab.get('meaning',''),'zh':sentence['zh'],
                    })
    return rows


def choose_span(row: dict) -> tuple[int,int,str]:
    key=(row['year'],row['article_id'],row['sentence_id'],row['en_start'],row['en_end'])
    phrase=MANUAL_PHRASES.get(key) or PHRASE_OVERRIDES.get(key)
    candidates=gloss_candidates(row['meaning'],row['zh'])
    if phrase is None:
        if not candidates:
            raise ValueError(f'unreviewed nonliteral occurrence: {key} {row["en_text"]!r}')
        phrase=max(candidates,key=len)
    if phrase not in row['zh']:
        raise ValueError(f'reviewed phrase not in translation: {key} {phrase!r}')
    if key in POSITION_OVERRIDES:
        start=POSITION_OVERRIDES[key]
        if row['zh'][start:start+len(phrase)] != phrase:
            raise ValueError(f'position override stale: {key} {phrase!r}')
    else:
        positions=[m.start() for m in re.finditer(re.escape(phrase),row['zh'])]
        if len(positions) != 1:
            raise ValueError(f'occurrence needs reviewed position: {key} {phrase!r} positions={positions}')
        start=positions[0]
    return start,start+len(phrase),phrase


def build() -> dict[int,dict]:
    outputs={year:{'version':1,'year':year,'articles':{},'exceptions':[]} for year in YEARS}
    rows=collect_occurrences()
    for row in rows:
        start,end,text=choose_span(row)
        entry={'en_start':row['en_start'],'en_end':row['en_end'],'en_text':row['en_text'],
               'zh_spans':[{'start':start,'end':end,'text':text}]}
        outputs[row['year']]['articles'].setdefault(row['article_id'],{}).setdefault(row['sentence_id'],[]).append(entry)
    counts=Counter(row['year'] for row in rows)
    if counts != Counter({2003:71,2004:85,2005:24,2006:28}):
        raise ValueError(f'curated occurrence inventory changed; editorial review required: {counts}')
    return outputs


def main() -> None:
    outputs=build()
    target=ROOT / 'content-pipeline/curated/bilingual-highlights'
    target.mkdir(parents=True,exist_ok=True)
    for year,data in outputs.items():
        (target / f'{year}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(year,sum(len(entries) for sm in data['articles'].values() for entries in sm.values()))


if __name__=='__main__':
    main()
