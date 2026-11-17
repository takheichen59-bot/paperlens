// Browser-only quick screening. It is deliberately NOT the measured Python engine.
const escapeRE=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
export function formula(value,policy,context=''){
 if(/^[HKL]{2,}\d*$/.test(value)&&/\b(?:planes?|reflections?|peaks?|facets?|orientations?|precession|indices)\b/i.test(context))return false;
 if(policy.known_formulas.includes(value))return true;
 if(!/[a-z0-9]/.test(value))return false;
 const parts=[...value.matchAll(/([A-Z][a-z]?)(\d*)/g)];
 if(parts.map(m=>m[0]).join('')!==value||parts.length<2||parts.length>8)return false;
 const counts=parts.map(m=>Number(m[2]||1));if(counts.some(n=>n<1||n>999)||parts.some(m=>!policy.oxidation[m[1]]))return false;
 const solve=(i,total,positive,negative)=>i===parts.length?total===0&&positive&&negative:policy.oxidation[parts[i][1]].some(v=>solve(i+1,total+counts[i]*v,positive||v>0,negative||v<0));
 return solve(0,0,false,false);
}
