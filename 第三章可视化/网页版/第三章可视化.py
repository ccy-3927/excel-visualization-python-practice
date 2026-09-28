"""第三章可视化：读取源数据并生成离线交互 HTML。

安装依赖：pip install openpyxl
运行：python 第三章可视化.py
或：python 第三章可视化.py --input "第三章 动态图表.xlsm" --output "第三章可视化.html"

HTML 内嵌全部必要数据、样式和 JavaScript，直接用浏览器打开即可。
不调用 Excel、不执行 VBA、不修改原工作簿。浏览器控件实现工作簿的计算逻辑。
05 只嵌入按部门与学历汇总的收入合计和人数，多部门筛选按人数加权。
02 与06保留原图的半总量/50%占位分母；03保留六层嵌套圆环结构。
"""
from pathlib import Path
import argparse
import json
import warnings
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
import openpyxl

NS={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    's':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'x':'http://schemas.microsoft.com/office/spreadsheetml/2009/9/main'}

def read_data(path):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        book=openpyxl.load_workbook(path,read_only=True,data_only=True)
        def block(sheet,ref):return [[c.value for c in row] for row in book[sheet][ref]]
        sales=block('1 动态柱形图','B3:H9')
        people=block('2 动态跑道图','B3:F9')
        rose=block('3 动态南丁格尔圆环图','B3:G5')
        combo=block('4 动态组合图','B3:F6')
        jade=block('6 VBA动态玉玦图','B3:F5')
        bead=block('7 动态滑珠图','B2:H8')
        groups=defaultdict(lambda:defaultdict(lambda:{'sum':0,'count':0}))
        for row in book['5 人力资源明细'].iter_rows(min_row=2,values_only=True):
            department,education,income=row[2],row[3],row[6]
            if department is not None and isinstance(income,(int,float)):
                groups[department][education]['sum']+=income
                groups[department][education]['count']+=1
        initial={'sales':int(book['1 动态柱形图']['J3'].value)-1,
                 'people':book['2 动态跑道图']['Q5'].value,
                 'rose':int(book['3 动态南丁格尔圆环图']['I3'].value)-1,
                 'combo':[bool(book['4 动态组合图'][c].value) for c in ['C13','D13','E13']],
                 'jade':book['6 VBA动态玉玦图']['H3'].value,
                 'beadMode':int(book['7 动态滑珠图']['K2'].value)-1,
                 'beadIndex':int(book['7 动态滑珠图']['K3'].value)-1}
        cached_pivot={book['5 透视表切片器'][f'B{r}'].value:book['5 透视表切片器'][f'C{r}'].value for r in range(4,9)}
        book.close()
    with zipfile.ZipFile(path) as z:
        cache=ET.fromstring(z.read('xl/pivotCache/pivotCacheDefinition1.xml'))
        fields=cache.findall('s:cacheFields/s:cacheField',NS)
        dept_items=[n.get('v') for n in fields[2].find('s:sharedItems',NS)]
        slicer=ET.fromstring(z.read('xl/slicerCaches/slicerCache1.xml'))
        items=slicer.findall('.//x:items/x:i',NS)
        departments=[dept_items[int(n.get('x'))] for n in items]
        initial['departments']=[dept_items[int(n.get('x'))] for n in items if n.get('s')=='1']
        if not initial['departments']:initial['departments']=departments[:]
        chart5=ET.fromstring(z.read('xl/charts/chart5.xml'))
        stops=[{'offset':int(s.get('pos'))/1000,'color':'#'+s.find('a:srgbClr',NS).get('val')}
               for s in chart5.findall('.//c:ser/c:spPr/a:gradFill/a:gsLst/a:gs',NS)]
        chart3=ET.fromstring(z.read('xl/charts/chart3.xml'))
        layers=[]
        for series in chart3.findall('.//c:ser',NS):
            layer=[]
            for p in series.findall('c:dPt',NS):
                sp=p.find('c:spPr',NS)
                if sp.find('a:noFill',NS) is not None:layer.append(None)
                else:
                    rgb=sp.find('a:solidFill/a:srgbClr',NS)
                    layer.append('#'+rgb.get('val') if rgb is not None else '#FFC000')
            layers.append(layer)
    data={'sales':sales,'people':people,'rose':rose,'combo':combo,'jade':jade,'bead':bead,
          'income':dict(groups),'departments':departments,'education':list(cached_pivot),
          'initial':initial,'pivotGradient':stops,'roseLayers':layers}
    # 确认源数据重算与工作簿已保存的透视结果一致。
    for education,expected in cached_pivot.items():
        total=count=0
        for dep in initial['departments']:
            g=groups[dep].get(education,{'sum':0,'count':0});total+=g['sum'];count+=g['count']
        assert count and abs(total/count-expected)<1e-8,(education,total,count,expected)
    return data

def main():
    parser=argparse.ArgumentParser(description='将第三章工作簿复现为离线交互图表')
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('第三章 动态图表.xlsm'))
    parser.add_argument('--output',type=Path,default=Path(__file__).with_suffix('.html'))
    args=parser.parse_args();data=read_data(args.input)
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(TEMPLATE.replace('__CHART_DATA__',payload),encoding='utf-8')
    print(args.output.resolve())


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>第三章可视化 · 动态图表</title>
<style>
:root{color-scheme:dark;--bg:#1a1e43;--ink:#f2f2f2;--muted:#bbc2d7;--blue:#0097e0}
*{box-sizing:border-box}body{margin:0;background:#10142d;color:var(--ink);font:15px/1.55 "Microsoft YaHei","PingFang SC",sans-serif}
main{max-width:1220px;margin:auto;padding:30px 28px 26px}h1{font-size:26px;margin:0 0 5px;font-weight:600}.intro{color:var(--muted);margin:0 0 22px}
nav{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:22px}button,select{font:inherit;cursor:pointer;color:var(--ink);background:#252d57;border:1px solid #495175;border-radius:5px;padding:8px 12px}button:hover{background:#34406d}button[aria-selected="true"],button[aria-pressed="true"]{background:#006baa;border-color:#2fbdff;color:white}button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #a8ddff;outline-offset:3px}
nav button{font-size:14px}section{background:var(--bg);padding:25px 28px 18px}section[hidden]{display:none}h2{font-size:22px;margin:0 0 16px;font-weight:600}.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;min-height:44px;margin-bottom:6px}.controls label{display:inline-flex;gap:8px;align-items:center;cursor:pointer}.controls input{accent-color:#0097e0;width:17px;height:17px}.controls .spacer{flex:1}.slicer{display:flex;gap:7px;flex-wrap:wrap}.slicer button{font-size:14px}.status{color:#d1d9ee;min-height:25px;margin:9px 0 0;font-variant-numeric:tabular-nums}.chart{width:100%;min-height:450px}svg{display:block;width:100%;overflow:visible}svg text{fill:var(--ink);font-family:"Microsoft YaHei","PingFang SC",sans-serif;font-size:14px;font-variant-numeric:tabular-nums}svg .value{font-size:15px}svg .note{fill:#b8c0d9;font-size:12px}svg .grid{stroke:#d9e2ff;stroke-opacity:.18;stroke-dasharray:5 5}svg .leader{fill:none;stroke-width:1.3}svg .direct-label{font-size:14px}svg .mark{outline:none}svg .mark:hover{filter:brightness(1.2)}.source{color:#aeb8d4;font-size:12px;margin:7px 0 0}.hint{font-size:12px;color:var(--muted);margin:10px 0 0}.foot{color:#909bbd;font-size:12px;margin:16px 0 0}.export{font-size:13px;padding:6px 10px}.legend-swatch{width:12px;height:12px;display:inline-block;margin-right:6px}.data-wrap{margin-top:10px}summary{color:#bcc9e8;cursor:pointer;font-size:13px}table{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}th,td{padding:8px;text-align:left;border-bottom:1px solid #3c4264}td:not(:first-child),th:not(:first-child){text-align:right}
@media(max-width:650px){main{padding:18px 10px}section{padding:18px 12px}h1{font-size:23px}h2{font-size:18px}.intro{font-size:13px}nav{gap:5px}nav button{padding:8px;font-size:12px}.chart{min-height:410px}.controls{gap:8px}.controls .spacer{display:none}svg text{font-size:12px}svg .direct-label{font-size:12px}svg .value{font-size:13px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style>
</head>
<body><main>
<h1>第三章可视化</h1><p class="intro">切换月份、周期和筛选条件，图形与文字标注同步更新。</p>
<nav role="tablist" aria-label="图表类型"></nav>
<div id="panels"></div>
<p class="foot">数据来自《第三章 动态图表.xlsm》。本文件可离线打开，默认选择与原工作簿保存状态一致。</p>
</main>
<script id="chart-data" type="application/json">__CHART_DATA__</script>
<script>
'use strict';
// 所有计算都使用工作簿源数据。控件模拟原 INDEX / VLOOKUP / HLOOKUP / IF 和透视平均值。
const D=JSON.parse(document.getElementById('chart-data').textContent);
const BG='#1A1E43',NS='http://www.w3.org/2000/svg';
const names=['动态柱形图','动态跑道图','动态南丁格尔圆环图','动态组合图','透视表切片器','VBA动态玉玦图','动态滑珠图'];
const titles=['2022年上半年各区域销售情况','各部门人数分布','2022年6月30日流量来源分布','销售额、利润与利润率','各学历平均工资情况','流量来源分布','2022年上半年区域销量目标达成率情况'];
const sources=['公司销售系统','公司人力资源系统','公司网站','公司销售系统','人力资源管理系统，统计日期截至2022.03.31','公司网站','公司销售系统，日期截至2022.06.30'];
const state={tab:0,sales:D.initial.sales,people:D.people[0].indexOf(D.initial.people)-1,rose:D.initial.rose,combo:D.initial.combo.slice(),departments:new Set(D.initial.departments),multi:false,jade:D.jade.slice(1).findIndex(r=>r[0]===D.initial.jade),beadMode:D.initial.beadMode,beadIndex:D.initial.beadIndex};
const jobs={},drawn={},models={};
function el(tag,attrs={},text){const e=document.createElement(tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;}
function S(tag,attrs={},text,parent){const e=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;if(parent)parent.append(e);return e;}
function text(g,x,y,t,attrs={}){return S('text',{x,y,...attrs},t,g);}
function line(g,x1,y1,x2,y2,attrs={}){return S('line',{x1,y1,x2,y2,...attrs},undefined,g);}
function pct(x,d=0){return (100*x).toFixed(d)+'%';}
function num(x,d=0){return x.toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d});}
function options(select,values,selected){select.replaceChildren(...values.map((v,i)=>{const o=el('option',{value:i},v);o.selected=i===selected;return o;}));}
function selectControl(i,label,values,value,onChange,id){const l=el('label',{},label),s=el('select',{'aria-label':label,id});options(s,values,value);l.append(s);document.getElementById('controls'+i).append(l);s.onchange=()=>onChange(+s.value);return s;}
function buttonGroup(i,values,selected,onChange,id){const wrap=el('div',{class:'slicer',id,'aria-label':'周期'});values.forEach((v,j)=>{const b=el('button',{'aria-pressed':j===selected,type:'button','data-index':j},v);b.onclick=()=>{[...wrap.children].forEach((n,k)=>n.setAttribute('aria-pressed',k===j));onChange(j);};wrap.append(b);});document.getElementById('controls'+i).append(wrap);}
names.forEach((name,i)=>{const b=el('button',{id:'tab'+i,type:'button',role:'tab','aria-controls':'panel'+i,'aria-selected':i===0},String(i+1).padStart(2,'0')+' '+name);b.onclick=()=>show(i);b.onkeydown=e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();const k=(i+(e.key==='ArrowRight'?1:6))%7;show(k);document.getElementById('tab'+k).focus();}};document.querySelector('nav').append(b);
const p=el('section',{id:'panel'+i,role:'tabpanel','aria-labelledby':'tab'+i});p.hidden=i!==0;p.append(el('h2',{},titles[i]),el('div',{class:'controls',id:'controls'+i}),el('p',{class:'status',id:'status'+i,'aria-live':'polite'}),el('div',{class:'chart',id:'chart'+i}),el('p',{class:'source'},'* 注：数据来源'+sources[i]));const details=el('details',{class:'data-wrap'});details.append(el('summary',{},'查看当前数据'),el('div',{id:'table'+i}));p.append(details);document.getElementById('panels').append(p);});
selectControl(0,'月份',D.sales.slice(1).map(r=>r[0]),state.sales,v=>{state.sales=v;render(0,true);},'sales-month');
selectControl(1,'月份',D.people[0].slice(1),state.people,v=>{state.people=v;render(1,true);},'people-month');
buttonGroup(2,D.rose.slice(1).map(r=>r[0]),state.rose,v=>{state.rose=v;render(2,true);},'rose-period');
['销售额','利润','利润率'].forEach((label,j)=>{const l=el('label'),input=el('input',{type:'checkbox',id:'series'+j});input.checked=state.combo[j];input.onchange=()=>{state.combo[j]=input.checked;render(3);};const sw=el('span',{class:'legend-swatch'});sw.style.background=['#0070C0','#E74E69','#FFC000'][j];l.append(input,sw,document.createTextNode(label));document.getElementById('controls3').append(l);});
const slice=el('div',{class:'slicer',id:'department-slicer'});document.getElementById('controls4').append(slice);
D.departments.forEach(dep=>{const b=el('button',{'aria-pressed':state.departments.has(dep),type:'button','data-department':dep},dep);b.onclick=()=>{if(state.multi){if(state.departments.has(dep))state.departments.delete(dep);else state.departments.add(dep);}else state.departments=new Set([dep]);syncSlicer();render(4,true);};slice.append(b);});
const multiLabel=el('label'),multi=el('input',{type:'checkbox',id:'multi-department'});multi.onchange=()=>state.multi=multi.checked;multiLabel.append(multi,document.createTextNode('多选'));document.getElementById('controls4').append(multiLabel);
const all=el('button',{type:'button',id:'all-departments'},'全部部门');all.onclick=()=>{state.departments=new Set(D.departments);syncSlicer();render(4,true);};document.getElementById('controls4').append(all);
function syncSlicer(){[...slice.children].forEach(b=>b.setAttribute('aria-pressed',state.departments.has(b.dataset.department)));}
buttonGroup(5,D.jade.slice(1).map(r=>r[0]),state.jade,v=>{state.jade=v;render(5,true);},'jade-period');
selectControl(6,'查看方式',['按月份看各区域','按区域看各月份'],state.beadMode,v=>{state.beadMode=v;state.beadIndex=0;updateBeadSelect();render(6,true);},'bead-mode');
const beadSelect=selectControl(6,state.beadMode===0?'月份':'区域',[],0,v=>{state.beadIndex=v;render(6,true);},'bead-select');
function updateBeadSelect(){const label=state.beadMode===0?'月份':'区域';beadSelect.parentElement.firstChild.textContent=label;beadSelect.setAttribute('aria-label',label);options(beadSelect,state.beadMode===0?D.bead[0].slice(1):D.bead.slice(1).map(r=>r[0]),state.beadIndex);}
updateBeadSelect();
// SVG 导出包含全部当前文字与图形，缩放不会模糊。
names.forEach((_,i)=>{document.getElementById('controls'+i).append(el('span',{class:'spacer'}));const b=el('button',{type:'button',class:'export'},'保存当前图 SVG');b.onclick=()=>exportSVG(i);document.getElementById('controls'+i).append(b);});
function show(i){state.tab=i;names.forEach((_,j)=>{document.getElementById('panel'+j).hidden=j!==i;document.getElementById('tab'+j).setAttribute('aria-selected',j===i);});render(i);}
function getModel(i){
 if(i===0){let r=D.sales[state.sales+1];return{labels:D.sales[0].slice(1),values:r.slice(1),status:r[0]};}
 if(i===1){let values=D.people.slice(1).map(r=>r[state.people+1]);return{labels:D.people.slice(1).map(r=>r[0]),values,status:D.people[0][state.people+1]+'公司总人数为'+values.reduce((a,b)=>a+b,0)};}
 if(i===2){let r=D.rose[state.rose+1];return{labels:D.rose[0].slice(1),values:r.slice(1),status:r[0]};}
 if(i===3)return{labels:D.combo[0].slice(1),values:D.combo.slice(1,4).flatMap(r=>r.slice(1)),status:'显示：'+(['销售额','利润','利润率'].filter((_,j)=>state.combo[j]).join('、')||'无')};
 if(i===4){let rows=D.education.map(edu=>{let sum=0,count=0;state.departments.forEach(dep=>{let r=D.income[dep][edu];if(r){sum+=r.sum;count+=r.count;}});return{sum,count};});let count=rows.reduce((a,r)=>a+r.count,0),total=rows.reduce((a,r)=>a+r.sum,0);return{labels:D.education,values:rows.map(r=>r.count?r.sum/r.count:null),counts:rows.map(r=>r.count),status:state.departments.size?(state.departments.size===D.departments.length?'全部部门':[...state.departments].join('、'))+' · '+count+'人 · 平均月收入 '+(count?num(total/count,2):'—'):'未选择部门'};}
 if(i===5){let r=D.jade[state.jade+1];return{labels:D.jade[0].slice(1),values:r.slice(1),status:r[0]};}
 if(state.beadMode===0)return{labels:D.bead.slice(1).map(r=>r[0]),values:D.bead.slice(1).map(r=>r[state.beadIndex+1]),status:D.bead[0][state.beadIndex+1]+' · 各区域完成率'};
 let r=D.bead[state.beadIndex+1];return{labels:D.bead[0].slice(1),values:r.slice(1),status:r[0]+' · 各月份完成率'};
}
function render(i,animate=false){const model=getModel(i);models[i]=model;document.getElementById('status'+i).textContent=model.status;dataTable(i,model);cancelAnimationFrame(jobs[i]);
 const target=model.values.map(v=>v??0),from=drawn[i]||target;
 if(animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches){let start=performance.now();function frame(t){let k=Math.min(1,(t-start)/350),ease=1-(1-k)**3;const vals=target.map((v,j)=>from[j]+(v-from[j])*ease);drawn[i]=vals;paint(i,{...model,values:vals});if(k<1)jobs[i]=requestAnimationFrame(frame);else paint(i,model);}jobs[i]=requestAnimationFrame(frame);}
 else{drawn[i]=target;paint(i,model);}
}
function svgFor(i){const box=document.getElementById('chart'+i),w=Math.max(280,Math.round(box.clientWidth)),h=w<600?450:510;const svg=S('svg',{xmlns:NS,width:w,height:h,viewBox:`0 0 ${w} ${h}`,role:'img','aria-label':titles[i]+'，'+models[i].status});S('title',{},titles[i]+'，'+models[i].status,svg);box.replaceChildren(svg);return{svg,w,h};}
function mark(e,label,value){e.classList.add('mark');e.dataset.label=label;e.dataset.value=value;S('title',{},label+'：'+value,e);return e;}
function grid(g,w,h,max,formatter=num){const left=w<600?49:65,right=w-25,top=48,bottom=h-53;for(let k=0;k<=4;k++){let v=max*k/4,y=bottom-(bottom-top)*k/4;line(g,left,y,right,y,{class:'grid'});text(g,left-10,y+5,formatter(v),{'text-anchor':'end',class:'note'});}return{left,right,top,bottom,x:j=>left+(right-left)*(j+.5),y:v=>bottom-(bottom-top)*v/max};}
function bars(i,m){const {svg:g,w,h}=svgFor(i),max=i===0?Math.max(800,Math.ceil(Math.max(...m.values)/200)*200):Math.max(8000,Math.ceil(Math.max(...m.values.filter(v=>v!==null),0)/2000)*2000);let q=grid(g,w,h,max);text(g,q.left,25,i===4?'平均月收入':'销售额（原表数值）',{class:'note'});
 if(i===4){const defs=S('defs',{},undefined,g),gradient=S('linearGradient',{id:'income-gradient',x1:'0%',y1:'0%',x2:'0%',y2:'100%'},undefined,defs);D.pivotGradient.forEach(s=>S('stop',{offset:s.offset+'%','stop-color':s.color},undefined,gradient));}
 let span=(q.right-q.left)/m.labels.length,bw=Math.min(i===4?62:76,span*.52);
 m.labels.forEach((label,j)=>{let v=m.values[j],x=q.left+span*(j+.5);text(g,x,q.bottom+29,label,{'text-anchor':'middle'});if(v===null){text(g,x,q.bottom-12,'无数据',{'text-anchor':'middle',class:'note'});return;}let y=q.y(v);mark(S('rect',{x:x-bw/2,y,width:bw,height:q.bottom-y,fill:i===4?'url(#income-gradient)':'#0097E0'},undefined,g),label,v);text(g,x,y-10,num(v,i===4?0:0),{'text-anchor':'middle',class:'value'});});}
function polar(cx,cy,r,a){return[cx+r*Math.sin(a),cy-r*Math.cos(a)];}
function sector(cx,cy,inner,outer,start,end){let [x1,y1]=polar(cx,cy,outer,start),[x2,y2]=polar(cx,cy,outer,end),[x3,y3]=polar(cx,cy,inner,end),[x4,y4]=polar(cx,cy,inner,start);let big=end-start>Math.PI?1:0;return`M${x1},${y1} A${outer},${outer} 0 ${big} 1 ${x2},${y2} L${x3},${y3} A${inner},${inner} 0 ${big} 0 ${x4},${y4} Z`;}
function rings(i,m){const{svg:g,w,h}=svgFor(i),n=m.values.length,R=Math.min(205,(w-40)/2),hole=i===1?.45:.35,step=R*(1-hole)/n,cx=w/2,cy=(h+10)/2;let total=m.values.reduce((a,b)=>a+b,0),denom=i===1?total/2:.5;const colors=i===1?['#7030A0','#0070C0','#37A2DA','#11A7AD','#F5C353','#E74E69']:['#00B0F0','#11A7AD','#FFC000','#E74E69'];
 m.values.forEach((v,j)=>{const inner=R*hole+step*j+1.5,outer=R*hole+step*(j+1)-1,mid=(inner+outer)/2,end=2*Math.PI*v/denom;mark(S('path',{d:sector(cx,cy,inner,outer,0,end),fill:colors[j]},undefined,g),m.labels[j],i===1?Math.round(v)+'人':pct(v));
 // 标签直接对应圆弧起点，不依赖悬停或独立图例。
 text(g,cx-11,cy-mid+4,m.labels[j]+(i===1?' '+Math.round(v)+'人':''),{'text-anchor':'end',class:'direct-label'});
 if(i===5){let a=end*.55,[x,y]=polar(cx,cy,mid,a);text(g,x,y+5,pct(v),{'text-anchor':'middle',class:'value',style:'paint-order:stroke;stroke:#1a1e43;stroke-width:3px;stroke-linejoin:round'});}
 });
 if(i===1){text(g,cx,cy+9,num(total),{'text-anchor':'middle',style:'font-size:26px;font-weight:600'});text(g,cx,cy+33,'公司总人数',{'text-anchor':'middle',class:'note'});}
 else{text(g,cx,cy+10,m.status,{'text-anchor':'middle',style:'font-size:17px'});}
 if(w<600){ // 窄屏起点标签间距不足时，使用图下方完整文字行。
 [...g.querySelectorAll('.direct-label')].forEach(e=>e.remove());m.labels.forEach((label,j)=>{let x=5+(j%2)*(w/2),y=h-57+Math.floor(j/2)*21;S('circle',{cx:x+4,cy:y-4,r:4,fill:colors[j]},undefined,g);text(g,x+14,y,label+' '+(i===1?Math.round(m.values[j])+'人':pct(m.values[j])),{class:'direct-label'});});}
}
function rose(m){const{svg:g,w,h}=svgFor(2),small=w<600,R=Math.min(small?110:174,w*.245),cx=w/2,cy=small?218:255,hole=.52,step=(1-hole)/6,labels=[];let sum=m.values.reduce((a,b)=>a+b,0),start=0;
 m.values.forEach((v,j)=>{let end=start+2*Math.PI*v/sum,outer=hole;
 D.roseLayers.forEach((layer,k)=>{if(layer[j]){let ri=R*(hole+k*step),ro=R*(hole+(k+1)*step);mark(S('path',{d:sector(cx,cy,ri,ro+.2,start,end),fill:layer[j]},undefined,g),m.labels[j],pct(v));outer=ro/R;}});
 let a=(start+end)/2,p=polar(cx,cy,R*outer,a),side=Math.sin(a)>=0?1:-1;
 labels.push({j,p,side,y:p[1],text:m.labels[j]+' '+pct(v),color:D.roseLayers[0][j]});start=end;});
 text(g,cx,cy+5,m.status,{'text-anchor':'middle',style:'font-size:18px'});
 // 引导线标签按左右两侧分别排布，周期变化后重新防碰撞。
 [-1,1].forEach(side=>{let group=labels.filter(d=>d.side===side).sort((a,b)=>a.y-b.y),gap=small?37:38,min=55,max=h-55;group.forEach((d,k)=>d.y=Math.max(d.y,k?group[k-1].y+gap:min));if(group.length&&group.at(-1).y>max){let delta=group.at(-1).y-max;group.forEach(d=>d.y-=delta);}group.forEach(d=>{let tx=side>0?w-12:12,edge=side>0?cx+R+12:cx-R-12;S('polyline',{points:`${d.p[0]},${d.p[1]} ${edge},${d.y} ${tx-side*4},${d.y}`,class:'leader',stroke:d.color},undefined,g);if(small){text(g,tx,d.y-18,m.labels[d.j],{'text-anchor':side>0?'end':'start',class:'direct-label'});text(g,tx,d.y-3,pct(m.values[d.j]),{'text-anchor':side>0?'end':'start',class:'direct-label'});}else text(g,tx,d.y-8,d.text,{'text-anchor':side>0?'end':'start',class:'direct-label'});});});
}
function combo(m){const{svg:g,w,h}=svgFor(3),left=w<600?46:63,right=w-50,top=55,bottom=h-55,span=(right-left)/4,max=Math.max(3500,Math.ceil(Math.max(...m.values.slice(0,8))/500)*500),y=v=>bottom-(bottom-top)*v/max;
 text(g,left,23,'销售额 / 利润',{class:'note'});text(g,right,23,'利润率',{'text-anchor':'end',class:'note'});
 for(let k=0;k<=5;k++){let yy=bottom-(bottom-top)*k/5;line(g,left,yy,right,yy,{class:'grid'});text(g,left-9,yy+4,num(max*k/5),{'text-anchor':'end',class:'note'});if(state.combo[2])text(g,right+8,yy+4,(k*20)+'%',{class:'note'});}
 let bw=Math.min(42,span*.22),points=[];
 m.labels.forEach((label,j)=>{let x=left+(j+.5)*span;text(g,x,bottom+28,label,{'text-anchor':'middle'});for(let s=0;s<2;s++){if(!state.combo[s])continue;let v=m.values[s*4+j],xx=x+(s===0?-bw-3:3);mark(S('rect',{x:xx,y:y(v),width:bw,height:bottom-y(v),fill:s===0?'#0070C0':'#E74E69'},undefined,g),label+(s===0?'销售额':'利润'),v);text(g,xx+bw/2,y(v)-8,num(v),{'text-anchor':'middle',class:'value'});}if(state.combo[2]){let v=m.values[8+j],yy=bottom-(bottom-top)*v;points.push([x,yy,v]);}});
 if(points.length){S('polyline',{points:points.map(p=>p.slice(0,2).join(',')).join(' '),fill:'none',stroke:'#FFC000','stroke-width':3},undefined,g);points.forEach(([x,yy,v],j)=>{mark(S('circle',{cx:x,cy:yy,r:4,fill:'#FFC000'},undefined,g),m.labels[j]+'利润率',pct(v,1));text(g,x,yy+24,pct(v,1),{'text-anchor':'middle',class:'value',style:'fill:#FFC000;paint-order:stroke;stroke:#1a1e43;stroke-width:3px'});});}
 if(!state.combo.some(Boolean))text(g,w/2,h/2,'请选择要显示的指标',{'text-anchor':'middle'});
}
function beads(m){const{svg:g,w,h}=svgFor(6),left=w<600?50:68,right=w-26,top=48,bottom=h-32,span=(bottom-top)/6;[0,.25,.5,.75,1].forEach(v=>text(g,left+(right-left)*v,24,pct(v),{'text-anchor':v===0?'start':v===1?'end':'middle',class:'note'}));m.labels.forEach((label,j)=>{let v=m.values[j],y=bottom-(j+.5)*span,x=left+(right-left)*v;text(g,left-10,y+5,label,{'text-anchor':'end'});S('rect',{x:left,y:y-9,width:right-left,height:18,fill:'#5b5f79'},undefined,g);S('rect',{x:left,y:y-9,width:x-left,height:18,fill:'#0070C0'},undefined,g);mark(S('circle',{cx:x,cy:y,r:12,fill:'#0070C0',stroke:'#f2f2f2','stroke-width':1.5},undefined,g),label,pct(v,2));text(g,x,y-21,pct(v),{'text-anchor':'middle',class:'value'});});}
function paint(i,m){if(i===0||i===4)bars(i,m);else if(i===1||i===5)rings(i,m);else if(i===2)rose(m);else if(i===3)combo(m);else beads(m);}
function dataTable(i,m){const t=el('table'),head=el('tr');let headers=i===3?['类别','销售额','利润','利润率']:i===4?['学历','平均月收入','人数']:['类别',i===1?'人数':i===2||i===5?'占比':i===6?'完成率':'销售额'];headers.forEach(h=>head.append(el('th',{},h)));const thead=el('thead');thead.append(head);t.append(thead);const body=el('tbody');m.labels.forEach((label,j)=>{let row=el('tr'),vals=i===3?[label,num(m.values[j]),num(m.values[4+j]),pct(m.values[8+j],2)]:i===4?[label,m.values[j]===null?'无数据':num(m.values[j],2),num(m.counts[j])]:[label,i===2||i===5||i===6?pct(m.values[j],2):num(m.values[j])];vals.forEach(v=>row.append(el('td',{},v)));body.append(row);});t.append(body);document.getElementById('table'+i).replaceChildren(t);}
function exportSVG(i){
 cancelAnimationFrame(jobs[i]);paint(i,models[i]);
 const source=document.querySelector('#chart'+i+' svg'),w=+source.getAttribute('width'),h=+source.getAttribute('height');
 const wrap=(s,size)=>{const n=Math.max(8,Math.floor((w-40)/size));return Array.from({length:Math.ceil(s.length/n)},(_,k)=>s.slice(k*n,(k+1)*n));};
 const heading=wrap(titles[i],20),status=wrap(models[i].status,13),notes=wrap('* 注：数据来源'+sources[i],12),offset=heading.length*26+status.length*20+24,total=offset+h+notes.length*18+25;
 const svg=S('svg',{xmlns:NS,width:w,height:total,viewBox:`0 0 ${w} ${total}`});S('rect',{width:w,height:total,fill:BG},undefined,svg);
 S('style',{},'text{fill:#f2f2f2;font:14px "Microsoft YaHei",sans-serif}.note{fill:#bbc2d7;font-size:12px}',svg);
 heading.forEach((s,j)=>text(svg,20,28+j*26,s,{style:'font-size:20px;font-weight:600'}));status.forEach((s,j)=>text(svg,20,heading.length*26+26+j*20,s,{class:'note'}));
 const clone=source.cloneNode(true),originals=source.querySelectorAll('*'),copies=clone.querySelectorAll('*');
 originals.forEach((node,j)=>{const computed=getComputedStyle(node);if(copies[j].style)for(const key of ['fill','stroke','stroke-width','stroke-opacity','stroke-dasharray','font-size','font-family','font-weight','paint-order'])copies[j].style.setProperty(key,computed.getPropertyValue(key));});
 let group=S('g',{transform:`translate(0 ${offset})`},undefined,svg);[...clone.children].forEach(n=>group.append(n));
 notes.forEach((s,j)=>text(svg,20,offset+h+18+j*18,s,{class:'note'}));
 const blob=new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml;charset=utf-8'}),url=URL.createObjectURL(blob),a=el('a',{href:url,download:String(i+1).padStart(2,'0')+'_'+names[i]+'.svg'});a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
let resizeTimer;new ResizeObserver(()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>render(state.tab),100);}).observe(document.querySelector('main'));
show(0);
</script></body></html>
'''

if __name__ == '__main__': main()
