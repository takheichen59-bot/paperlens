// Only the explicitly acquired CC-BY corpus is presented as a verified example.
export const EXAMPLE_IDS=['2501.00680v1','2501.00591v1','2501.00561v1'];
export function exampleRecords(records){return EXAMPLE_IDS.map(id=>records.find(r=>r.id===id&&r.meta?.source==='arxiv')).filter(Boolean);}
export function exampleMetadata(record){return {source:record.meta.source==='arxiv'?'arXiv':record.meta.source||'来源未记录',year:record.meta.year||(record.meta.source==='arxiv'&&/^\d{4}\./.test(record.id)?2000+Number(record.id.slice(0,2)):'年份未记录')};}
