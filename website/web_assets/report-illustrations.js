// Concept sketches only: no measured values, reconstructed micrographs or data curves.
import {READING_DIAGRAM_TYPES} from './reading-chinese.js';
import {rgb} from './vendor/pdf-lib.esm.min.js';
const INK=rgb(.12,.28,.34),BLUE=rgb(.28,.53,.63),PALE=rgb(.84,.92,.94),GOLD=rgb(.78,.55,.25);
export const ILLUSTRATION_TYPES=READING_DIAGRAM_TYPES;
export function drawReadingDiagram(page,type,{x,y,width,height,font}){
 if(!ILLUSTRATION_TYPES.includes(type))throw Error('未知的理解示意图类型。');
 const cx=x+width/2,cy=y+height/2;
 const label=(s,a,b,size=10)=>page.drawText(s,{x:a-font.widthOfTextAtSize(s,size)/2,y:b,size,font,color:INK});
 const line=(a,b,c,d,color=BLUE,w=1.5)=>page.drawLine({start:{x:a,y:b},end:{x:c,y:d},thickness:w,color});
 const circle=(a,b,r,fill=PALE)=>page.drawCircle({x:a,y:b,size:r,color:fill,borderColor:BLUE,borderWidth:1.5});
 const arrow=(a,b,c)=>{line(a,b,c,b);line(c-5,b+3,c,b);line(c-5,b-3,c,b);};
 if(type==='surface_particles'){
  circle(x+width*.24,cy+8,29);circle(x+width*.24,cy+8,22,rgb(.97,.99,1));
  for(const [dx,dy]of [[-22,10],[11,18],[30,-9],[-12,-18]]){circle(x+width*.73+dx,cy+dy+8,13);circle(x+width*.73+dx,cy+dy+8,7,rgb(.97,.99,1));}
  label('较大的颗粒',x+width*.24,y+5);label('更小的颗粒',x+width*.73,y+5);label('浅色边缘表示表面区域',cx,y+height-13,9);
 }else if(type==='preparation'){
  const centers=[x+width/6,cx,x+width*5/6];
  centers.forEach((c,i)=>{page.drawRectangle({x:c-53,y:cy-19,width:106,height:44,color:i===1?rgb(.99,.93,.82):PALE,borderColor:BLUE,borderWidth:.8});label(['混合原料','加工与处理','检查成品'][i],c,cy-2,11);if(i<2)arrow(c+59,cy+3,centers[i+1]-59);});
  label('具体配比、温度和检测条件要看原文',cx,y+3,9);
 }else if(type==='assembly'){
  for(let i=0;i<5;i++){if(i)line(x+width*.17+(i-1)*19,cy+12+(i-1)%2*11,x+width*.17+i*19,cy+12+i%2*11);circle(x+width*.17+i*19,cy+12+i%2*11,9);}
  for(let row=0;row<3;row++)for(let col=0;col<4;col++)circle(x+width*.67+col*18,cy-2+row*16,8);
  label('较疏松的连接',x+width*.25,y+5);label('更紧密的聚集',x+width*.75,y+5);
 }else if(type==='sensor'){
  label('磁场变化',x+width*.14,cy+3,11);arrow(x+width*.26,cy+8,x+width*.36);
  for(let i=0;i<3;i++)page.drawRectangle({x:cx-47,y:cy-15+i*13,width:94,height:10,color:i===1?BLUE:PALE});
  label('复合薄膜',cx,y+5);arrow(x+width*.64,cy+8,x+width*.74);label('电信号',x+width*.86,cy+3,11);
 }else if(type==='layer_stack'){
  const labels=['相邻磁性层','铁酸铋薄层','相邻磁性层'];
  for(let i=0;i<3;i++){page.drawRectangle({x:cx-105,y:y+14+i*24,width:210,height:21,color:i===1?PALE:rgb(.79,.87,.91)});label(labels[i],cx,y+20+i*24,10);}
  line(cx+115,y+38,cx+142,y+38,GOLD);label('界面',cx+166,y+34,10);
 }
}
