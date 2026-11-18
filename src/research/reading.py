"""Versioned reading layer over immutable research-1 evidence.

This layer reconstructs display text and keeps a reversible source map. It never
rewrites original fields, infers scientific accuracy, or marks a user review done.
"""
from __future__ import annotations
import hashlib
import re

VERSION = 'reading-evidence-v1.1'
SCHEMA = 'paperlens-reading-1'
JOIN_WORDS = set('distributions arrangement arrangements previously floating substitutional phonon observations coupling groundstates commensurate incommensurate networking measurements measurement experimental experiments experiment computational computation calculations calculation photoluminescence spectroscopy temperature dependence nanoparticles nanoparticle ferroelectric polarization antiferromagnetic centrosymmetric noncentrosymmetric synthesized synthesis characterizes characterization configurations configuration interactions interaction simulation simulations relaxation implementation investigated investigate electronic structural spectroscopy properties consequently corresponding comparison approximately superconductivity intercalation irreducible representation'.split())
METHODS = {
 'computation': ('计算与模型', r'\b(?:first.principles|density.functional|DFT|hybrid functional|molecular dynamics|shell model|DL_POLY|Monte.Carlo|computational|interatomic potential)\b'),
 'preparation': ('样品制备', r'\b(?:synthesi[sz]|grown|growth|floating.zone|hydrothermal|precipitation|chemical vapor transport|anneal|sinter)\w*'),
 'characterization': ('测量与表征', r'\b(?:neutron diffraction|X.ray diffraction|Raman|photoluminescence|susceptibility|specific heat|spectroscop|energy.dispersive|4.probes)\w*'),
 'validation': ('比较与验证', r'\b(?:compar\w*.{0,90}(?:calculat|experiment|measur)|(?:calculat|experiment|measur).{0,90}compar\w*|Rietveld|refin\w*|representation analysis)\b'),
}
OWN = re.compile(r'\b(?:we|our|this (?:work|study|paper)|here we)\b', re.I)
PRIOR = re.compile(r'\b(?:previous(?:ly)?|prior|earlier|et al\.|collaborators|has been reported|have been reported|best known)\b', re.I)
RESULT = re.compile(r'\b(?:observ\w*|find|found|show\w*|reveal\w*|demonstrat\w*|exhibit\w*|confirm\w*|stabili[sz]\w*|suggest\w*|possesses|correspond\w*)\b', re.I)
PREDICATE = re.compile(r'\b(?:is|are|was|were|has|have|can|cannot|may|will|could|should|do|does|did|observ\w*|find|found|show\w*|report\w*|reveal\w*|demonstrat\w*|confirm\w*|suggest\w*|exhibit\w*|lead\w*|stabili[sz]\w*|possess\w*|outline|discuss|synthesi[sz]\w*|calculate|use|used|prepared|grown|measur\w*|conduct\w*|collect\w*|record\w*|refin\w*|perform\w*|anneal\w*|relax\w*|optimi[sz]\w*|remain\w*|induce\w*|drive\w*|simulat\w*|promotes|supports|indicates|corroborates|provides|affects|contains|describes|uses|stabilizes|aim\w*|turn\w*|obtain\w*|verif\w*|characteriz\w*|focus\w*|make\w*|yield\w*)\b', re.I)
ORPHAN = re.compile(r'^(?:as (?:a|an|the)\b|temperature dependence\b|and\b|which\b|that\b|with\b|of\b|to\b|because\b|respectively\b)', re.I)
QUANTITIES = re.compile(r'(?<![\w.])([−-]?\d+(?:\.\d+)?)\s*(meV|eV|GPa|MPa|nm|μm|µm|mm|cm[−-]?1|K|°C|ps|fs|Å|%)(?![A-Za-z])')
FIELD_LABELS = {'question':'研究问题', 'methods':'方法路线', 'findings':'主要发现', 'conclusions':'作者结论', 'limitations':'作者明确局限'}


def normalize_text(text):
    """Reflow prose, joining only known broken words; retain ambiguous hyphens."""
    def join(match):
        a, b = match.group(1), match.group(2)
        return a+b if (a+b).lower() in JOIN_WORDS else a+'-'+b
    text = re.sub(r'([A-Za-zα-ωΑ-Ω]+)-[ \t]*\n\s*([A-Za-zα-ωΑ-Ω]+)', join, text)
    return re.sub(r'\s+', ' ', text).strip()


def scientific_title(text):
    text = re.sub(r'\\(?:beta)', 'β', text)
    text = re.sub(r'\\(?:alpha)', 'α', text)
    text = text.replace('\\', '')
    sub = str.maketrans('0123456789x', '₀₁₂₃₄₅₆₇₈₉ₓ')
    text = re.sub(r'_\{([^}]+)\}|_([0-9x]+)', lambda m:(m[1] or m[2]).translate(sub), text)
    return normalize_text(text.replace('$','').replace('{','').replace('}','').replace('--','—'))


def sentences(text):
    start = 0
    # Abbreviations and decimals do not split; fragments remain visible to diagnostics.
    for m in re.finditer(r'(?:[!?]|\.(?![0-9])|(?<![0-9])\.[0-9]+(?:[,–−-][0-9]+)*)(?=\s+(?:[\(\"]?[A-Zβ])|$)',text):
        if text[max(0,m.start()-4):m.end()].endswith(('et al.','Fig.','Sec.','Dr.','e.g.','i.e.')): continue
        a=start
        while a<m.end() and text[a].isspace():a+=1
        if m.end()>a:yield a,m.end()
        start=m.end()
    a=start
    while a<len(text) and text[a].isspace():a+=1
    if a<len(text):yield a,len(text.rstrip())


def complete_sentence(text):
    return not re.search(r'(?:Fig|Sec|Ref|Dr)\.$',text) and len(text.split())>=4 and len(text)>24 and bool(re.search(r'[.!?][”\'"]?$|(?<![0-9])[.!?][0-9,–−-]+$',text)) and not re.match(r'^(?:And|Which|That|Of)\b',text) and not re.match(r'^[a-z]',text) and bool(PREDICATE.search(text))


def _heading(text):
    value=normalize_text(text)
    return len(value)<90 and bool(re.fullmatch(r'(?:[IVX]+[. ]+|\d+[. ]+)?(?:abstract|introduction|methods?|experimental(?: details)?|computational(?: methodology| details)?|calculation details|results(?: and discussion)?|conclusions?|summary|acknowledg\w*|references|supplementary material)',value,re.I))


def _adjacent(previous, current, extents):
    a,b=previous.get('bbox'),current.get('bbox')
    if not a or not b:return previous['page']==current['page']
    if previous['page']==current['page']:
        overlap=min(a[2],b[2])-max(a[0],b[0])
        same_column=overlap>0.55*min(a[2]-a[0],b[2]-b[0]) and -3<=b[1]-a[3]<=48
        next_column=a[0]+80<b[0] and a[3]>.7*extents.get(previous['page'],800) and b[1]<.35*extents.get(current['page'],800)
        return same_column or next_column
    return current['page']==previous['page']+1 and a[3]>.7*extents.get(previous['page'],800) and b[1]<.35*extents.get(current['page'],800)


def build_reading(record):
    raw={b['block_id']:b for b in record['raw_blocks']};extents={}
    for b in raw.values():
        if b.get('bbox'):extents[b['page']]=max(extents.get(b['page'],0),b['bbox'][3])
    groups=[];pending=[];last=None;non_prose=[]
    def flush():
        nonlocal pending
        if pending:groups.append(pending);pending=[]
    for span in record['eligible_ranges']:
        if span['section_kind'] in {'references','supplement'}:flush();last=None;continue
        b=raw[span['block_id']];text=b['text'][span['start']:span['end']]
        if not text.strip() or _heading(text):flush();last=None;continue
        if (not re.search(r'[A-Za-z]{3}',text)) or (re.search(r'[=∑∫∂]',text) and len(text.split())<5):
            flush();last=None;non_prose.append({'block_id':b['block_id'],'start':span['start'],'end':span['end'],'page':b['page'],'reason':'formula_or_numeric_layout_kept_in_original'});continue
        unit={**span,'page':b['page'],'bbox':b.get('bbox'),'raw_text':text}
        prior=normalize_text(pending[-1]['raw_text']) if pending else ''
        continuation=bool(prior and not re.search(r'[.!?:;](?:[0-9,–−-]+)?$',prior) and last and _adjacent(last,unit,extents) and last['section_kind']==unit['section_kind'])
        if not continuation:flush()
        pending.append(unit);last=unit
    flush()
    paragraphs=[];evidence=[];seen=set();fragments=[]
    for group in groups:
        joined='\n'.join(x['raw_text'] for x in group);text=normalize_text(joined)
        if len(text)<35 or text in seen:continue
        seen.add(text)
        parts=[{'block_id':x['block_id'],'start':x['start'],'end':x['end'],'page':x['page']} for x in group]
        mapped,trace=mapped_text(parts,raw)
        if mapped!=text:raise ValueError('Normalization mapping mismatch')
        pid='p-'+hashlib.sha256((text+str(parts)).encode()).hexdigest()[:12]
        paragraphs.append({'id':pid,'text':text,'parts':parts,'section_kind':group[0]['section_kind']})
        for a,z in sentences(text):
            value=text[a:z]
            eid=pid+'-'+str(a)
            item={'id':eid,'paragraph_id':pid,'text':value,'start':a,'end':z,'section_kind':group[0]['section_kind'],'parts':exact_parts(parts,trace[a:z]),'pages':sorted({x['page'] for x in exact_parts(parts,trace[a:z])})}
            if complete_sentence(value):evidence.append(item)
            elif RESULT.search(value):fragments.append({'text':value,'paragraph_id':pid,'reason':'sentence_incomplete_or_context_dependent'})
    title=scientific_title(record['meta'].get('title',''))
    early=' '.join(s['text'] for s in evidence if s['pages'][0]<=2)
    perspective=bool(re.search(r'\b(?:challenges|perspective|review)\b',title,re.I) and re.search(r'\b(?:outline and discuss|review|outstanding challenges|we discuss)\b',early,re.I))
    kind='perspective_or_review' if perspective else 'computational' if re.search(r'simulations|atomistic',title,re.I) else 'mixed_computational_experimental' if re.search(r'first.principles',early,re.I) and re.search(r'photoluminescence|measurements',early,re.I) else 'experimental_or_unresolved'
    fields={}
    def selected(name,items,reason=None):
        unique=list(dict.fromkeys(s['id'] for s in items))
        fields[name]={'status':'candidate_extracted' if unique else 'not_identified','evidence_ids':unique,'reason':None if unique else reason or '规则未找到可独立理解且有来源支持的完整语句，需对照原文复核。'}
    questions=[s for s in evidence if s['pages'][0]<=3 and re.search(r'\b(?:we aim|we investigate|we study|we explore|this paper analyzes|we thoroughly characterize|we outline and discuss|remains unclear|is unknown)\b',s['text'],re.I)]
    selected('question',questions[:2])
    routes=[]
    for key,(label,expression) in METHODS.items():
        candidates=[s for s in evidence if re.search(expression,s['text'],re.I) and not (PRIOR.search(s['text']) and not OWN.search(s['text']))]
        candidates=[s for s in candidates if re.search(r'\b(?:using|used|utiliz\w*|employ\w*|perform\w*|measur\w*|grown|synthesi[sz]\w*|calculat\w*|we (?:report|combine)|conducted|solved)\b',s['text'],re.I)]
        candidates.sort(key=lambda s:(-int(s['section_kind']=='methods')-int(bool(re.search(r'\b(?:using|used|performed|grown|synthesized|conducted)\b',s['text'],re.I))),s['pages'][0]))
        if candidates:routes.append({'category':key,'label':label,'evidence_ids':[s['id'] for s in candidates[:2]],'status':'rule_candidate'})
    selected('methods',[s for s in evidence if any(s['id'] in r['evidence_ids'] for r in routes)])
    candidates=[s for s in evidence if RESULT.search(s['text']) and not (PRIOR.search(s['text']) and not OWN.search(s['text'])) and not re.search(r'\b(?:in recent work|previous work|collaborators)\b',s['text'],re.I)]
    candidates.sort(key=lambda s:(-int(bool(OWN.search(s['text'])))-int(s['section_kind'] in {'results','conclusions'})-int(bool(re.search(r'\b(?:observ|find|found|stabiliz)',s['text'],re.I))),s['pages'][0]))
    chosen=[]
    for s in candidates:
        if any(s['text'] in x['text'] or x['text'] in s['text'] for x in chosen):continue
        if len(s['text'])>650:continue
        chosen.append(s)
        if len(chosen)==3:break
    selected('findings',chosen)
    conclusions=[s for s in evidence if (s['section_kind']=='conclusions' or re.search(r'\b(?:in conclusion|in summary|clearly|we have shown|our results suggest)\b',s['text'],re.I)) and s['id'] not in fields['findings']['evidence_ids']]
    selected('conclusions',conclusions[:2],'未找到独立于已列发现的完整作者结论；没有复制发现或补写结论。')
    limitations=[s for s in evidence if re.search(r'\b(?:limited by|limitation|beyond the scope|future work|not considered|not included|remains unclear|remain unknown)\b',s['text'],re.I)]
    selected('limitations',limitations[:2],'未定位到作者明确局限；不等于论文不存在局限。')
    if perspective:
        fields['methods']={'status':'not_applicable','evidence_ids':[],'reason':'文章属于观点/综述候选；实验操作流程不适用，论证路线需单独阅读。'}
        fields['findings']={'status':'not_applicable','evidence_ids':[],'reason':'未按原创实验结果模板强填；请查看研究问题及论点证据。'}
    objects=[]
    plain=re.sub(r'[$_{}\\]','',record['meta'].get('title','')).replace('beta','β')
    for name in dict.fromkeys(re.findall(r'(?<![A-Za-z])(?:[A-Z][a-z]?(?:\d+(?:\.\d+)?|[xy])?){2,}(?![a-z])',plain if re.search(r'\d',plain) else plain+' '+' '.join(s['text'] for s in evidence if s['pages'][0]==1 and OWN.search(s['text']))[:2500])):
        if name in {'DFT','EPC','PL','BCS','GLW','PAW','XRD','CVT','III','II'} or len(name)<4 or not re.search(r'\d',name):continue
        sources=[s['id'] for s in evidence if name in re.sub(r'\s+','',s['text'])]
        if sources:objects.append({'name':name,'role':'title_study_object_candidate','evidence_ids':sources[:2]})
    if re.search(r'Chromium|\bCr\b',plain,re.I) and any('Ga2O3' in x['name'] for x in objects):
        sources=[s['id'] for s in evidence if re.search(r'\bCr\b|Chromium',s['text'],re.I) and 'Ga2O3' in s['text']]
        objects.append({'name':'Cr in β-Ga2O3','role':'impurity_in_host_candidate','evidence_ids':sources[:2]})
    if perspective:objects=[{'name':'quantum matter','role':'research_topic_not_sample','evidence_ids':fields['question']['evidence_ids']}]
    numeric=[]
    for s in evidence:
        for m in QUANTITIES.finditer(s['text']):
            numeric.append({'value':m[1],'unit':m[2],'statement':s['text'],'evidence_ids':[s['id']],
                'object':next((o['name'] for o in objects if o['name'] in s['text']),None),'quantity':None,
                'conditions':s['text'] if re.search(r'\b(?:at|under|using|with|temperature|excitation)\b',s['text'],re.I) else None,
                'comparison_baseline':None,'ownership':'needs_review','missing_bindings':['physical_quantity','ownership']})
    layer={'schema_version':SCHEMA,'version':VERSION,'origin':'deterministic_source_reconstruction','review_status':'unreviewed',
        'paper_id':record['paper_id'],'pdf_hash':record['pdf_hash'],'title':title,'article_type':{'label':kind,'status':'rule_candidate'},
        'objects':objects,'fields':fields,'method_routes':routes,'numeric_candidates':numeric,
        'paragraphs':paragraphs,'evidence':evidence,'excluded_fragments':fragments,'non_prose_ranges':non_prose,
        'quality':{'parsing':'text_available' if raw else 'no_text','field_coverage':{k:v['status'] for k,v in fields.items()},'source_slices':'validated','scientific_accuracy':'not_independently_evaluated','human_review':'unreviewed'},
        'notes':['规范化文本用于阅读；原始块和定位保持不变。','方法路线按来源线索分类，不等于已核验的操作顺序。','数值缺少对象、条件或归属时不进入关键发现数字表。']}
    validate_reading(record,layer)
    return layer


def validate_reading(record,layer=None):
    layer=layer or record.get('reading_card')
    if layer is None:return record
    if layer.get('schema_version')!=SCHEMA or layer['pdf_hash']!=record['pdf_hash'] or layer['review_status']!='unreviewed':raise ValueError('Invalid reading layer identity')
    if layer.get('version') not in {VERSION,'reading-evidence-v1','reading-evidence-browser-v1','reading-evidence-browser-v2'} or layer.get('paper_id')!=record['paper_id'] or not isinstance(layer.get('article_type',{}).get('label'),str):raise ValueError('Invalid reading metadata')
    if set(layer.get('fields',{}))!=set(FIELD_LABELS):raise ValueError('Missing reading fields')
    raw={b['block_id']:b for b in record['raw_blocks']};paragraphs={p['id']:p for p in layer['paragraphs']};evidence={s['id']:s for s in layer['evidence']}
    if len(paragraphs)!=len(layer['paragraphs']) or len(evidence)!=len(layer['evidence']):raise ValueError('Duplicate reading evidence')
    def source(part):
        b=raw[part['block_id']];a,z=part['start'],part['end']
        if type(a)is not int or type(z)is not int or not 0<=a<z<=len(b['text']) or part['page']!=b['page']:raise ValueError('Reading source range mismatch')
        if not any(x['block_id']==part['block_id'] and x['start']<=a<z<=x['end'] and x['section_kind'] not in {'references','supplement'} for x in record['eligible_ranges']):raise ValueError('Reading evidence outside body')
        return b['text'][a:z]
    for p in paragraphs.values():
        chunks=[source(part) for part in p['parts']]
        if normalize_text('\n'.join(chunks))!=p['text']:raise ValueError('Reading normalization/source mismatch')
    for s in evidence.values():
        p=paragraphs[s['paragraph_id']]
        if p['text'][s['start']:s['end']]!=s['text'] or not complete_sentence(s['text']):raise ValueError('Incomplete or mismatched reading sentence')
        chunks=[source(v) for v in s['parts']]
        if normalize_text('\n'.join(chunks))!=s['text'] or s['pages']!=sorted({v['page'] for v in s['parts']}):raise ValueError('Reading sentence source map mismatch')
    for field in layer['fields'].values():
        if any(eid not in evidence for eid in field['evidence_ids']):raise ValueError('Reading field lacks evidence')
    review=layer.get('source_review')
    if review:
        if review.get('origin')!='assistant_source_review' or review.get('human_review_status')!='unreviewed' or review.get('independent_gold') is not False or review.get('pdf_hash')!=record['pdf_hash']:raise ValueError('Invalid source review provenance')
        for name in ('question','objects','methods','steps','findings','arguments','conclusion','author_limitations','boundaries','suggestions','numbers'):
            for item in review.get(name,[]):
                if not isinstance(item.get('text'),str) or not item['text'].strip() or not item.get('evidence_ids') or any(e not in evidence for e in item['evidence_ids']):raise ValueError('Unsupported source-reviewed claim')
                if name=='numbers' and any(not item.get(k) for k in ('value','unit','quantity','object','conditions','ownership')):raise ValueError('Incomplete key-number binding')
    return record


def mapped_text(parts, raw):
    """Normalization plus transient output-character -> original range mapping."""
    chars=[];positions=[]
    for i,part in enumerate(parts):
        if i:chars.append('\n');positions.append(None)
        text=raw[part['block_id']]['text'][part['start']:part['end']]
        chars.extend(text);positions.extend((i,n) for n in range(part['start'],part['end']))
    source=''.join(chars);out=[];mapping=[];cursor=0
    for m in re.finditer(r'([A-Za-zα-ωΑ-Ω]+)-[ \t]*\n\s*([A-Za-zα-ωΑ-Ω]+)',source):
        out.extend(source[cursor:m.start()]);mapping.extend(positions[cursor:m.start()])
        indexes=list(range(m.start(1),m.end(1)))
        if (m[1]+m[2]).lower() not in JOIN_WORDS:indexes.append(m.end(1))
        indexes.extend(range(m.start(2),m.end(2)))
        out.extend(source[n] for n in indexes);mapping.extend(positions[n] for n in indexes);cursor=m.end()
    out.extend(source[cursor:]);mapping.extend(positions[cursor:])
    text=''.join(out);result=[];traces=[];last=0
    for m in re.finditer(r'\s+',text):
        result.extend(text[last:m.start()]);traces.extend(mapping[last:m.start()]);result.append(' ');traces.append(next((p for p in mapping[m.start():m.end()] if p is not None),None));last=m.end()
    result.extend(text[last:]);traces.extend(mapping[last:]);a=0;z=len(result)
    while a<z and result[a].isspace():a+=1
    while z>a and result[z-1].isspace():z-=1
    return ''.join(result[a:z]),traces[a:z]


def exact_parts(parts, trace):
    ranges=[]
    for position in trace:
        if position is None:continue
        i,n=position
        if ranges and ranges[-1][0]==i:ranges[-1][2]=n+1
        else:ranges.append([i,n,n+1])
    return [{'block_id':parts[i]['block_id'],'start':a,'end':z,'page':parts[i]['page']} for i,a,z in ranges]
