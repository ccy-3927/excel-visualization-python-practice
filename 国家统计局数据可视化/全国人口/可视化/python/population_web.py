"""生成两套可完全离线打开的交互HTML。

11：全国年度人口2016—2025，浅色五图联动、年份播放、101指标检索。
12：湖蓝侧栏、暖白主体，抽样年龄/性别与2020普查分开切换，布局与11不同。
Plotly JS、原始数据与说明全部内嵌，无外部字体、CDN或联网请求。
统计处理与population_static.py一致；缺失保留null，抽样时间轴跳过缺失2020，
热力图仅展示有效年份；2020普查独立冻结年份。
默认读取population_data.py内嵌快照。依赖plotly；无需浏览器服务器。
"""
from pathlib import Path
import json,argparse
from plotly.offline import get_plotlyjs
from population_data import load_data,validate,YEARS,SAMPLE_YEARS,AGES
OUT=Path(__file__).resolve().parents[1]

BASE_CSS=r'''
*{box-sizing:border-box}body{margin:0;font:14px/1.5 "Microsoft YaHei","Noto Sans SC",sans-serif;color:#243F48;background:#F8F8F3}button,input,select{font:inherit}button{cursor:pointer;transition:background .18s,transform .18s}button:hover{transform:translateY(-1px)}button:disabled{cursor:default;opacity:.5;transform:none}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #C88E59;outline-offset:3px}button,a{touch-action:manipulation}a{color:inherit;text-decoration:none}.btn{border:1px solid #E2E9E6;border-radius:10px;background:#fff;color:#60777F;padding:8px 14px}.btn.primary{background:#287D8E;border-color:#287D8E;color:white}.muted{color:#6B7E83}.modal{position:fixed;inset:0;background:#183D4760;z-index:100;display:grid;place-items:center;padding:26px;backdrop-filter:blur(6px)}.modal[hidden]{display:none}.modalbox{color:#243F48;background:#FBFCF9;border:1px solid #E2E9E6;border-radius:22px;max-width:1050px;width:100%;max-height:88vh;overflow:auto;box-shadow:0 30px 120px #24454F28;padding:28px}.modalhead{display:flex;justify-content:space-between;align-items:center;gap:14px;position:sticky;top:-28px;background:#FBFCF9;z-index:3;padding:12px 0}.modalhead h2{margin:0;font-size:22px}.close{font-size:22px;line-height:1;border:0;background:#EDF3F1;border-radius:50%;width:34px;height:34px;color:#557982}.notes p{line-height:1.9;margin:13px 0}.notes h3{margin:25px 0 8px;color:#287D8E}.notes details{margin:10px 0;border-top:1px solid #E2E9E6;padding-top:10px}.notes summary{cursor:pointer}.search{width:100%;padding:12px 15px;margin:10px 0 20px;border:1px solid #D5E3E3;border-radius:12px;background:#fff}.indicator{background:#fff;border:1px solid #E2E9E6;border-radius:12px;padding:14px;margin-bottom:10px}.indicator summary{cursor:pointer;display:flex;justify-content:space-between;gap:14px;font-weight:600}.indicator small{color:#74898E;white-space:nowrap;font-weight:400}.rawtable{margin-top:15px;overflow:auto}.rawtable table{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}.rawtable th,.rawtable td{padding:9px 11px;border-bottom:1px solid #E8EEEB;text-align:right}.rawtable th:first-child,.rawtable td:first-child{text-align:left}.chart{min-height:0;min-width:0;width:100%;height:100%}.plotcard{min-width:0;min-height:0;display:flex;flex-direction:column}.cardhead{flex:0 0 auto;padding:16px 20px 4px;display:flex;align-items:start;justify-content:space-between;gap:10px}.cardhead h2{font-size:16px;margin:0;letter-spacing:.02em}.cardhead p{font-size:12px;color:#6F858A;margin:3px 0 0}.chartwrap{flex:1;min-height:0;min-width:0}.export{border:0;color:#80969C;background:transparent;padding:2px 3px;font-size:12px;white-space:nowrap}.paneltag{font-size:11px;border-radius:6px;padding:3px 7px;color:#477887;background:#F0F6F4;white-space:nowrap}input[type=range]{accent-color:#287D8E;cursor:pointer}input[type=range]:disabled{cursor:default}svg{display:block}.modebar{display:none!important}
@media(max-width:700px){.modal{padding:10px}.modalbox{padding:18px;max-height:92vh}.modalhead{top:-18px}.indicator summary{display:block}.cardhead{padding:14px 14px 2px}.cardhead h2{font-size:15px}}
'''

MODALS=r'''
<div class="modal" id="infoModal" hidden role="dialog" aria-modal="true" aria-labelledby="infoTitle"><div class="modalbox"><div class="modalhead"><h2 id="infoTitle">数据说明</h2><button class="close" data-close aria-label="关闭">×</button></div><div class="notes">
<h3>数据来自哪里</h3><p>仅使用本次提供的国家统计局8个工作簿。年度人口覆盖2016—2025年；年龄分组抽样覆盖2016—2024年，未提供2020；人口普查及平均预期寿命仅有2020年。原始数值、单位与缺失情况可在“全部指标”中查看。</p>
<h3>三种数据分别呈现</h3><p>年度人口为全国数据，人数原单位为万人。人口抽样调查记录的是样本人数，不是全国人口估计；不同年份样本量不同，结构比较以各年总样本为分母。2020年末人口与2020普查人口分别保留，不作为同一次观测替换。</p>
<h3>计算方法</h3><p>城镇人口比重＝城镇人口÷年末总人口×100；年度年龄比重＝该年龄段人口÷同年年末总人口×100；年度人口变化＝当年人口−上年人口。2016没有上年基值。抚养比沿用发布值，不用其他表重新计算覆盖。</p><p>样本年龄比重＝该年龄段样本人数÷当年总样本人数×100；样本男女金字塔均用同年总样本为分母。样本性别比＝男性人数÷女性人数×100（女＝100）。横截面性别差异不能解释为个人的生存过程。2020样本缺失不插值、不补零。</p>
<p>教育程度使用每十万人中的人数，四类不凑成100%。预期寿命差＝女性−男性。普查年龄比重原表合计100.1%，加权样本分项与总数也可能略有差异，均保留原值。图内数字适度四舍五入，悬浮框显示更多位数。渐变及立体装饰均不代表额外数据。</p>
<h3>原始工作簿注释</h3><div id="originalNotes"></div>
</div></div></div>
<div class="modal" id="explorerModal" hidden role="dialog" aria-modal="true" aria-labelledby="explorerTitle"><div class="modalbox"><div class="modalhead"><h2 id="explorerTitle">全部指标 <span id="indicatorCount" class="muted"></span></h2><button class="close" data-close aria-label="关闭">×</button></div><input id="indicatorSearch" class="search" placeholder="搜索指标，例如：人口、寿命、35-39岁" aria-label="搜索指标"><div id="indicatorList"></div></div></div>
'''

COMMON_JS=r'''
const D=SNAPSHOT.series,Y=YEARS,SY=SAMPLE_YEARS,A=AGES;
const C={teal:'#4A7180',blue:'#287D8E',blueFill:'#4E98AA',orange:'#EFB885',orangeLine:'#C58B56',orangeInk:'#9D6334',gold:'#9D6334',ink:'#243F48',muted:'#6B7E83',grid:'#E6ECEA'};
const $=s=>document.querySelector(s),v=(k,y)=>D[k]?.values[String(y)]??null,vs=(k,ys=Y)=>ys.map(y=>v(k,y));
const fmt=(n,d=2)=>n===null||!Number.isFinite(n)?'—':n.toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d});
const signed=(n,d=2)=>n===null?'—':(n>0?'+':'')+fmt(n,d);
const sk=(age=null,sex=null)=>age===null?(sex||'')+'人口数 (人口抽样调查)':age+(sex||'')+'人口数 (人口抽样调查)';
const profile=(year,sex=null)=>A.map(a=>v(sk(),year)===null?null:v(sk(a,sex),year)/v(sk(),year)*100);
const ranges=[[0,3],[3,13],[13,20]],broad=(year,sex=null)=>ranges.map(([a,b])=>v(sk(),year)===null?null:profile(year,sex).slice(a,b).reduce((s,n)=>s+n,0));
const config={displayModeBar:false,responsive:true,scrollZoom:false,locale:'zh-CN'};
const hoverNumber=(label,unit,d=2)=>`${label}<br>%{x}年 · %{y:.${d}f}${unit}<extra></extra>`;
function layout(structure=false){
 const fg=C.muted,grid=C.grid;
 return {paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'Microsoft YaHei, sans-serif',size:12,color:fg},
 margin:{l:49,r:20,t:12,b:35},hovermode:'x unified',hoverlabel:{bgcolor:'#FFFFFF',bordercolor:'#D5E4E4',font:{color:C.ink,size:13}},
 xaxis:{showgrid:false,zeroline:false,tickfont:{size:11},fixedrange:true,tickmode:'array',tickvals:[2016,2018,2020,2022,2024,2025],range:[2015.6,2025.4],ticks:''},
 yaxis:{gridcolor:grid,zeroline:false,fixedrange:true,ticks:'',tickfont:{size:11},rangemode:'tozero'},
 legend:{orientation:'h',x:0,y:1.02,xanchor:'left',yanchor:'bottom',font:{size:11},traceorder:'normal',itemclick:false,itemdoubleclick:false},showlegend:false};
}
function series(k,c,name=k,ys=Y,scale=1){return {type:'scatter',mode:'lines+markers',x:ys,y:vs(k,ys).map(n=>n===null?null:n/scale),name,line:{color:c,width:2.5},marker:{color:c,size:4},connectgaps:false};}
function selection(year,structure=false){return {type:'line',xref:'x',yref:'paper',x0:year,x1:year,y0:0,y1:1,line:{color:'#90ADB54A',width:1,dash:'dot'},layer:'below'};}
function mark(year,y,c,structure=false){return {type:'scatter',mode:'markers',x:[year],y:[y],marker:{size:10,color:c,line:{color:'#FFFFFF',width:2}},showlegend:false,hoverinfo:'skip'};}
async function draw(id,traces,l,click){
 const el=document.getElementById(id);await Plotly.react(el,traces,l,config);
 el.removeAllListeners('plotly_click');if(click)el.on('plotly_click',e=>click(e.points[0]));
}
let activeModal=null,modalOrigin=null;
function openModal(id){modalOrigin=document.activeElement;activeModal=document.getElementById(id);activeModal.hidden=false;document.body.style.overflow='hidden';activeModal.querySelector('button').focus();}
function closeModal(){if(activeModal){activeModal.hidden=true;activeModal=null;document.body.style.overflow='';modalOrigin?.focus();}}
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',closeModal));
document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)closeModal();}));
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();if(e.key==='Tab'&&activeModal){const nodes=[...activeModal.querySelectorAll('button,input,summary,[href]')].filter(n=>n.offsetParent!==null);const first=nodes[0],last=nodes.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
$('#originalNotes').innerHTML=Object.entries(SNAPSHOT.notes).map(([file,notes])=>`<details><summary>${esc(file)}</summary>${notes.map(n=>`<p>${esc(n)}</p>`).join('')}</details>`).join('');
function indicators(query=''){
 const list=Object.entries(D).filter(([k])=>k.includes(query));$('#indicatorCount').textContent=list.length+' / '+Object.keys(D).length;
 $('#indicatorList').innerHTML=list.length?list.map(([k,s])=>{
  const sample=k.includes('抽样调查'),census=k.startsWith('人口普查'),only2020=Object.keys(s.values).length===1;
  const scope=sample?'抽样样本':census?'2020普查':only2020?'2020':'全国年度';
  const ys=sample?Array.from({length:9},(_,i)=>2016+i):only2020?[2020]:Y;
  return `<details class="indicator"><summary><span>${esc(k)}</span><small>${scope} · ${esc(s.unit)}</small></summary><div class="rawtable"><table><tr><th>年份</th>${ys.map(y=>`<th>${y}</th>`).join('')}</tr><tr><td>${esc(s.unit)}</td>${ys.map(y=>`<td>${s.values[y]==null?'—':fmt(s.values[y],Number.isInteger(s.values[y])?0:2)}</td>`).join('')}</tr></table></div><p class="muted">${s.sources.map(esc).join('、')}</p></details>`;
 }).join(''):'<p class="muted">没有匹配的指标</p>';
}
$('#indicatorSearch').addEventListener('input',e=>indicators(e.target.value.trim()));indicators();
document.querySelectorAll('[data-info]').forEach(b=>b.addEventListener('click',()=>openModal('infoModal')));
document.querySelectorAll('[data-explorer]').forEach(b=>b.addEventListener('click',()=>openModal('explorerModal')));
document.querySelectorAll('[data-export]').forEach(b=>b.addEventListener('click',async()=>{
 const id=b.dataset.export,el=document.getElementById(id);b.disabled=true;
 try{const uri=await Plotly.toImage(el,{format:'png',width:1600,height:900,scale:2});const a=document.createElement('a');a.href=uri;a.download=(el.closest('.plotcard').querySelector('h2').textContent||'人口图表')+'.png';a.click();}finally{b.disabled=false;}
}));
function resizePlots(){document.querySelectorAll('.js-plotly-plot').forEach(el=>Plotly.Plots.resize(el));}
window.addEventListener('resize',resizePlots);
'''

DAY_CSS=r'''
.day{max-width:2400px;margin:auto;padding:22px 28px 20px;min-height:100vh;display:grid;grid-template-rows:65px 105px 69px minmax(295px,1fr) minmax(290px,1fr);gap:16px;height:100vh;min-height:900px}.dayhead{display:flex;align-items:center;justify-content:space-between;gap:20px}.brand{display:flex;gap:16px;align-items:center}.brandicon{height:46px;width:46px;background:linear-gradient(145deg,#65A9B7,#287D8E);border-radius:14px;box-shadow:0 8px 20px #287D8E1C;display:flex;gap:4px;align-items:end;justify-content:center;padding:12px}.brandicon i{width:5px;background:#F2F8F8;border-radius:2px}.brandicon i:nth-child(1){height:9px}.brandicon i:nth-child(2){height:16px}.brandicon i:nth-child(3){height:23px}.brand h1{margin:0;font-size:26px;letter-spacing:.05em}.brand p{margin:2px 0 0;color:#7A8E91;font-size:12px}.actions{display:flex;gap:8px;align-items:center}.yearpill{border:1px solid #D6E5E3;background:#EDF4F2;border-radius:10px;padding:8px 15px;color:#287D8E;font-weight:700}.kpis{display:grid;grid-template-columns:1.15fr 1fr 1fr 1fr;gap:16px}.kpi{position:relative;padding:15px 20px;border-radius:17px;border:1px solid #E2E9E6;background:#fff;box-shadow:0 4px 16px #24454F04;overflow:hidden}.kpi.featured{background:linear-gradient(115deg,#287D8E,#246B7C);color:#fff;border-color:transparent}.kpi .label{font-size:12px;color:#73898D}.kpi.featured .label{color:#D2E6E9}.kpi .value{font-size:31px;line-height:1.35;font-weight:700;letter-spacing:.02em}.kpi .value small{font-size:13px;font-weight:400;margin-left:7px;opacity:.72}.kpi .detail{font-size:11px;color:#7B8F93}.kpi.featured .detail{color:#CBE1E5}.spark{position:absolute;right:13px;bottom:20px;width:105px;height:32px;opacity:.55;pointer-events:none}.kpi .value,.kpi .detail{position:relative;z-index:1}.timebar{display:flex;gap:20px;align-items:center;background:#fff;border:1px solid #E2E9E6;border-radius:15px;padding:13px 20px}.timebar .now{font-size:22px;font-weight:700;color:#287D8E;width:59px}.sliderwrap{flex:1;min-width:0}.sliderwrap input{display:block;width:100%;margin:0;height:12px}.ticks{display:flex;justify-content:space-between;color:#859A9D;font-size:10px;margin-top:5px}.timehint{font-size:11px;color:#859A9D}.daygrid{display:grid;gap:16px;min-height:0}.top{grid-template-columns:1.15fr 1fr 1fr}.bottom{grid-template-columns:1.15fr 1fr}.day .plotcard{background:#fff;border:1px solid #E2E9E6;border-radius:18px;box-shadow:0 6px 18px #24454F04;overflow:hidden}.day .plotcard.tinted{background:linear-gradient(140deg,#FFFFFF,#F7FAF9)}.day .plotcard.blue{background:linear-gradient(140deg,#fff,#FCF7F0)}
@media(min-width:1900px){.day{padding:26px 36px;gap:18px;grid-template-rows:68px 113px 72px minmax(310px,1fr) minmax(310px,1fr)}.kpi{padding:16px 24px}.kpi .value{font-size:34px}.cardhead{padding:17px 23px 5px}.cardhead h2{font-size:17px}}
@media(max-width:1100px){.day{height:auto;min-height:100vh;display:block;padding:20px}.dayhead{margin-bottom:20px}.brand h1{font-size:22px}.actions{flex-wrap:wrap;justify-content:end}.kpis{margin-bottom:15px}.kpi{padding:14px}.kpi .value{font-size:26px}.spark{display:none}.timebar{margin-bottom:16px}.timehint{display:none}.daygrid{margin-bottom:16px}.day .plotcard{height:330px}.top{grid-template-columns:1fr 1fr}.top .plotcard:first-child{grid-column:span 2}.bottom{grid-template-columns:1fr 1fr}}
@media(max-width:700px){.day{padding:15px 12px}.dayhead{align-items:start;gap:10px;flex-wrap:wrap}.brand{gap:10px}.brandicon{width:39px;height:39px;padding:9px}.brand h1{font-size:21px}.brand p{font-size:10px}.actions{width:100%;justify-content:start;gap:7px}.actions .btn{font-size:12px;padding:6px 10px}.yearpill{padding:6px 12px;font-size:12px}.kpis{grid-template-columns:1fr 1fr;gap:10px}.kpi{padding:13px 14px;min-height:103px}.kpi .value{font-size:27px}.kpi .value small{font-size:10px;margin-left:3px}.kpi .detail{font-size:10px}.timebar{gap:12px;padding:12px}.timebar .now{font-size:19px;width:44px}.timebar .btn{padding:6px 10px;font-size:12px}.ticks span:nth-child(even){display:none}.daygrid.top,.daygrid.bottom{grid-template-columns:1fr;gap:13px}.top .plotcard:first-child{grid-column:auto}.day .plotcard{height:315px}.daygrid{margin-bottom:13px}}

.kpi:nth-child(2){background:linear-gradient(125deg,#fff,#FDF7EF)}.kpi:nth-child(3){background:linear-gradient(125deg,#fff,#F4F8F7)}.kpi:nth-child(4){background:linear-gradient(125deg,#fff,#F3F8F8)}

.kpi:nth-child(2),.kpi:nth-child(3),.kpi:nth-child(4){background:#FFFFFF}.kpi:nth-child(2){border-top-color:#EBC49D}.kpi:nth-child(3){border-top-color:#A3C7CF}.kpi:nth-child(4){border-top-color:#CBDDDF}
'''

DAY_BODY=r'''
<main class="day">
<header class="dayhead"><div class="brand"><span class="brandicon" aria-hidden="true"><i></i><i></i><i></i></span><div><h1>全国人口 · 变化图谱</h1><p>2016—2025 · 年度人口与结构观察</p></div></div><div class="actions"><span class="yearpill" id="yearBadge">2025</span><button class="btn" data-explorer>全部指标</button><button class="btn" data-info>数据说明</button><a class="btn" href="12_人口结构观察台.html">结构观察台 ↗</a><a class="btn" href="13_人口三维探索.html">三维探索 ↗</a></div></header>
<section class="kpis" aria-label="年度关键指标">
<article class="kpi featured"><div class="label">年末总人口</div><div class="value" id="kTotal"></div><div class="detail" id="kTotalDetail"></div><svg class="spark" id="sparkTotal" viewBox="0 0 105 32"></svg></article>
<article class="kpi"><div class="label">自然增长率</div><div class="value" id="kNatural"></div><div class="detail" id="kNaturalDetail"></div><svg class="spark" id="sparkNatural" viewBox="0 0 105 32"></svg></article>
<article class="kpi"><div class="label">城镇人口比重</div><div class="value" id="kUrban"></div><div class="detail" id="kUrbanDetail"></div><svg class="spark" id="sparkUrban" viewBox="0 0 105 32"></svg></article>
<article class="kpi"><div class="label">65岁及以上人口比重</div><div class="value" id="kOld"></div><div class="detail" id="kOldDetail"></div><svg class="spark" id="sparkOld" viewBox="0 0 105 32"></svg></article>
</section>
<section class="timebar" aria-label="选择年份"><span class="now" id="yearLabel">2025</span><div class="sliderwrap"><input type="range" id="yearSlider" aria-label="年份" min="2016" max="2025" value="2025" step="1"><div class="ticks"><span>2016</span><span>2017</span><span>2018</span><span>2019</span><span>2020</span><span>2021</span><span>2022</span><span>2023</span><span>2024</span><span>2025</span></div></div><span class="timehint">点击图中年份可联动</span><button class="btn primary" id="playButton">播放</button></section>
<section class="daygrid top">
<article class="plotcard tinted"><div class="cardhead"><div><h2>人口总量轨迹</h2><p>年末总人口 · 亿人</p></div><button class="export" data-export="totalChart">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="totalChart"></div></div></article>
<article class="plotcard"><div class="cardhead"><div><h2>出生与死亡</h2><p>出生率 / 死亡率 · ‰</p></div><button class="export" data-export="ratesChart">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="ratesChart"></div></div></article>
<article class="plotcard blue"><div class="cardhead"><div><h2>城乡人口结构</h2><p>城镇 / 乡村 · 占年末总人口 %</p></div><button class="export" data-export="urbanChart">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="urbanChart"></div></div></article>
</section>
<section class="daygrid bottom">
<article class="plotcard"><div class="cardhead"><div><h2>三大年龄组</h2><p>年度人口比重 · %</p></div><button class="export" data-export="ageChart">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="ageChart"></div></div></article>
<article class="plotcard tinted"><div class="cardhead"><div><h2>抚养结构的变化</h2><p>少儿 / 老年 / 总抚养比 · %</p></div><button class="export" data-export="dependencyChart">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="dependencyChart"></div></div></article>
</section>
</main>
'''

DAY_JS=r'''
let selectedYear=2025,playing=false,playTimer=null,renderSerial=0;
function spark(id,points,c){const min=Math.min(...points),max=Math.max(...points),span=max-min||1;const coords=points.map((n,i)=>`${i*105/(points.length-1)},${29-(n-min)/span*25}`).join(' ');document.getElementById(id).innerHTML=`<polyline points="${coords}" fill="none" stroke="${c}" stroke-width="2"/>`;}
function kpis(){
 const y=selectedYear,t=v('年末总人口',y),p=v('年末总人口',y-1),nat=v('人口自然增长率',y),pn=v('人口自然增长率',y-1);
 const urban=v('城镇人口',y)/t*100,old=v('65岁及以上人口',y)/t*100;
 $('#kTotal').innerHTML=fmt(t/10000,4)+'<small>亿人</small>';$('#kTotalDetail').textContent=p===null?'较上年 —':`较上年 ${signed(t-p,0)} 万人`;
 $('#kNatural').innerHTML=signed(nat,2)+'<small>‰</small>';$('#kNaturalDetail').textContent=pn===null?'较上年 —':`较上年 ${signed(nat-pn)} ‰`;
 $('#kUrban').innerHTML=fmt(urban,2)+'<small>%</small>';$('#kUrbanDetail').textContent=`城镇人口 ${fmt(v('城镇人口',y)/10000,3)} 亿人`;
 $('#kOld').innerHTML=fmt(old,2)+'<small>%</small>';$('#kOldDetail').textContent=`65岁及以上 ${fmt(v('65岁及以上人口',y)/10000,3)} 亿人`;
 spark('sparkTotal',vs('年末总人口'),'#CFE6E8');spark('sparkNatural',vs('人口自然增长率'),C.gold);
 spark('sparkUrban',Y.map(y=>v('城镇人口',y)/v('年末总人口',y)*100),C.blue);spark('sparkOld',Y.map(y=>v('65岁及以上人口',y)/v('年末总人口',y)*100),C.teal);
}
function setYear(y){y=Number(y);if(!Y.includes(y))return;selectedYear=y;return render();}
function yearClick(p){if(Y.includes(Number(p.x)))setYear(Number(p.x));}
async function render(){
 const serial=++renderSerial,y=selectedYear;window.populationReady=false;
 $('#yearSlider').value=y;$('#yearLabel').textContent=y;$('#yearBadge').textContent=y;kpis();
 let l=layout();l.shapes=[selection(y)];l.yaxis={...l.yaxis,range:[13.88,14.18],tickvals:[13.9,14,14.1],tickformat:'.1f'};
 let total=series('年末总人口',C.blue,'年末总人口',Y,10000);total.fill='tozeroy';total.fillgradient={type:'vertical',colorscale:[[0,'rgba(40,125,142,0.02)'],[1,'rgba(40,125,142,0.18)']]};total.hovertemplate=hoverNumber('年末总人口','亿人',4);
 const jobs=[draw('totalChart',[total,mark(y,v('年末总人口',y)/10000,C.gold)],l,yearClick)];
 l=layout();l.showlegend=true;l.margin.t=25;l.yaxis.range=[0,16];l.yaxis.dtick=5;l.shapes=[selection(y)];
 jobs.push(draw('ratesChart',[...['人口出生率','人口死亡率'].map((k,i)=>({...series(k,[C.blue,C.orangeLine][i],['出生率','死亡率'][i]),hovertemplate:hoverNumber(k,'‰')})),mark(y,v('人口出生率',y),C.blue),mark(y,v('人口死亡率',y),C.orangeLine)],l,yearClick));
 l=layout();l.showlegend=true;l.margin.t=25;l.yaxis.range=[0,100];l.yaxis.ticksuffix='%';l.yaxis.dtick=25;l.shapes=[selection(y)];
 const urban=Y.map(y=>v('城镇人口',y)/v('年末总人口',y)*100);
 jobs.push(draw('urbanChart',[{type:'scatter',mode:'lines',x:Y,y:urban,name:'城镇',stackgroup:'u',line:{color:'#65A9B7',width:1},fillcolor:'#65A9B7',hovertemplate:'城镇<br>%{x}年 · %{y:.2f}%<extra></extra>'},
 {type:'scatter',mode:'lines',x:Y,y:urban.map(n=>100-n),name:'乡村',stackgroup:'u',line:{color:'#EFB885',width:1},fillcolor:'#EFB885',hovertemplate:'乡村<br>%{x}年 · %{y:.2f}%<extra></extra>'}],l,yearClick));
 l=layout();l.showlegend=true;l.margin.t=25;l.yaxis.range=[0,100];l.yaxis.ticksuffix='%';l.yaxis.dtick=25;l.barmode='stack';l.bargap=.38;
 jobs.push(draw('ageChart',['0-14岁人口','15-64岁人口','65岁及以上人口'].map((k,i)=>({type:'bar',x:Y,y:Y.map(z=>v(k,z)/v('年末总人口',z)*100),name:['0—14岁','15—64岁','65岁及以上'][i],marker:{color:[C.orange,'#BAD1D9',C.blue][i],opacity:Y.map(z=>z===y?1:.78)},hovertemplate:`${['0—14岁','15—64岁','65岁及以上'][i]}<br>%{x}年 · %{y:.2f}%<extra></extra>`})),l,yearClick));
 l=layout();l.showlegend=true;l.margin.t=25;l.yaxis.range=[0,55];l.yaxis.ticksuffix='%';l.yaxis.dtick=15;l.shapes=[selection(y)];
 jobs.push(draw('dependencyChart',['少儿抚养比','老年抚养比','总抚养比'].map((k,i)=>({...series(k,[C.orangeLine,C.blue,'#9FB8BE'][i],k.replace('抚养比','')),line:{color:[C.orangeLine,C.blue,'#9FB8BE'][i],width:i===2?1.7:2.5,dash:i===2?'dash':'solid'},hovertemplate:hoverNumber(k,'%',1)})),l,yearClick));
 await Promise.all(jobs);if(serial===renderSerial){window.populationReady=true;window.populationState={page:'annual',year:y,charts:5};}
}
$('#yearSlider').addEventListener('input',e=>setYear(e.target.value));
function stop(){playing=false;clearInterval(playTimer);$('#playButton').textContent='播放';}
$('#playButton').addEventListener('click',()=>{if(playing){stop();return;}playing=true;$('#playButton').textContent='暂停';if(selectedYear===2025)setYear(2016);playTimer=setInterval(()=>{if(selectedYear>=2025){stop();return;}setYear(selectedYear+1);},1500);});
window.setPopulationYear=setYear;render();
'''

NIGHT_CSS=r'''
body.night{background:#F8F8F3;color:#243F48}
.side .btn{background:#FFFFFF08;border-color:#55727C;color:#D7E7EA}.side .btn:hover{background:#FFFFFF13}.side .btn.primary{background:#EFB885;border-color:#EFB885;color:#284550;box-shadow:none}
.observatory .paneltag{background:#EDF3F2;color:#477887}.observatory .export{color:#789098}.shell{min-height:100vh;display:grid;grid-template-columns:224px 1fr}
.side{background:linear-gradient(165deg,#193C49,#214955 58%,#244B56);padding:32px 20px;display:flex;flex-direction:column;border-right:1px solid #375B66;min-height:100vh;box-shadow:none}
.sidelogo{width:40px;height:40px;border:1px solid #7AA4AE;border-radius:12px;display:grid;place-items:center;color:#F0BF91;font-size:22px;margin-bottom:18px;background:#FFFFFF06}
.side h1{font-size:22px;line-height:1.6;margin:0;letter-spacing:.06em;color:#F1F7F7}.side .subtitle{color:#A5C1C9;font-size:11px;margin:6px 0 30px}.tabs{display:grid;gap:9px}
.tab{border:1px solid transparent;background:none;border-radius:11px;padding:12px 14px;text-align:left;color:#B3CCD2;font-size:14px;display:flex;gap:12px;align-items:center}.tab span{font-size:11px;color:#8EB0BA}.tab.active{background:linear-gradient(105deg,#355E6B,#3D626D);border-color:#73929B;color:#F5F9F8;box-shadow:inset 3px 0 #EFB885}.tab.active span{color:#F2C69D}
.sidecontrol{margin-top:27px;padding:20px 0;border-top:1px solid #4D6E78}.sidecontrol label{font-size:11px;color:#BDD1D6}.sideyear{font-size:37px;font-weight:600;color:#EFF7F7;line-height:1.5}.sidecontrol input{width:100%;display:block;accent-color:#A5CDD5}.siderange{display:flex;justify-content:space-between;color:#A2BFC7;font-size:10px;margin-top:7px}
.sidetools{display:grid;gap:10px;margin-top:auto;padding-top:25px}.sidetools .btn{text-align:center;font-size:12px}.sidefoot{font-size:10px;color:#9FBCC5;margin-top:18px}.observatory{padding:23px 28px;display:grid;grid-template-rows:72px minmax(410px,1.5fr) minmax(255px,1fr);gap:18px;height:100vh;min-height:900px;min-width:0}
.nighthead{display:flex;align-items:center;justify-content:space-between;gap:20px}.nighthead h2{font-size:24px;color:#243F48;letter-spacing:.03em;margin:0}.nighthead p{color:#74878B;font-size:12px;margin:5px 0}.nightbadge{font-size:11px;border:1px solid #E7D4BE;background:#FAF0E5;color:#956337;padding:7px 12px;border-radius:9px;white-space:nowrap}
.focusrow{display:grid;grid-template-columns:minmax(0,1fr) 230px;gap:18px;min-height:0}.observatory .plotcard{background:#FFFFFF;border:1px solid #E2E9E6;border-radius:18px;box-shadow:0 3px 14px #24455005;overflow:hidden}
.focusrow>.plotcard{border-top-color:#AACCD2;background:#FFFFFF}
.nightbottom>.plotcard:first-child{background:#FFFFFF;border-color:#E2E9E6}.nightbottom>.plotcard:last-child{background:#FFFFFF;border-color:#E2E9E6}
.observatory .cardhead h2{color:#2B4750;font-weight:500}.observatory .cardhead p{color:#7A8C91}.statsrail{display:flex;flex-direction:column;gap:14px;min-height:0}
.railcard{flex:1;border:1px solid #DFE8E6;border-radius:16px;display:flex;flex-direction:column;justify-content:center;padding:18px 22px;position:relative;overflow:hidden;box-shadow:none}
.railcard:before{content:'';position:absolute;top:0;left:20px;width:37px;height:3px;border-radius:0 0 4px 4px;background:#BDD8DF}
.railcard:nth-child(1){background:linear-gradient(130deg,#287D8E,#246B7C);border-color:#287D8E}.railcard:nth-child(2){background:#F7E8D7;border-color:#EBD8C2}.railcard:nth-child(3){background:#E8F1F4;border-color:#D6E4E9}
.railcard:nth-child(1):before{background:#F0C69F}.railcard:nth-child(2):before{background:#DDA66F}.railcard:nth-child(3):before{background:#83ACB9}.railcard .label{font-size:12px;color:#6B8188}.railcard .value{font-size:32px;color:#243F48;line-height:1.6;font-weight:600;white-space:nowrap}.railcard:nth-child(1) .label{color:#C7E0E4}.railcard:nth-child(1) .value{color:#F3FAFA}.railcard:nth-child(2) .label{color:#8A7059}.railcard:nth-child(2) .value{color:#885A33}.railcard:nth-child(3) .value{color:#2A6574}.railcard .value small{font-size:12px;color:#76888D;margin-left:5px;font-weight:400}.railcard:nth-child(1) .value small{color:#D2E7E9}.railcard:nth-child(2) .value small{color:#93755B}.railcard .detail{font-size:10px;color:#798D92}.railcard:nth-child(1) .detail{color:#B9D8DF}.railcard:nth-child(2) .detail{color:#967B64}.nightbottom{display:grid;grid-template-columns:1.15fr 1fr;gap:18px;min-height:0}
@media(min-width:1900px){.observatory{padding:26px 34px;gap:20px;grid-template-rows:78px minmax(460px,1.5fr) minmax(300px,1fr)}.side{padding:40px 23px}.focusrow{grid-template-columns:minmax(0,1fr) 265px}.railcard .value{font-size:37px}.nighthead h2{font-size:27px}}
@media(max-width:1100px){.shell{grid-template-columns:185px 1fr}.side{padding:26px 14px}.side h1{font-size:20px}.observatory{padding:20px 18px;height:auto;min-height:100vh;display:block}.nighthead{margin-bottom:20px}.focusrow{display:block}.focusrow>.plotcard{height:500px}.statsrail{display:grid;grid-template-columns:1fr 1fr 1fr;margin:15px 0;gap:10px}.railcard{padding:12px}.railcard .value{font-size:23px}.railcard .value small{font-size:10px}.railcard .detail{font-size:9px}.nightbottom{grid-template-columns:1fr}.nightbottom>.plotcard{height:300px}}
@media(max-width:700px){.shell{display:block}.side{padding:17px 14px 13px;min-height:0;display:block;border-right:0;border-bottom:1px solid #52757F}.sidelogo{display:none}.side h1{font-size:21px}.side h1 br{display:none}.side .subtitle{font-size:10px;margin:3px 0 13px}.tabs{grid-template-columns:1fr 1fr 1fr;gap:7px}.tab{padding:9px 6px;justify-content:center;font-size:12px;gap:4px}.tab span{display:none}.sidecontrol{margin:12px 0 0;padding:11px 0 0;display:grid;grid-template-columns:1fr 80px;align-items:center;gap:3px 15px}.sidecontrol label{font-size:10px}.sideyear{grid-column:2;grid-row:1 / span 2;font-size:30px;text-align:right}.sidecontrol input{grid-column:1}.siderange{display:none}.sidetools{margin:13px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:7px}.sidetools .btn{padding:6px 9px;font-size:11px}.sidefoot{display:none}.observatory{padding:14px 12px}.nighthead{align-items:start;gap:10px;margin-bottom:14px}.nighthead h2{font-size:21px}.nighthead p{font-size:10px}.nightbadge{font-size:10px;padding:5px 8px}.focusrow>.plotcard{height:500px}.statsrail{gap:8px;margin:12px 0}.railcard{padding:10px 9px;border-radius:12px}.railcard .label{font-size:10px}.railcard .value{font-size:22px}.railcard .value small{font-size:9px;margin-left:1px}.railcard .detail{font-size:9px}.nightbottom{gap:12px}.nightbottom>.plotcard{height:290px}}
'''

NIGHT_BODY=r'''
<div class="shell"><aside class="side"><div class="sidelogo" aria-hidden="true">◒</div><h1>人口结构<br>观察台</h1><p class="subtitle">从年龄、性别到普查画像</p>
<nav class="tabs" aria-label="选择专题"><button class="tab active" data-tab="age"><span>01</span>年龄样本</button><button class="tab" data-tab="sex"><span>02</span>性别样本</button><button class="tab" data-tab="census"><span>03</span>2020普查</button></nav>
<div class="sidecontrol"><label id="sampleLabel" for="sampleSlider">抽样年份</label><div class="sideyear" id="sampleYear">2024</div><input type="range" id="sampleSlider" aria-label="抽样年份" min="0" max="7" value="7" step="1"><div class="siderange"><span>2016</span><span>2024</span></div></div>
<div class="sidetools"><button class="btn primary" id="samplePlay">播放年份</button><button class="btn" data-explorer>全部指标</button><button class="btn" data-info>数据说明</button><a class="btn" href="11_人口变化图谱.html">年度变化图谱 ↗</a><a class="btn" href="13_人口三维探索.html">三维探索 ↗</a></div><p class="sidefoot">国家统计局 · 人口数据</p></aside>
<main class="observatory"><header class="nighthead"><div><h2 id="topicTitle">年龄的层叠形状</h2><p id="topicSubtitle">抽样样本 · 男女同用总样本为分母</p></div><span class="nightbadge" id="scopeBadge">2024 · 抽样样本</span></header>
<section class="focusrow"><article class="plotcard"><div class="cardhead"><div><h2 id="focusTitle">男女年龄金字塔</h2><p id="focusUnit">占总样本 · %</p></div><button class="export" data-export="focusChart">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="focusChart"></div></div></article><div class="statsrail">
<article class="railcard"><div class="label" id="statLabel0"></div><div class="value" id="statValue0"></div><div class="detail" id="statDetail0"></div></article>
<article class="railcard"><div class="label" id="statLabel1"></div><div class="value" id="statValue1"></div><div class="detail" id="statDetail1"></div></article>
<article class="railcard"><div class="label" id="statLabel2"></div><div class="value" id="statValue2"></div><div class="detail" id="statDetail2"></div></article>
</div></section>
<section class="nightbottom"><article class="plotcard"><div class="cardhead"><div><h2 id="lowerTitle0">三大年龄组的年度切片</h2><p id="lowerUnit0">占总样本 · %</p></div><button class="export" data-export="lowerChart0">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="lowerChart0"></div></div></article>
<article class="plotcard"><div class="cardhead"><div><h2 id="lowerTitle1">年龄分布对照</h2><p id="lowerUnit1">2016与所选年 · 占总样本 %</p></div><button class="export" data-export="lowerChart1">导出 ↗</button></div><div class="chartwrap"><div class="chart" id="lowerChart1"></div></div></article></section>
</main></div>
'''

NIGHT_JS=r'''
const NC={teal:'#287D8E',blue:'#4E98AA',orange:'#EFB885',gold:'#9D6334',muted:'#6D93A0'};
let topic='age',sampleYear=2024,sampleTimer=null,samplePlaying=false,renderSerial=0;
function stats(items){items.forEach(([label,value,unit,detail],i)=>{$('#statLabel'+i).textContent=label;$('#statValue'+i).innerHTML=value+`<small>${unit}</small>`;$('#statDetail'+i).textContent=detail;});}
function titles(main,sub,focus,unit,lower0,unit0,lower1,unit1){
 $('#topicTitle').textContent=main;$('#topicSubtitle').textContent=sub;$('#focusTitle').textContent=focus;$('#focusUnit').textContent=unit;
 $('#lowerTitle0').textContent=lower0;$('#lowerUnit0').textContent=unit0;$('#lowerTitle1').textContent=lower1;$('#lowerUnit1').textContent=unit1;
}
function setSampleYear(y){y=Number(y);if(!SY.includes(y)||topic==='census')return;sampleYear=y;return renderNight();}
function setTopic(t){if(!['age','sex','census'].includes(t))return;stopSamples();topic=t;return renderNight();}
function sampleClick(p){if(topic!=='census'&&SY.includes(Number(p.x)))setSampleYear(Number(p.x));}
async function renderNight(){
 const serial=++renderSerial,y=sampleYear;window.populationReady=false;
 document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===topic);b.setAttribute('aria-pressed',b.dataset.tab===topic?'true':'false');});
 $('#sampleSlider').disabled=topic==='census';$('#samplePlay').disabled=topic==='census';$('#sampleSlider').value=SY.indexOf(y);
 $('#sampleSlider').style.display=topic==='census'?'none':'';$('.siderange').style.display=topic==='census'?'none':'';
 $('#sampleYear').textContent=topic==='census'?'2020':y;$('#sampleLabel').textContent=topic==='census'?'普查年份':'抽样年份';$('#scopeBadge').textContent=topic==='census'?'2020 · 人口普查':`${y} · 抽样样本`;
 let l=layout(true),b=layout(true),r=layout(true),traces=[],bottom=[],right=[];
 const ageLabels=A.map(a=>a.replace('-','—')),ageTicks=A.map((a,i)=>i);
 if(topic==='age'){
  titles('年龄的层叠形状','抽样样本 · 男女同用总样本为分母','男女年龄金字塔','占总样本 · %','三大年龄组的年度切片','占总样本 · %','年龄分布对照',`2016与${y} · 占总样本 %`);
  const m=profile(y,'男性'),f=profile(y,'女性'),n=v(sk(),y),ba=broad(y);
  stats([['调查样本',fmt(n/10000,2),'万人','样本人数'],['0—14岁比重',fmt(ba[0],2),'%','占当年总样本'],['65岁及以上比重',fmt(ba[2],2),'%','占当年总样本']]);
  l.margin={l:87,r:32,t:28,b:35};l.hovermode='closest';l.showlegend=true;l.barmode='relative';l.bargap=.22;
  l.xaxis={...l.xaxis,tickvals:[-5,-2.5,0,2.5,5],ticktext:['5','2.5','0','2.5','5'],range:[-5.7,5.7],showgrid:true,gridcolor:'#E6ECEA'};
  l.yaxis={...l.yaxis,tickvals:ageTicks,ticktext:ageLabels,range:[-.7,19.8],showgrid:false,tickfont:{size:11},autorange:false};
  traces=[{type:'bar',orientation:'h',x:m.map(n=>-n),y:ageTicks,name:'男性',marker:{color:NC.blue},customdata:m,hovertemplate:'男性 · %{y}<br>占总样本 %{customdata:.2f}%<extra></extra>'},
  {type:'bar',orientation:'h',x:f,y:ageTicks,name:'女性',marker:{color:NC.orange},hovertemplate:'女性 · %{y}<br>占总样本 %{x:.2f}%<extra></extra>'}];
  traces.forEach(t=>t.customdata=t.y.map((i,j)=>[ageLabels[i],Math.abs(t.x[j])]));traces.forEach(t=>t.hovertemplate=`${t.name} · %{customdata[0]}<br>占总样本 %{customdata[1]:.2f}%<extra></extra>`);
  const hy=SY.map(String),z=[0,1,2].map(i=>SY.map(y=>broad(y)[i]));
  b.margin={l:91,r:22,t:10,b:35};b.xaxis={...b.xaxis,type:'category',tickvals:hy,categoryorder:'array',categoryarray:hy,range:[-.5,hy.length-.5],tickfont:{size:10}};b.yaxis={...b.yaxis,type:'category',showgrid:false,autorange:'reversed'};
  bottom=[{type:'heatmap',x:hy,y:['0—14岁','15—64岁','65岁及以上'],z,zmin:0,zmax:75,colorscale:[[0,'#F4F8F7'],[.35,'#DFEDF0'],[.7,'#BAD8DF'],[1,'#8DBAC6']],showscale:false,xgap:4,ygap:5,
   texttemplate:'%{z:.1f}',textfont:{size:12,color:'#294F5B'},hoverongaps:false,hovertemplate:'%{x}年 · %{y}<br>占总样本 %{z:.2f}%<extra></extra>'}];
  r.margin={l:43,r:18,t:25,b:48};r.showlegend=true;r.xaxis={...r.xaxis,tickvals:[0,4,8,12,16,19],ticktext:ageLabels.filter((a,i)=>[0,4,8,12,16,19].includes(i)),range:[-.4,19.4],tickangle:-20};r.yaxis.range=[0,11];
  right=[{type:'scatter',mode:'lines',x:ageTicks,y:profile(2016),name:'2016',line:{color:NC.muted,width:1.8,dash:'dot'},customdata:ageLabels,hovertemplate:'2016 · %{customdata}<br>%{y:.2f}%<extra></extra>'},
  {type:'scatter',mode:'lines+markers',x:ageTicks,y:profile(y),name:String(y),line:{color:NC.teal,width:2.6},marker:{size:4},customdata:ageLabels,hovertemplate:`${y} · %{customdata}<br>%{y:.2f}%<extra></extra>`}];
 }else if(topic==='sex'){
  titles('性别差异的年龄截面','抽样样本 · 性别比以女性＝100','各年龄段性别比','女＝100','三大年龄组中的男女构成','占总样本 · %','总体样本性别比','女＝100 · 缺失年份不连接');
  const m=A.map(a=>v(sk(a,'男性'),y)),f=A.map(a=>v(sk(a,'女性'),y)),rat=m.map((n,i)=>n/f[i]*100),mn=v(sk(null,'男性'),y),fn=v(sk(null,'女性'),y);
  stats([['男性样本',fmt(mn/10000,2),'万人','当年抽样人数'],['女性样本',fmt(fn/10000,2),'万人','当年抽样人数'],['总体性别比',fmt(mn/fn*100,2),'','女性＝100']]);
  l.margin={l:87,r:34,t:10,b:35};l.hovermode='closest';l.xaxis={...l.xaxis,tickvals:[0,25,50,75,100,125],range:[0,135],showgrid:true,gridcolor:'#E6ECEA'};l.yaxis={...l.yaxis,tickvals:ageTicks,ticktext:ageLabels,range:[-.7,19.8],showgrid:false,tickfont:{size:11}};
  const segX=[],segY=[];rat.forEach((n,i)=>{segX.push(100,n,null);segY.push(i,i,null);});
  l.shapes=[{type:'line',xref:'x',yref:'paper',x0:100,x1:100,y0:0,y1:1,line:{color:'#9DB6BD',width:1,dash:'dot'}}];
  traces=[{type:'scatter',mode:'lines',x:segX,y:segY,line:{color:'#CCDFE2',width:3},hoverinfo:'skip'},
  {type:'scatter',mode:'markers',x:rat,y:ageTicks,marker:{size:8,color:rat.map(n=>n>=100?NC.blue:NC.orange),line:{color:rat.map(n=>n>=100?'#287D8E':'#B77B48'),width:.8}},customdata:ageLabels,hovertemplate:'%{customdata}<br>性别比 %{x:.2f}<extra></extra>'}];
  b.margin={l:84,r:25,t:25,b:35};b.showlegend=true;b.barmode='stack';b.bargap=.45;b.xaxis={...b.xaxis,type:'category',range:undefined,tickvals:undefined};b.yaxis.range=[0,80];
  bottom=['男性','女性'].map((sex,i)=>({type:'bar',x:['0—14岁','15—64岁','65岁及以上'],y:broad(y,sex),name:sex,marker:{color:[NC.blue,NC.orange][i]},hovertemplate:`${sex} · %{x}<br>占总样本 %{y:.2f}%<extra></extra>`}));
  const hy=Array.from({length:9},(_,i)=>2016+i),ratios=hy.map(y=>v(sk(),y)===null?null:v(sk(null,'男性'),y)/v(sk(null,'女性'),y)*100);
  r.margin={l:43,r:20,t:12,b:35};r.xaxis={...r.xaxis,tickvals:[2016,2018,2020,2022,2024],range:[2015.6,2024.4]};r.yaxis.range=[100,108];r.yaxis.dtick=2;r.shapes=[selection(y,true)];
  right=[{type:'scatter',mode:'lines+markers',x:hy,y:ratios,connectgaps:false,line:{color:NC.teal,width:2.5},marker:{size:6},hovertemplate:'%{x}年<br>性别比 %{y:.2f}<extra></extra>'},mark(y,mn/fn*100,NC.gold,true)];
 }else{
  titles('2020年的普查画像','人口普查 · 全国静态截面','教育程度','每十万人中的人数 · 人','城乡与性别结构','分别以各自分类合计为分母 · %','平均预期寿命','2020 · 岁');
  stats([['普查总人口',fmt(v('人口普查总人口',2020)/10000,4),'亿人','2020人口普查'],['城镇化率',fmt(v('人口普查城镇化率',2020),1),'%','原表发布值'],['家庭户规模',fmt(v('人口普查家庭户规模',2020),2),'人/户','原表发布值']]);
  const labels=['大专及以上','高中和中专','初中','小学'],edu=labels.map(n=>v('人口普查每十万人口中受'+n+'教育人口数',2020));
  l.margin={l:110,r:60,t:25,b:35};l.xaxis={...l.xaxis,tickvals:[0,10000,20000,30000,40000],ticktext:['0','1万','2万','3万','4万'],range:[0,42500],showgrid:true,gridcolor:'#E6ECEA'};l.yaxis={...l.yaxis,type:'category',showgrid:false,autorange:'reversed'};l.hovermode='closest';l.bargap=.38;
  traces=[{type:'bar',orientation:'h',x:edu,y:labels,marker:{color:[NC.blue,'#92B9C5',NC.teal,NC.orange]},text:edu.map(n=>fmt(n,0)),textposition:'outside',textfont:{color:'#243F48',size:15},cliponaxis:false,hovertemplate:'%{y}<br>每十万人中 %{x:,.0f} 人<extra></extra>'}];
  b.margin={l:66,r:28,t:25,b:35};b.xaxis={...b.xaxis,range:[0,100],tickvals:[0,25,50,75,100],ticksuffix:'%'};b.yaxis={...b.yaxis,type:'category',showgrid:false};b.barmode='stack';b.bargap=.45;b.hovermode='closest';b.showlegend=false;
  const urb=v('人口普查城镇人口数',2020),rur=v('人口普查乡村人口数',2020),male=v('人口普查男性人口数',2020),female=v('人口普查女性人口数',2020);
  const a=[urb/(urb+rur)*100,male/(male+female)*100],bb=[100-a[0],100-a[1]];
  bottom=[{type:'bar',orientation:'h',x:a,y:['城乡','性别'],marker:{color:[NC.teal,NC.blue]},text:['城镇 '+fmt(a[0],1)+'%','男性 '+fmt(a[1],1)+'%'],textposition:'inside',insidetextanchor:'middle',textfont:{color:['#FFFFFF','#102A34']},customdata:['城镇','男性'],hovertemplate:'%{customdata} · %{x:.2f}%<extra></extra>'},
   {type:'bar',orientation:'h',x:bb,y:['城乡','性别'],marker:{color:[NC.orange,NC.orange]},text:['乡村 '+fmt(bb[0],1)+'%','女性 '+fmt(bb[1],1)+'%'],textposition:'inside',textfont:{color:'#243F48'},customdata:['乡村','女性'],hovertemplate:'%{customdata} · %{x:.2f}%<extra></extra>'}];
  r.margin={l:58,r:40,t:12,b:35};r.xaxis={...r.xaxis,range:[0,93],tickvals:[0,20,40,60,80],showgrid:true,gridcolor:'#E6ECEA'};r.yaxis={...r.yaxis,type:'category',autorange:'reversed',showgrid:false};r.hovermode='closest';r.bargap=.55;
  const life=[v('男性平均预期寿命',2020),v('平均预期寿命',2020),v('女性平均预期寿命',2020)];
  right=[{type:'bar',orientation:'h',x:life,y:['男性','总体','女性'],marker:{color:[NC.blue,'#A9BFC5',NC.orange]},text:life.map(n=>fmt(n,2)),textposition:'outside',textfont:{color:'#243F48',size:13},cliponaxis:false,hovertemplate:'%{y}<br>%{x:.2f} 岁<extra></extra>'}];
 }
 await Promise.all([draw('focusChart',traces,l),draw('lowerChart0',bottom,b,topic==='age'?sampleClick:null),draw('lowerChart1',right,r,topic==='sex'?sampleClick:null)]);
 if(serial===renderSerial){window.populationReady=true;window.populationState={page:'structure',topic,year:topic==='census'?2020:y,charts:3};}
}
$('#sampleSlider').addEventListener('input',e=>setSampleYear(SY[Number(e.target.value)]));
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>setTopic(b.dataset.tab)));
function stopSamples(){samplePlaying=false;clearInterval(sampleTimer);$('#samplePlay').textContent='播放年份';}
$('#samplePlay').addEventListener('click',()=>{if(samplePlaying){stopSamples();return;}samplePlaying=true;$('#samplePlay').textContent='暂停';if(sampleYear===2024)setSampleYear(2016);sampleTimer=setInterval(()=>{const i=SY.indexOf(sampleYear);if(i===SY.length-1){stopSamples();return;}setSampleYear(SY[i+1]);},1600);});
window.setPopulationTopic=setTopic;window.setPopulationYear=setSampleYear;renderNight();
'''

def page(title,css,body,script,d,night=False):
    payload='const SNAPSHOT='+json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n'
    payload+='const YEARS='+json.dumps(YEARS)+';const SAMPLE_YEARS='+json.dumps(SAMPLE_YEARS)+';const AGES='+json.dumps(AGES,ensure_ascii=False)+';\n'
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+BASE_CSS+css+'</style><script>'+get_plotlyjs()+'</script></head><body'+(' class="night"' if night else '')+'>'+body+MODALS+'<script>'+payload+COMMON_JS+script+'</script></body></html>'

def build(d=None,out=OUT):
    d=load_data() if d is None else d;validate(d);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for name,title,css,body,script,night in [
        ('11_人口变化图谱.html','全国人口 · 变化图谱',DAY_CSS,DAY_BODY,DAY_JS,False),
        ('12_人口结构观察台.html','人口结构观察台',NIGHT_CSS,NIGHT_BODY,NIGHT_JS,True)]:
        (out/name).write_text(page(title,css,body,script,d,night),encoding='utf-8');print('HTML',name)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--data-dir',type=Path);args=parser.parse_args();build(load_data(args.data_dir),args.out)
