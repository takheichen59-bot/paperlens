// The reading layer is additive. Historical automatic fields remain in the audit sheets.
export const READING_COLUMNS=['论文ID','标题','文章类型','研究问题','研究对象 / 主题','方法路线','步骤 / 论证路径','主要发现 / 论点','作者结论','作者明确局限','助手阅读边界','助手借鉴建议','来源与复核边界'];
export function readingText(r,field){
 const c=r.reading_card,g=c?.source_review;if(!c)return '历史记录没有阅读层；请查看原自动字段。';
 const name=field==='conclusions'?'conclusion':field==='limitations'?'author_limitations':field;
 if(g){const value=g[name];if(value?.length)return value.map(v=>v.text).join('\n');}
 if(field==='objects')return (c.objects||[]).map(o=>o.name+'（'+o.role+'）').join('；')||'对象尚未确认';
 if(field==='steps'&&c.procedure_steps?.length)return c.procedure_steps.map(s=>s.text).join('\n');
 if(field==='steps')return c.article_type?.label==='perspective_or_review'?readingText(r,'arguments'):'未核实可复述的步骤顺序';
 if(field==='arguments'&&c.argument_candidates?.length)return c.argument_candidates.map(s=>s.text).join('\n');
 if(field==='arguments')return (c.fields.findings?.evidence_ids||[]).map(id=>c.evidence.find(e=>e.id===id)?.text).filter(Boolean).join('\n')||'未定位到独立论点';
 const f=c.fields[field];if(f)return f.status==='not_applicable'?'文章类型不适用：'+(f.reason||''):(f.evidence_ids||[]).map(id=>c.evidence.find(e=>e.id===id)?.text).filter(Boolean).join('\n')||f.reason||'未定位到完整候选';
 return '未提供来源支持的条目';
}
export function readingRow(r){const c=r.reading_card,g=c?.source_review;return [r.paper_id,g?.title_zh||c?.title||r.meta.title,g?.type_zh||c?.article_type?.label||'未判定',...['question','objects','methods',c?.article_type?.label==='perspective_or_review'?'arguments':'steps',c?.article_type?.label==='perspective_or_review'?'arguments':'findings','conclusions','limitations','boundaries','suggestions'].map(f=>readingText(r,f)),g?'助手对照原PDF整理；不是自动摘要或独立专家金标准；用户尚未复核。':'规则原文候选，科学内容尚未核实。'];}
export const READING_NUMBERS=['论文ID','对象','物理量','值','单位','条件','归属','阅读证据ID','原文页码'];
export function readingNumbers(r){const c=r.reading_card;return (c?.source_review?.numbers||c?.numeric_bindings||[]).map(n=>[r.paper_id,n.object,n.quantity,n.value,n.unit,n.conditions,n.ownership,n.evidence_ids.join('; '),[...new Set(n.evidence_ids.flatMap(id=>c.evidence.find(e=>e.id===id)?.pages||[]))].join('; ')]);}
export const READING_SOURCES=['论文ID','阅读证据ID','规范化完整句','原文页码','块ID','起始偏移（含）','结束偏移（不含）','原始切片','原PDF SHA256'];
export function readingSources(r){const blocks=new Map((r.raw_blocks||[]).map(b=>[b.block_id,b.text]));return (r.reading_card?.evidence||[]).flatMap(e=>e.parts.map(p=>[r.paper_id,e.id,e.text,p.page,p.block_id,p.start,p.end,Array.from(blocks.get(p.block_id)).slice(p.start,p.end).join(''),r.pdf_hash]));}
