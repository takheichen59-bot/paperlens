// Presentation layer only. Original fields, source text and user reviews stay intact.
export const CHINESE_GUIDE_VERSION='source-chinese-v1';
const zh=s=>typeof s==='string'&&/[\u3400-\u9fff]/u.test(s);
const names=['question','objects','methods','steps','findings','arguments','conclusion','author_limitations','boundaries','suggestions','numbers'];
export function validateChineseSourceReview(record,guide=record.reading_card?.source_review){
 if(!guide||guide.language!=='zh-CN')return null;
 const card=record.reading_card,byId=new Map((card?.evidence||[]).map(e=>[e.id,e]));
 if(guide.version!==CHINESE_GUIDE_VERSION||guide.origin!=='assistant_source_review'||guide.independent_gold!==false||guide.human_review_status!=='unreviewed'||guide.status!=='source_bound'||guide.pdf_hash!==record.pdf_hash||guide.source_paper_id!==record.paper_id||guide.source_title!==record.meta.title||guide.source_parser_version!==record.parser_version||guide.source_reading_version!==card.version||!zh(guide.title_zh))throw Error('中文导读与原论文或提取版本不一致，请重新核对。');
 const anchors=new Map((guide.evidence_anchors||[]).map(a=>[a.id,a.text]));
 if(!anchors.size||anchors.size!==guide.evidence_anchors.length)throw Error('中文导读缺少完整的原句绑定。');
 for(const [id,text]of anchors)if(byId.get(id)?.text!==text)throw Error('中文导读对应的英文证据已变化，请重新核对。');
 for(const name of names){
  if(guide[name]!==undefined&&!Array.isArray(guide[name]))throw Error('中文导读栏目格式不正确。');
  for(const item of guide[name]||[])if(!zh(item.text)||!item.evidence_ids?.length||item.evidence_ids.some(id=>!anchors.has(id)))throw Error('中文要点必须有中文说明和可回查的原句。');
 }
 return guide;
}

const subjectRoles=new Set(['study_subject','study_subject_variant','material_family','impurity_in_host','title_study_object_candidate','impurity_in_host_candidate']);
const fieldMap={question:'question',objects:'objects',methods:'methods',steps:'steps',findings:'findings',conclusions:'conclusion',limitations:'author_limitations'};
const empty={question:'还没有整理出可靠的中文研究目的。',objects:'还没有确认这篇文章主要研究的对象。',methods:'还没有整理出可靠的中文方法说明。',steps:'暂时不能把提取到的句子整理成清楚的操作步骤。',findings:'还没有整理出可靠的中文发现说明。',conclusions:'还没有整理出可靠的中文结论说明。',limitations:'暂时没有找到作者明确说明的不足，不代表研究没有局限。'};

/** No translation model is configured. Missing authored Chinese stays visibly missing. */
export function chineseReadingPlan(record){
 const c=record.reading_card||{},strict=validateChineseSourceReview(record),old=c.source_review,guide=strict||(!old?.language&&old?.origin==='assistant_source_review'&&old?.pdf_hash===record.pdf_hash&&old?.question?.some(i=>zh(i.text))?{...old,legacy:true}:null),fields={};
 for(const [key,source]of Object.entries(fieldMap))fields[key]={items:(guide?.[source]||[]).map(i=>({...i})),reason:guide?.[source]?.length?'':empty[key]};
 if(c.article_type?.label==='perspective_or_review'){fields.methods={items:[],reason:'这是一篇综述或观点文章，不把它当作实验论文来填写方法。'};fields.steps={items:[],reason:'这类文章不提供一套可直接照做的实验步骤。'};if(guide?.arguments?.length)fields.findings={items:guide.arguments.map(i=>({...i})),reason:''};}
 if(!guide){
  const objects=(c.objects||[]).filter(o=>subjectRoles.has(o.role)&&o.evidence_ids?.length&&!/[A-Za-z]{5,}\s+[A-Za-z]{4,}/.test(o.name));
  fields.objects={items:objects.map(o=>({text:'识别到的研究对象线索：'+o.name+'。这项判断还需要核对。',evidence_ids:o.evidence_ids})),reason:objects.length?'':empty.objects};
  const techniques=(c.techniques||[]).filter(t=>t.evidence_ids?.length);
  if(techniques.length)fields.methods.items=[{text:'文中出现了这些技术：'+techniques.map(t=>t.label.replace(/Raman/g,'拉曼')).join('、')+'。这只是方法线索，尚未整理成完整中文说明。',evidence_ids:[...new Set(techniques.flatMap(t=>t.evidence_ids))]}];
 }
 return {language:'zh-CN',origin:guide?'assistant_source_review':'rule_based_chinese_hints',title:guide?.title_zh||'研究阅读卡片',fields,numbers:guide?.numbers||[],boundaries:guide?.boundaries||[],guide,
  notice:guide?.legacy?'这是以前保存的助手中文导读，本次没有重新核对其解释。原来的自动结果和原句均保留。':guide?'中文说明由助手对照原文整理，尚未经过用户或领域专家确认。英文原句和自动提取结果另行保留。':'这篇还没有完整中文导读。下面只列出能识别的线索；没有把英文段落直接当作中文说明。'};
}
