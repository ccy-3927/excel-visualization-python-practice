"""第三章七图共用的 Python 绘图函数；Streamlit 与 Notebook 调用同一实现。"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Patch
from matplotlib.ticker import PercentFormatter
from data_model import read_data

NAMES = ['动态柱形图', '动态跑道图', '动态南丁格尔圆环图', '动态组合图', '透视表切片器', 'VBA动态玉玦图', '动态滑珠图']
COLORS = ['#6073F3', '#0097E0', '#11A7AD', '#F5C353', '#E66B4C', '#C58AE8']
BG = '#1A1E43'
plt.rcParams.update({'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'DejaVu Sans'], 'axes.unicode_minus': False, 'font.size': 11, 'svg.fonttype': 'none'})

def load_data():
    return read_data(Path(__file__).with_name('第三章 动态图表.xlsm'))

def defaults(d):
    s = d['initial']
    return dict(sales=s['sales'], people=d['people'][0][1:].index(s['people']), rose=s['rose'], combo=s['combo'][:], departments=s['departments'][:], jade=[r[0] for r in d['jade'][1:]].index(s['jade']), beadMode=s['beadMode'], beadIndex=s['beadIndex'])

def current_table(d, i, s):
    if i in (0, 2, 5):
        key = {0:'sales', 2:'rose', 5:'jade'}[i]
        row = d[key][s[key]+1]
        return pd.DataFrame({'类别':d[key][0][1:], '数值':row[1:]}), row[0]
    if i == 1:
        return pd.DataFrame({'类别':[r[0] for r in d['people'][1:]], '数值':[r[s['people']+1] for r in d['people'][1:]]}), d['people'][0][s['people']+1]
    if i == 3:
        return pd.DataFrame({'类别':d['combo'][0][1:], **{r[0]:r[1:] for r in d['combo'][1:]}}), '销售额、利润与利润率'
    if i == 4:
        rows=[]
        for edu in d['education']:
            groups=[d['income'][dep].get(edu, {'sum':0,'count':0}) for dep in s['departments']]
            count=sum(g['count'] for g in groups)
            rows.append([edu, sum(g['sum'] for g in groups)/count if count else np.nan, count])
        return pd.DataFrame(rows, columns=['类别','数值','人数']), '、'.join(s['departments']) or '未选择部门'
    if s['beadMode'] == 0:
        return pd.DataFrame({'类别':[r[0] for r in d['bead'][1:]], '数值':[r[s['beadIndex']+1] for r in d['bead'][1:]]}), d['bead'][0][s['beadIndex']+1]
    row=d['bead'][s['beadIndex']+1]
    return pd.DataFrame({'类别':d['bead'][0][1:], '数值':row[1:]}), row[0]

def draw_chart(d, i, state=None):
    s=defaults(d) if state is None else state
    df, subtitle=current_table(d,i,s)
    fig, ax=plt.subplots(figsize=(10,6), layout='constrained')
    fig.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors='white')
    for spine in ax.spines.values(): spine.set_visible(False)
    ax.set_title(f'{i+1:02d}  {NAMES[i]} · {subtitle}', color='white', pad=22, fontsize=15)
    labels=df['类别'].tolist()
    if i in (0,4):
        values=df['数值'].to_numpy()
        bars=ax.bar(labels, np.nan_to_num(values), color=COLORS[1], width=.55)
        ax.bar_label(bars, labels=['无数据' if np.isnan(v) else f'{v:,.0f}' for v in values], padding=6, color='white')
        ax.set_ylim(0,max(1,np.nan_to_num(values).max())*1.2)
        ax.set_ylabel('平均月收入' if i==4 else '销售额（原表数值）',color='white')
        ax.yaxis.grid(True,alpha=.16); ax.set_axisbelow(True)
    elif i in (1,2,5):
        values=df['数值'].to_numpy()
        ax.set_aspect('equal'); ax.axis('off'); ax.set_xlim(-1.18,1.75); ax.set_ylim(-1.18,1.18)
        if i in (1,5):
            hole=.45 if i==1 else .35
            step=(1-hole)/len(values)
            denominator=values.sum()/2 if i==1 else .5
            for j,v in enumerate(values):
                outer=hole+(j+1)*step
                ax.add_patch(Wedge((0,0),outer,90-360*v/denominator,90,width=step*.83,facecolor=COLORS[j]))
            center=f'{values.sum():,.0f}\n公司总人数' if i==1 else subtitle
            ax.text(0,0,center,ha='center',va='center',color='white',fontsize=15)
            colors=COLORS
        else:
            start=90
            for j,v in enumerate(values):
                end=start-360*v/values.sum()
                for k,layer in enumerate(d['roseLayers']):
                    if layer[j]: ax.add_patch(Wedge((0,0),.52+(k+1)*.08,end,start,width=.081,facecolor=layer[j]))
                start=end
            colors=d['roseLayers'][0]
            ax.text(0,0,subtitle,ha='center',va='center',color='white',fontsize=15)
        legend=[f'{label}  {v:,.0f}人' if i==1 else f'{label}  {v:.0%}' for label,v in zip(labels,values)]
        ax.legend([Patch(color=colors[j]) for j in range(len(values))],legend,loc='center left',bbox_to_anchor=(.75,.5),frameon=False,labelcolor='white')
    elif i==3:
        x=np.arange(len(labels)); ax.set_xticks(x,labels)
        for j,name in enumerate(['销售额','利润']):
            if s['combo'][j]:
                bars=ax.bar(x+(j-.5)*.3,df[name],width=.28,label=name,color=COLORS[j])
                ax.bar_label(bars,padding=4,color='white',fontsize=10)
        ax.set_ylim(0,df[['销售额','利润']].to_numpy().max()*1.3)
        ax.set_ylabel('销售额 / 利润（原表数值）',color='white')
        if s['combo'][2]:
            right=ax.twinx(); right.set_ylim(0,1); right.tick_params(colors=COLORS[3]); right.yaxis.set_major_formatter(PercentFormatter(1))
            right.set_ylabel('利润率',color=COLORS[3])
            right.plot(x,df['利润率'],color=COLORS[3],marker='D',label='利润率')
            for xx,v in zip(x,df['利润率']): right.annotate(f'{v:.1%}',(xx,v),xytext=(0,-20),textcoords='offset points',ha='center',color=COLORS[3])
            for spine in right.spines.values(): spine.set_visible(False)
        if any(s['combo'][:2]): ax.legend(frameon=False,labelcolor='white',loc='upper left')
        if not any(s['combo']): ax.text(.5,.5,'请选择要显示的指标',transform=ax.transAxes,ha='center',color='white')
    else:
        values=df['数值'].to_numpy(); y=np.arange(len(labels))
        ax.barh(y,np.ones(len(y)),color='#555B77',height=.22)
        ax.barh(y,values,color=COLORS[1],height=.22)
        ax.scatter(values,y,s=260,color=COLORS[1],edgecolor='white',zorder=3)
        for yy,v in zip(y,values): ax.text(v,yy+.25,f'{v:.1%}',ha='center',color='white')
        ax.set_yticks(y,labels); ax.set_xlim(0,1.08); ax.set_ylim(-.6,len(y)-.35)
        ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.set_xlabel('销量目标达成率',color='white')
    return fig,df

if __name__=='__main__':
    print('请运行 python -m streamlit run app.py 打开动态图表，或打开第三章可视化.ipynb。')
