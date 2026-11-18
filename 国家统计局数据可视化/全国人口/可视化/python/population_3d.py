"""生成可离线旋转、缩放和联动年份的13_人口三维探索.html。

python population_3d.py [--out 输出目录] [--data-dir 原工作簿目录]
依赖plotly及同目录population_data.py；默认使用已经核验的内嵌工作簿快照。
API：build(d=None, out=OUT)，与其他生成器一致。

年度轨迹：x=城镇人口/年末总人口×100，y=65岁及以上人口/年末总人口×100，
z=年末总人口(万人)/10000，2016—2025，线条只表示年度先后，不表示因果。
三个数值轴按实际观测范围展开，右侧二维投影保留相同原始坐标以便准确比较。

抽样年龄脊线：x为20个有序年龄组，y为实际调查年份，z为该年龄组人数/当年
总样本×100。每个有效年份各画一条独立折线，没有插值曲面；2020未提供，
年份滑块直接跳过。样本人数不是全国人口估计，各年样本规模不同，跨年只比较
结构份额，不比较原始人数增长。95岁以上为开放组，x轴仍按年龄类别标注。
数据详细原表说明保留于population_data.py，图内只展示必要标题、单位与标识。
所有数据和完整Plotly JS内嵌，无CDN或其他联网请求。
"""
from pathlib import Path
import argparse,json
from plotly.offline import get_plotlyjs
from population_data import load_data,validate,YEARS,SAMPLE_YEARS,AGES

OUT=Path(__file__).resolve().parents[1]
CSS=r'''
*{box-sizing:border-box}body{margin:0;background:#F8F8F3;color:#243F48;font:14px/1.55 "Microsoft YaHei","Noto Sans SC",sans-serif}button,input,a{font:inherit}button,a{touch-action:manipulation}button{cursor:pointer;transition:background .18s,border-color .18s}button:hover{border-color:#8BB4BF}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #E5AD77;outline-offset:3px}a{color:inherit;text-decoration:none}button{color:#4C707B;border:1px solid #D6E4E4;background:#fff;border-radius:10px;padding:9px 14px}.primary{background:#287D8E;color:#fff;border-color:#287D8E}.page{height:100vh;min-height:880px;display:grid;grid-template-rows:79px 87px minmax(0,1fr) 27px;gap:18px;padding:26px 36px 18px;max-width:2500px;margin:auto}.header{display:flex;align-items:center;justify-content:space-between;gap:20px}.brandline{display:flex;align-items:center;gap:15px}.icon{width:43px;height:43px;border-radius:13px;background:linear-gradient(145deg,#5B9CAB,#287D8E);display:grid;place-items:center;box-shadow:0 6px 18px #287D8E16}.icon svg{width:27px;height:27px;stroke:#EFF7F7;stroke-width:1.3;fill:none}.header h1{font-size:28px;margin:0;font-weight:650;letter-spacing:.03em}.header h1 span{color:#287D8E}.header p{font-size:11px;color:#7B9095;margin:4px 0 0}.nav{display:flex;gap:8px;align-items:center}.nav a,.nav button{border:1px solid #DCE7E5;background:#fff;padding:7px 12px;font-size:12px;border-radius:9px;color:#607D86}.control{display:grid;grid-template-columns:auto minmax(200px,1fr) auto;gap:27px;align-items:center;padding:15px 20px;border-radius:16px;border:1px solid #DDE7E4;background:#fff}.modes{display:flex;gap:5px;background:#F2F6F4;border-radius:11px;padding:4px}.mode{padding:8px 15px;border-color:transparent;background:none;white-space:nowrap;font-size:13px;color:#819398}.mode.active{background:#287D8E;color:#fff;border-color:#287D8E;box-shadow:0 3px 9px #287D8E16}.timeline{display:flex;gap:20px;align-items:center;min-width:0}.year{font-size:25px;color:#287D8E;font-weight:650;min-width:61px}.year-track{flex:1;min-width:0}input[type=range]{display:block;width:100%;margin:0;accent-color:#4E98AA;cursor:pointer}.year-ticks{display:flex;justify-content:space-between;margin-top:7px;gap:3px}.year-ticks button{padding:0;border:0;border-radius:0;background:none;font-size:10px;color:#849B9E}.year-ticks button.active{color:#9D6334;font-weight:700}.actions{display:flex;gap:8px}.actions button{padding:8px 13px;font-size:12px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 377px;gap:22px;min-height:0}.stage{min-width:0;min-height:0;display:flex;flex-direction:column;border:1px solid #D5E3E1;border-radius:20px;overflow:hidden;background:radial-gradient(ellipse at 50% 60%,#F2F8F8,#FCFDFC 76%);box-shadow:0 6px 25px #24454F04}.stage-head{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:20px 25px 0}.stage-head h2{font-size:19px;margin:0;font-weight:600;color:#285563}.stage-head .hint{font-size:11px;color:#8BA1A4;white-space:nowrap}.stage-chart{flex:1;min-height:0;width:100%;position:relative}.aside{min-width:0;min-height:0;display:flex;flex-direction:column;gap:17px}.values{border:1px solid #DDE7E4;background:#fff;border-radius:17px;padding:19px 22px;display:grid;gap:15px;flex:0 0 auto}.value-row{display:flex;gap:14px;align-items:center;justify-content:space-between;min-width:0}.value-row+.value-row{border-top:1px solid #EEF3F0;padding-top:14px}.value-row span{font-size:12px;color:#6A858D;min-width:0}.value-row strong{font-size:27px;font-weight:650;color:#287D8E;letter-spacing:-.4px;white-space:nowrap;font-variant-numeric:tabular-nums}.value-row small{font-size:11px;color:#81969B;font-weight:400;margin-left:4px}.value-row:last-child strong{color:#9D6334}.projection{border:1px solid #DDE7E4;background:#fff;border-radius:17px;min-height:0;display:flex;flex-direction:column;flex:1;overflow:hidden}.projection-head{padding:19px 21px 3px}.projection-head h2{font-size:16px;color:#2E5663;margin:0;font-weight:600}.projection-head p{font-size:10px;color:#839A9F;margin:4px 0 0}.projection-chart{flex:1;min-height:0;width:100%}.footer{display:flex;align-items:center;justify-content:space-between;color:#86999D;font-size:10px;gap:14px}.footer .status{color:#9D6334}.modal{position:fixed;inset:0;background:#153B4560;backdrop-filter:blur(5px);z-index:100;display:grid;place-items:center;padding:20px}.modal[hidden]{display:none}.modalbox{background:#FBFCF9;border:1px solid #DCE7E3;border-radius:21px;padding:26px 30px;max-width:800px;max-height:86vh;overflow:auto;color:#42616B;box-shadow:0 25px 100px #193C4933}.modalhead{display:flex;align-items:center;justify-content:space-between;gap:25px}.modalhead h2{font-size:22px;margin:0;color:#243F48}.close{border:0;background:#EAF2F0;border-radius:50%;width:33px;height:33px;padding:0;font-size:23px;line-height:1}.modalbox h3{font-size:15px;color:#287D8E;margin:22px 0 7px}.modalbox p{font-size:13px;line-height:1.9;margin:0 0 12px}.modebar{display:none!important}
@media(min-width:1900px){.page{padding:28px 40px 20px;gap:20px;grid-template-rows:82px 88px minmax(0,1fr) 25px}.layout{grid-template-columns:minmax(0,1fr) 410px;gap:24px}.header h1{font-size:30px}.value-row strong{font-size:30px}.stage-head{padding:22px 28px 0}.stage-head h2{font-size:20px}}
@media(max-width:1200px){.page{padding:22px 24px;gap:16px;grid-template-rows:76px 87px minmax(0,1fr) 28px}.layout{grid-template-columns:minmax(0,1fr) 310px;gap:17px}.control{gap:15px;padding:13px 15px}.modes{padding:3px}.mode{font-size:12px;padding:8px 10px}.timeline{gap:12px}.actions{gap:6px}.actions button{padding:8px 10px}.values{padding:18px}.value-row strong{font-size:25px}.stage-head{padding:18px 20px 0}.stage-head .hint{font-size:10px}}
@media(max-width:950px){.page{height:auto;min-height:100vh;display:block}.header{margin-bottom:22px}.control{grid-template-columns:1fr auto;margin-bottom:18px;gap:14px}.modes{grid-column:1 / span 2;width:max-content}.timeline{min-width:0}.layout{display:block}.stage{height:600px}.aside{display:grid;grid-template-columns:1fr 1fr;gap:17px;margin-top:18px}.values{gap:12px}.projection{min-height:280px}.footer{margin-top:17px}}
@media(max-width:700px){.page{padding:17px 12px 18px}.header{display:block;margin-bottom:17px}.brandline{gap:10px}.icon{width:38px;height:38px;border-radius:11px}.header h1{font-size:23px}.header p{font-size:10px;margin-top:3px}.nav{margin-top:14px;gap:7px;flex-wrap:wrap}.nav a,.nav button{font-size:11px;padding:6px 10px}.control{display:flex;flex-wrap:wrap;padding:12px;gap:15px 10px;margin-bottom:14px;border-radius:14px}.modes{width:100%;display:grid;grid-template-columns:1fr 1fr}.mode{font-size:12px;padding:8px 9px}.timeline{width:100%;gap:12px}.year{min-width:48px;font-size:23px}.year-ticks button{font-size:9px}.actions{margin-left:auto;gap:8px}.actions button{padding:6px 13px;font-size:11px}.stage{height:500px;border-radius:16px}.stage-head{padding:16px 16px 0;display:block}.stage-head h2{font-size:17px}.stage-head .hint{display:block;font-size:10px;margin-top:4px}.aside{display:flex;flex-direction:column;gap:14px;margin-top:14px}.values{padding:16px 19px;border-radius:14px;gap:11px}.value-row+.value-row{padding-top:11px}.value-row strong{font-size:27px}.value-row span{font-size:12px}.projection{height:330px;min-height:330px;border-radius:14px}.projection-head{padding:17px 19px 3px}.projection-head h2{font-size:16px}.footer{font-size:9px;align-items:start;gap:10px}.footer .status{white-space:nowrap}.modal{padding:12px}.modalbox{padding:22px 20px}.modalbox p{font-size:12px}}
'''

BODY=r'''
<main class="page">
<header class="header"><div class="brandline"><div class="icon" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M16 3 28 10 28 23 16 30 4 23 4 10Z M4 10 16 17 28 10 M16 17V30 M16 3V17 M4 23 16 17 28 23"/></svg></div><div><h1>人口的<span>三维坐标</span></h1><p id="scope">全国年度人口 · 2016—2025</p></div></div><nav class="nav"><a href="11_人口变化图谱.html">年度变化图谱 ↗</a><a href="12_人口结构观察台.html">结构观察台 ↗</a><button id="infoButton">数据说明</button></nav></header>
<section class="control" aria-label="探索模式和年份"><div class="modes" aria-label="探索模式"><button class="mode active" data-mode="annual" aria-pressed="true">年度人口轨迹</button><button class="mode" data-mode="ridges" aria-pressed="false">样本年龄脊线</button></div><div class="timeline"><strong class="year" id="yearLabel">2025</strong><div class="year-track"><input type="range" id="yearRange" min="0" max="9" value="9" step="1" aria-label="探索年份"><div class="year-ticks" id="yearTicks"></div></div></div><div class="actions"><button class="primary" id="playButton">播放</button><button id="resetCamera">复位视角</button></div></section>
<section class="layout"><article class="stage"><div class="stage-head"><h2 id="stageTitle">城镇化、老龄化与人口总量</h2><span class="hint">拖动旋转 · 滚轮缩放 · 点击选年</span></div><div id="spaceChart" class="stage-chart" role="img" aria-label="人口三维探索"></div></article><aside class="aside"><section class="values" id="values" aria-label="所选年份指标"></section><section class="projection"><div class="projection-head"><h2 id="projectionTitle">城镇化 × 老龄化</h2><p id="projectionSub">同一轨迹的二维投影</p></div><div id="projectionChart" class="projection-chart" role="img" aria-label="三维图的二维对照"></div></section></aside></section>
<footer class="footer"><span id="footerNote">每个点代表一年，连线表示年度先后。</span><span class="status" id="status">2025 年</span></footer>
</main>
<div class="modal" id="infoModal" hidden role="dialog" aria-modal="true" aria-labelledby="infoTitle"><div class="modalbox"><div class="modalhead"><h2 id="infoTitle">数据与三维坐标</h2><button class="close" id="closeInfo" aria-label="关闭">×</button></div><h3>年度人口轨迹</h3><p>仅使用提供的全国年度人口表，覆盖2016—2025。横轴为城镇人口比重，纵轴为65岁及以上人口比重，高度为年末总人口（亿人）。比重均以同年年末总人口为分母，人口原单位万人除以10000转为亿人。</p><p>坐标轴按观测范围展开；连线表示年度先后，共同变化不代表因果。右侧二维图保留相同原始坐标，悬浮可查看具体数值。</p><h3>样本年龄脊线</h3><p>每条线是一年的人口抽样调查年龄分布，年龄组人数除以当年总样本人数得到比重。横轴为20个有序年龄组，纵轴为实际调查年份，高度为占总样本的百分比。95岁以上为开放年龄组，横轴使用年龄类别。</p><p>抽样样本不是全国人口估计；不同年份样本规模不同，跨年以结构份额比较。只展示2016、2017、2018、2019、2021、2022、2023、2024年，缺少的2020不补值、不插值。每年各画一条独立脊线，不生成年份间的插值曲面。</p><h3>交互方式</h3><p>拖动主图旋转，滚轮缩放；点选年度标记或脊线选择年份，也可拖动年份滑块或播放。切换年份保留当前视角，两个模式分别记忆视角；“复位视角”恢复当前模式的初始相机。原始工作簿注释及完整指标可在年度变化图谱的“全部指标”与“数据说明”中查看。</p></div></div>
'''

JS=r'''
const D=SNAPSHOT.series,Y=YEARS,SY=SAMPLE_YEARS,A=AGES;
const C={blue:'#287D8E',fill:'#4E98AA',orange:'#EFB885',orangeInk:'#9D6334',ink:'#243F48',muted:'#6B7E83',grid:'#DDE8E7',pale:'#BAD1D9'};
const $=id=>document.getElementById(id),copy=x=>JSON.parse(JSON.stringify(x));
const V=(k,y)=>D[k]?.values[String(y)]??null,fmt=(n,d=2)=>n==null?'—':n.toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d});
const sampleKey=a=>a==null?'人口数 (人口抽样调查)':a+'人口数 (人口抽样调查)';
const profiles=Object.fromEntries(SY.map(y=>[y,A.map(a=>V(sampleKey(a),y)/V(sampleKey(),y)*100)]));
const annual=Object.fromEntries(Y.map(y=>[y,{urban:V('城镇人口',y)/V('年末总人口',y)*100,old:V('65岁及以上人口',y)/V('年末总人口',y)*100,total:V('年末总人口',y)/10000}]));
const initialCamera={annual:{up:{x:0,y:0,z:1},center:{x:0,y:0,z:-.10},eye:{x:1.28,y:-1.36,z:.82},projection:{type:'perspective'}},ridges:{up:{x:0,y:0,z:1},center:{x:0,y:0,z:-.06},eye:{x:1.38,y:-1.58,z:.93},projection:{type:'perspective'}}};
const mobileCamera={annual:{up:{x:0,y:0,z:1},center:{x:0,y:0,z:-.08},eye:{x:2.15,y:-2.3,z:1.4},projection:{type:'perspective'}},ridges:{up:{x:0,y:0,z:1},center:{x:0,y:0,z:-.08},eye:{x:2.3,y:-2.7,z:1.6},projection:{type:'perspective'}}};
const cameras={...copy(initialCamera),annualMobile:copy(mobileCamera.annual),ridgesMobile:copy(mobileCamera.ridges)},lastYear={annual:2025,ridges:2024};
let mode='annual',year=2025,queue=Promise.resolve(),requested=0,playing=false,timer=null,renderingMode='annual';
const mobile=()=>innerWidth<700;
const cameraKey=m=>m+(mobile()?'Mobile':'');
const currentYears=()=>mode==='annual'?Y:SY;
function axis3(title,range,extra={}){return {title:{text:title,font:{size:mobile()?10:13,color:'#557985'}},range,gridcolor:'#C4DADB',zeroline:false,showbackground:true,backgroundcolor:'#EDF5F5',tickfont:{size:mobile()?10:12,color:'#69858D'},showspikes:false,...extra};}
function layout3(m){
 const domain=mobile()?{x:[0,1],y:[.03,.95]}:{x:[.015,.985],y:[.015,.985]};
 const scene=m==='annual'?{
  xaxis:axis3(mobile()?'城镇 / %':'城镇人口比重 / %',[58,70],{tickvals:[58,62,66,70]}),
  yaxis:axis3(mobile()?'65+ / %':'65岁及以上人口比重 / %',[10,17.5],{tickvals:[10,12,14,16]}),
  zaxis:axis3('总人口 / 亿人',[13.88,14.18],{tickvals:[13.9,14,14.1],tickformat:'.1f'}),
  aspectmode:'manual',aspectratio:{x:1.12,y:1,z:.80},
 }:{
  xaxis:axis3('年龄组',[0,19],{tickvals:[0,4,8,12,16,19],ticktext:['0—4','20—24','40—44','60—64','80—84','95+']}),
  yaxis:axis3(mobile()?'年份':'调查年份',[2015.5,2024.5],{tickvals:mobile()?[2016,2019,2021,2024]:SY,tickformat:'.0f'}),
  zaxis:axis3(mobile()?'样本 / %':'占总样本 / %',[0,Math.ceil(Math.max(...Object.values(profiles).flat()))+1],{tickvals:[0,3,6,9]}),
  aspectmode:'manual',aspectratio:{x:1.5,y:1.15,z:.78},
 };
 return {paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'Microsoft YaHei, sans-serif',color:C.ink,size:12},margin:{l:0,r:0,t:0,b:0},showlegend:false,uirevision:'camera-'+m,scene:{...scene,domain,camera:copy(cameras[cameraKey(m)]),dragmode:'orbit',bgcolor:'rgba(0,0,0,0)',uirevision:'camera-'+m}};
}
function layout2(){return {paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'Microsoft YaHei, sans-serif',color:C.muted,size:11},margin:{l:54,r:20,t:24,b:55},hovermode:'closest',showlegend:false,xaxis:{zeroline:false,showgrid:false,fixedrange:true,tickfont:{size:10},title:{font:{size:11}}},yaxis:{zeroline:false,gridcolor:C.grid,fixedrange:true,tickfont:{size:10},title:{font:{size:11}}},hoverlabel:{bgcolor:'#FFFFFF',bordercolor:'#D5E4E4',font:{color:C.ink,size:12}}};}
function values(items){$('values').innerHTML=items.map(([name,n,d,unit])=>`<div class="value-row"><span>${name}</span><strong>${fmt(n,d)}<small>${unit}</small></strong></div>`).join('');}
function updateControls(){
 const ys=currentYears();$('yearLabel').textContent=year;$('yearRange').max=ys.length-1;$('yearRange').value=ys.indexOf(year);$('yearRange').setAttribute('aria-valuetext',String(year)+'年');
 $('yearTicks').innerHTML=ys.map(y=>`<button data-year="${y}" class="${y===year?'active':''}">${y}</button>`).join('');
 $('yearTicks').querySelectorAll('button').forEach(b=>b.onclick=()=>setYear(Number(b.dataset.year)));
 document.querySelectorAll('[data-mode]').forEach(b=>{const yes=b.dataset.mode===mode;b.classList.toggle('active',yes);b.setAttribute('aria-pressed',String(yes));});
 $('scope').textContent=mode==='annual'?'全国年度人口 · 2016—2025':'人口抽样样本 · 2016—2024';
 $('status').textContent=year+' 年'+(mode==='ridges'?' · 抽样样本':'');
}
function annualTraces(y){
 const a=annual[y];return [
 {type:'scatter3d',mode:'lines+markers',x:Y.map(y=>annual[y].urban),y:Y.map(y=>annual[y].old),z:Y.map(y=>annual[y].total),customdata:Y,text:Y.map(y=>y+'年'),line:{color:'#8FB6C1',width:5},marker:{size:4.5,color:C.fill,opacity:.9,line:{color:'#FFFFFF',width:.5}},hovertemplate:'%{text}<br>城镇比重 %{x:.2f}%<br>65岁及以上 %{y:.2f}%<br>总人口 %{z:.4f} 亿人<extra></extra>'},
 {type:'scatter3d',mode:'markers+text',x:[a.urban],y:[a.old],z:[a.total],customdata:[y],text:[String(y)],textposition:'top center',textfont:{size:mobile()?15:18,color:C.orangeInk},marker:{size:7.5,color:C.orange,line:{color:'#FFFFFF',width:1.7}},hovertemplate:`${y}年<br>城镇比重 %{x:.2f}%<br>65岁及以上 %{y:.2f}%<br>总人口 %{z:.4f} 亿人<extra></extra>`}
 ];
}
function ridgeTraces(y){return SY.map(sy=>({type:'scatter3d',mode:sy===y?'lines+markers':'lines',name:String(sy),x:A.map((a,i)=>i),y:A.map(()=>sy),z:profiles[sy],customdata:A.map(()=>sy),text:A,line:{color:sy===y?C.orange:'#75A5B5',width:sy===y?6:3},opacity:sy===y?1:.52,marker:{size:3.1,color:C.orange,line:{color:C.orangeInk,width:.5}},hovertemplate:`${sy}年 · %{text}<br>占总样本 %{z:.2f}%<extra></extra>`}));}
async function render(m,y,version){
 renderingMode=m;let traces,projection,l2=layout2();
 if(m==='annual'){
  const a=annual[y];$('stageTitle').textContent='城镇化、老龄化与人口总量';$('projectionTitle').textContent='城镇化 × 老龄化';$('projectionSub').textContent='同一轨迹的二维投影';$('footerNote').textContent='每个点代表一年，连线表示年度先后。';
  values([['年末总人口',a.total,4,'亿人'],['城镇人口比重',a.urban,2,'%'],['65岁及以上比重',a.old,2,'%']]);traces=annualTraces(y);
  l2.xaxis={...l2.xaxis,title:{text:'城镇人口比重 / %',font:{size:11}},range:[58,70],tickvals:[58,62,66,70]};l2.yaxis={...l2.yaxis,title:{text:'65岁及以上 / %',font:{size:11}},range:[10,17.5],tickvals:[10,12,14,16]};
  projection=[{type:'scatter',mode:'lines+markers',x:Y.map(y=>annual[y].urban),y:Y.map(y=>annual[y].old),customdata:Y,line:{color:'#A4C2CA',width:2},marker:{size:6,color:C.fill},hovertemplate:'%{customdata}年<br>城镇比重 %{x:.2f}%<br>65岁及以上 %{y:.2f}%<extra></extra>'},
  {type:'scatter',mode:'markers+text',x:[a.urban],y:[a.old],customdata:[y],text:[String(y)],textposition:y>=2024?'bottom left':'top center',textfont:{color:C.orangeInk,size:12},marker:{size:12,color:C.orange,line:{color:'#FFFFFF',width:1.5}},hoverinfo:'skip'}];
 }else{
  const p=profiles[y];$('stageTitle').textContent='样本年龄分布的年度脊线';$('projectionTitle').textContent='所选年份的年龄剖面';$('projectionSub').textContent=`2016与${y} · 占总样本 %`;$('footerNote').textContent='每条线代表一个调查年份；年份之间不绘制插值曲面。';
  values([['调查样本',V(sampleKey(),y)/10000,2,'万人'],['0—14岁比重',p.slice(0,3).reduce((s,n)=>s+n,0),2,'%'],['65岁及以上比重',p.slice(13).reduce((s,n)=>s+n,0),2,'%']]);traces=ridgeTraces(y);
  l2.margin={l:42,r:18,t:30,b:62};l2.showlegend=true;l2.legend={orientation:'h',x:0,y:1.03,xanchor:'left',yanchor:'bottom',font:{size:10},itemclick:false,itemdoubleclick:false};
  l2.xaxis={...l2.xaxis,title:{text:'年龄组',font:{size:11}},range:[-.3,19.3],tickvals:[0,4,8,12,16,19],ticktext:['0—4','20—24','40—44','60—64','80—84','95+'],tickangle:-25};l2.yaxis={...l2.yaxis,range:[0,11],tickvals:[0,3,6,9],ticksuffix:'%'};
  projection=[{type:'scatter',mode:'lines',x:A.map((a,i)=>i),y:profiles[2016],customdata:A,name:'2016',visible:y===2016?false:true,line:{color:'#82A5B2',width:1.6,dash:'dot'},hovertemplate:'2016 · %{customdata}<br>%{y:.2f}%<extra></extra>'},
  {type:'scatter',mode:'lines+markers',x:A.map((a,i)=>i),y:p,customdata:A,name:String(y),line:{color:C.blue,width:2.5},marker:{size:4,color:C.blue},hovertemplate:`${y} · %{customdata}<br>%{y:.2f}%<extra></extra>`}];
 }
 await Promise.all([
  Plotly.react('spaceChart',traces,layout3(m),{displayModeBar:false,responsive:true,scrollZoom:true,displaylogo:false}),
  Plotly.react('projectionChart',projection,l2,{displayModeBar:false,responsive:true,scrollZoom:false,displaylogo:false})
 ]);
 $('spaceChart').removeAllListeners('plotly_click');$('spaceChart').on('plotly_click',e=>{const value=Number(e.points?.[0]?.customdata);if(currentYears().includes(value))setYear(value);});
 $('projectionChart').removeAllListeners('plotly_click');if(m==='annual')$('projectionChart').on('plotly_click',e=>{const value=Number(e.points?.[0]?.customdata);if(Y.includes(value))setYear(value);});
 $('spaceChart').removeAllListeners('plotly_relayout');$('spaceChart').on('plotly_relayout',e=>{if(e['scene.camera'])cameras[cameraKey(m)]=copy(e['scene.camera']);});
 if(version===requested){window.population3dReady=true;window.population3dState={mode:m,year:y,years:m==='annual'?Y:SY,charts:2};}
}
function schedule(){
 window.population3dReady=false;updateControls();const m=mode,y=year,version=++requested;
 queue=queue.then(()=>version===requested?render(m,y,version):null).catch(error=>{console.error(error);$('status').textContent='绘制失败，请重新打开页面';throw error;});return queue;
}
function setYear(y){y=Number(y);if(!currentYears().includes(y))return Promise.resolve(false);year=y;lastYear[mode]=y;return schedule();}
function stop(){playing=false;clearInterval(timer);$('playButton').textContent='播放';}
function setMode(m){if(!['annual','ridges'].includes(m))return Promise.resolve(false);stop();mode=m;year=lastYear[m];return schedule();}
function resetCamera(){cameras[cameraKey(mode)]=copy(mobile()?mobileCamera[mode]:initialCamera[mode]);return Plotly.relayout('spaceChart',{'scene.camera':copy(cameras[cameraKey(mode)])});}
$('yearRange').addEventListener('input',e=>setYear(currentYears()[Number(e.target.value)]));
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
$('resetCamera').addEventListener('click',resetCamera);
$('playButton').addEventListener('click',()=>{if(playing){stop();return;}playing=true;$('playButton').textContent='暂停';let ys=currentYears();if(year===ys.at(-1))setYear(ys[0]);timer=setInterval(()=>{const ys=currentYears(),i=ys.indexOf(year);if(i>=ys.length-1){stop();return;}setYear(ys[i+1]);},1700);});
let origin=null;function openInfo(){origin=document.activeElement;$('infoModal').hidden=false;document.body.style.overflow='hidden';$('closeInfo').focus();}function closeInfo(){$('infoModal').hidden=true;document.body.style.overflow='';origin?.focus();}
$('infoButton').addEventListener('click',openInfo);$('closeInfo').addEventListener('click',closeInfo);$('infoModal').addEventListener('click',e=>{if(e.target===$('infoModal'))closeInfo();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('infoModal').hidden)closeInfo();if(e.key==='Tab'&&!$('infoModal').hidden){e.preventDefault();$('closeInfo').focus();}});
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{Plotly.Plots.resize('spaceChart');Plotly.Plots.resize('projectionChart');const l=layout3(mode);Plotly.relayout('spaceChart',{'scene.domain':l.scene.domain,'scene.camera':copy(cameras[cameraKey(mode)]),'scene.xaxis':l.scene.xaxis,'scene.yaxis':l.scene.yaxis,'scene.zaxis':l.scene.zaxis});},120);});
window.population3dSetYear=setYear;window.population3dSetMode=setMode;window.population3dResetCamera=resetCamera;window.population3dGetCamera=()=>copy(cameras[cameraKey(mode)]);window.population3dData={annual,profiles};
schedule();
'''

def page(d):
    payload='const SNAPSHOT='+json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n'
    payload+='const YEARS='+json.dumps(YEARS)+';const SAMPLE_YEARS='+json.dumps(SAMPLE_YEARS)+';const AGES='+json.dumps(AGES,ensure_ascii=False)+';\n'
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全国人口 · 三维探索</title><style>'+CSS+'</style><script>'+get_plotlyjs()+'</script></head><body>'+BODY+'<script>'+payload+JS+'</script></body></html>'

def build(d=None,out=OUT):
    d=load_data() if d is None else d;validate(d);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    target=out/'13_人口三维探索.html';target.write_text(page(d),encoding='utf-8');print('HTML',target.name)
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT);parser.add_argument('--data-dir',type=Path)
    args=parser.parse_args();build(load_data(args.data_dir),args.out)
