// Metadata origin and cache age for search results and saved batch reports.
export function discoveryDescription(data){
 const provider={arxiv:'arXiv',datacite:'DataCite',openalex:'OpenAlex',crossref:'Crossref'}[data.provider]||'文献来源';
 if(data.cache){const at=new Date(data.cache.fetched_at).toLocaleString('zh-CN');return (data.cache.state==='stale'?'实时来源暂不可用，使用相同检索词的历史真实结果':'使用已保存的真实检索结果')+' · '+provider+' · 获取于 '+at;}
 if(data.scope?.startsWith('PINNED_'))return '按输入的 arXiv ID 读取已核对版本；不是关键词实时检索。';
 return data.upstream_notice||(provider==='DataCite'?'DataCite 登记的真实 arXiv 元数据':provider==='OpenAlex'?'OpenAlex 实时元数据 · arXiv 原文位置':provider+' 实时元数据');
}
