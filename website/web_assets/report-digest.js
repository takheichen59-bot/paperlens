import {chineseReadingPlan} from './reading-chinese.js';
// An evidence-indexed comparison, never a pooled effect, vote or novelty judgement.
export function themeReportPlan(records){
 const rows=Array.from(records,r=>{const p=chineseReadingPlan(r),fields=Object.fromEntries(['question','objects','methods','findings','conclusions'].map(k=>[k,{items:p.fields[k].items.slice(0,k==='objects'?2:1),reason:p.fields[k].reason}]));return {id:r.id,title:p.title,record:r,fields,hasChineseGuide:!!p.guide};});
 return {version:'evidence-comparison-v1',rows,completeChineseGuides:rows.filter(r=>r.hasChineseGuide).length,notice:'按研究对象、方法和发现并排整理。这里没有把不同条件下的数值直接排名，也没有把几篇论文的观点合成一个已经证实的结论。'};
}
