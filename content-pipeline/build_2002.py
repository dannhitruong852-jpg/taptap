"""Compile explicitly curated 2002 translations and C directions. No runtime AI."""
import hashlib
import json
import re
import sys
from pathlib import Path
from cloze import fill_cloze

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'voice-pipeline'))
from batch_schema import validate_article

# emotion, contrast, rate, exaggeration, CFG, clause pause. Discourse labels
# and clause boundaries are authored upstream, not inferred by this compiler.
PROFILES = {
 'compare': ('neutral','micro',.98,.57,.44,95),
 'contrast': ('serious','micro',.98,.61,.43,130),
 'explain': ('neutral','micro',1.00,.52,.46,65),
 'sequence': ('lively','micro',1.03,.55,.45,65),
 'qualify': ('neutral','low',.97,.50,.47,85),
 'emphasize': ('warm','micro',.97,.60,.43,90),
 'advance': ('lively','micro',1.02,.55,.45,65),
 'conclude': ('warm','micro',.97,.56,.46,95),
 'story': ('warm','micro',1.01,.56,.44,75),
 'settle': ('warm','low',.98,.49,.48,90),
 'action_turn': ('lively','strong',1.04,.66,.40,70),
 'dialogue': ('curious','micro',1.00,.60,.43,85),
 'irony': ('ironic','strong',.97,.67,.39,180),
 'warning': ('serious','micro',.97,.57,.45,105),
 'resolve': ('warm','micro',1.00,.55,.46,75),
 'encourage': ('warm','micro',1.00,.57,.44,75),
 'playful': ('lively','micro',1.02,.62,.41,130),
 'example': ('neutral','low',1.02,.50,.47,65),
 'ask': ('curious','micro',.98,.60,.43,110),
 'statistic': ('neutral','micro',.96,.54,.47,90),
 'report': ('neutral','low',1.00,.50,.48,75),
 'explain_quote': ('neutral','micro',.99,.57,.43,95),
 'qualify_quote': ('serious','micro',.96,.55,.46,95),
 'evaluation_quote': ('serious','strong',.97,.62,.43,115),
}
OVERRIDES = {('text2',6): {'contrast':'micro', 'exaggeration':.59},
             ('text1',8): {'strong_evidence':'until: calm setup interrupted by pushing, rushing, grabbing and stomping'},
             ('text1',10): {'strong_evidence':'The God/doctor reversal is the explicit punchline'},
             ('text4',14): {'strong_evidence':'Explicit evaluation: systematic patient abuse'}}
CLOZE_ANCHORS = [
 ('happened between.', 'between'), ('not until the', 'until'),
 ('pre-electronic medium,', 'medium'), ('the company of', 'company'),
 ('revolution speeded up', 'speeded'), ('leading on through', 'on'),
 ('pictures into the', 'into'), ('in perspective.', 'perspective'),
 ('recognized, however,', 'however'), ('followed by the invention', 'followed'),
 ('although its impact', 'although'), ('immediately apparent.', 'apparent'),
 ('as institutional,', 'institutional'), ('storage capacity increasing', 'capacity'),
 ('people, in terms of generations', 'in terms of'), ('much smaller.', 'smaller'),
 ('the context within', 'context'), ('has influenced both', 'influenced'),
 ('been controversial views', 'controversial'), ('weighed against', 'against')]
CHOICES = [
 ['between','before','since','later'],['after','by','during','until'],
 ['means','method','medium','measure'],['process','company','light','form'],
 ['gathered','speeded','worked','picked'],['on','out','over','off'],
 ['of','for','beyond','into'],['concept','dimension','effect','perspective'],
 ['indeed','hence','however','therefore'],['brought','followed','stimulated','characterized'],
 ['unless','since','lest','although'],['apparent','desirable','negative','plausible'],
 ['institutional','universal','fundamental','instrumental'],['ability','capability','capacity','faculty'],
 ['by means of','in terms of','with regard to','in line with'],['deeper','fewer','nearer','smaller'],
 ['context','range','scope','territory'],['regarded','impressed','influenced','effected'],
 ['competitive','controversial','distracting','irrational'],['above','upon','against','with']]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def vocabulary_for(en, lexicon):
    found = []
    for lemma, entry in lexicon.items():
        level, meaning, *variants = entry
        for surface in [lemma, *variants]:
            for match in re.finditer(r'(?<![\w-])' + re.escape(surface) + r'(?![\w-])', en, flags=re.I):
                found.append({'word':match.group(), 'lemma':lemma, 'level':level,
                              'meaning':meaning, 'start':match.start(), 'end':match.end()})
    return sorted(found, key=lambda x: x['start'])


def compile_article(source, item):
    article_id = item['id']
    result = {'year':2002, 'section_type':item['section_type'], 'article_id':article_id,
              'source_sha256':source['source_sha256'], 'source_pages':item['pages'],
              'accent':'en-US', 'primary_actor_id':item['actor'],
              'article_context':item['context'],
              'article':{'year':2002, 'section':article_id, 'title':item['title'], 'background':item['context']},
              'editorial_status':'reviewed_candidate', 'audio_status':'not_rendered',
              'vocabulary_scale':'project-curated-1-9-v1',
              'reference_pack_status':'three licensed pilot voices; not the full 15-actor pack',
              'sentences':[]}
    for number, row in enumerate(item['rows'], 1):
        paragraph, marked, zh, discourse, focus = row
        en = marked.replace('|', '')
        parts = marked.split('|')
        emotion, contrast, rate, exaggeration, cfg, pause = PROFILES[discourse]
        override = OVERRIDES.get((article_id, number), {})
        contrast = override.get('contrast', contrast)
        exaggeration = override.get('exaggeration', exaggeration)
        sentence = {'id':f's{number:02d}', 'paragraph':paragraph, 'en':en, 'zh':zh,
                    'vocab':vocabulary_for(en, source['vocabulary']),
                    'discourse_function':discourse, 'prosody_focus':focus,
                    'contrast_level':contrast, 'strong_evidence':override.get('strong_evidence'),
                    'segments':[]}
        for part_index, text in enumerate(parts):
            sid = f's{number:02d}-{part_index+1:02d}'
            actor, role = item['actor'], 'narrator'
            e, r, ex, cf = emotion, rate, exaggeration, cfg
            if article_id == 'text1' and number == 9 and part_index == 0:
                actor, role = '12', 'new_arrival'
            if article_id == 'text1' and number == 10:
                actor, role = ('05','narrator') if part_index == 1 else ('13','st_peter')
                e, ex = ('neutral',.50) if part_index == 1 else ('ironic',.65)
            if article_id == 'text2' and number == 10:
                actor, role = ('05','narrator') if part_index == 1 else ('12','dave_lavery')
            if article_id == 'text4' and (number in (7,8,14) or (number == 6 and part_index == 0)):
                actor, role = '13', 'george_annas'
            if article_id == 'text1' and number == 8:
                e, r, ex, cf = [('warm',.97,.48,.48),('curious',1.00,.60,.44),('lively',1.06,.68,.40)][part_index]
            elif len(parts) > 1 and part_index == len(parts)-1 and discourse in ('contrast','compare','qualify','conclude','explain'):
                r, ex = max(.92, rate-.02), min(.70, exaggeration+.035)
            segment = {'id':sid,'text':text,'speaker_role':role,'actor_id':actor,
                       'emotion':e,'intensity':2 if contrast=='strong' else 1,
                       'rate':round(r,3),'exaggeration':round(ex,3),'cfg_weight':cf,
                       'pause_before_ms':0,'pause_after_ms':pause if part_index < len(parts)-1 else 0,
                       'audio_path':f'./audio/2002/c-{article_id}/{sid}.opus',
                       'generation_fingerprint':'pending-render','qa_status':'not_generated'}
            sentence['segments'].append(segment)
        if ''.join(s['text'] for s in sentence['segments']) != en:
            raise ValueError('Segment fidelity failure')
        result['sentences'].append(sentence)
    errors = validate_article(result)
    if errors:
        raise ValueError(f'{article_id}: {errors}')
    return result


def main():
    source_path = ROOT / 'content-pipeline/curated/2002.json'
    source = json.loads(source_path.read_text(encoding='utf-8'))
    catalog = {'version':1, 'years':[2002], 'default_article':'2002-text1', 'articles':[]}
    results = []
    for item in source['articles']:
        doc = compile_article(source,item)
        out = ROOT / f"kaoyan-reader-v1/content/2002/c/{item['id']}.json"
        write_json(out, doc)
        catalog['articles'].append({'id':f"2002-{item['id']}",'year':2002,
            'section_type':item['section_type'],'title':item['title'],
            'content':f"./content/2002/c/{item['id']}.json",
            'manifest':f"./audio/2002/c-{item['id']}/manifest.json",
            'sentences':len(doc['sentences'])})
        results.append({'id':item['id'], 'sentences':len(doc['sentences']),
                        'segments':sum(len(s['segments']) for s in doc['sentences'])})
        if item['id'] == 'cloze':
            original = '\n'.join(s['en'] for s in doc['sentences'])
            template = original
            for n,(anchor,word) in enumerate(CLOZE_ANCHORS,1):
                if template.count(anchor) != 1:
                    raise ValueError(f'Ambiguous cloze anchor {n}: {anchor}')
                template = template.replace(anchor, anchor.replace(word,'{{'+str(n)+'}}',1),1)
            answers = {n:letter for n,letter in enumerate(source['cloze_key']['answers'],1)}
            choices = {n:dict(zip('ABCD',options)) for n,options in enumerate(CHOICES,1)}
            if fill_cloze(template, answers, choices) != original:
                raise ValueError('Cloze reconstruction disagrees with reviewed manuscript')
            write_json(ROOT / 'reports/extraction/2002-cloze-provenance.json',
                       {'source':source['cloze_key'], 'template':template,'answers':answers,'choices':choices,
                        'restored_blanks':20,'status':'verified_against_publisher_key_and_user_pdf_choices'})
    semantic_path = ROOT / 'content-pipeline/semantic_spans/2002.json'
    if semantic_path.is_file():
        semantic = json.loads(semantic_path.read_text(encoding='utf-8'))
        write_json(ROOT / 'kaoyan-reader-v1/content/2002/semantic-spans.json', semantic)
    write_json(ROOT / 'kaoyan-reader-v1/content/catalog.json',catalog)
    write_json(ROOT / 'reports/extraction/2002.json',
               {'year':2002,'source_filename':source['source_filename'], 'source_sha256':source['source_sha256'],
                'curated_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
                'method':'visual PDF review plus explicit curated manuscript; not unverified regex output',
                'cloze_count':1,'reading_count':4,'part_b_count':0,'translation_count':1,
                'translation_selection':'five original underlined segments; surrounding context only in separate introductory note',
                'excluded_pages':[4,6,8,10,12],
                'corrections':['PDF text-layer quote artifacts restored visually',
                               'Text 1 alternatively if: no inserted comma',
                               'Text 2 and Text 3 for/far text-layer errors restored from rendered page',
                               'Original early 20th century and machine panel error wording preserved; not silently corrected'],
                'warnings':['Audio requires C-mode listening acceptance','Only three licensed pilot reference voices configured',
                            'Vocabulary is a transparent curated study scale, not an official external standard'],
                'suspected_contamination':[], 'unresolved_sections':[], 'articles':results})
    print(json.dumps(results))

if __name__ == '__main__':
    main()
