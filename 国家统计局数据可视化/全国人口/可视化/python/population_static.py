"""重建10张人口主题PNG，4800×2700，300 dpi。

用法：python population_static.py [--out 输出目录] [--data-dir 原始工作簿目录]
默认使用population_data.py内嵌的原始快照，不依赖D盘路径。
依赖numpy、matplotlib、Pillow。中文字体优先Microsoft YaHei。

01 全国年度人口：万人÷10000=亿人；年度变化为相邻年差，2016无基值不画差值。
02 出生率、死亡率、自然增长率都用原表‰；不以人口变化替代自然增长。
03 城镇与乡村人数堆叠；圆角长方体仅为装饰，正面柱高严格对应人数。
04 各年龄段年度人口÷同年年末总人口×100；取自年度表，不混入普查比重。
05 抚养比全部使用发布值；不同人口表的舍入/修订差不人为消除。
06 男女年龄金字塔均除以同年总样本；不是全国人口估计，也非各性别内占比。
07 每格为该年龄段人数÷当年总样本×100；仅列8个有效年份，略过缺失2020，不补零或插值。
08 样本性别比=同龄男性人数÷女性人数×100，女=100；横截面不能解释为个人生存曲线。
09 普查4类教育程度并非全部互斥完备分类，不凑成100%饼图；保留每十万人单位。
10 预期寿命只有2020；共用数值刻度的点线对照，横向距离表示差值。
   女性与男性差值为80.88−75.37=5.51岁，不构造时间趋势。
PNG仅留必要标题、单位和标识，详细原表注释见population_data.py与交互HTML。
"""
from pathlib import Path
import argparse,warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap,TwoSlopeNorm,to_rgb
from matplotlib.patches import FancyBboxPatch,Rectangle,Polygon,Patch,PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.ticker import FuncFormatter
from population_data import load_data,val,vals,sample_key,sample_profile,validate,YEARS,SAMPLE_YEARS,AGES

P=dict(bg='#F8F8F3',ink='#243F48',muted='#6B7E83',grid='#E6ECEA',teal='#4A7180',
       blue='#287D8E',blue_fill='#4E98AA',gold='#9D6334',orange='#EFB885',
       orange_ink='#9D6334',orange_line='#C58B56',pale='#EEF5F5',midblue='#BAD1D9')
OUT=Path(__file__).resolve().parents[1]
QA_CALLBACK=None

def configure():
    installed={f.name for f in font_manager.fontManager.ttflist}
    font=next((f for f in ['Microsoft YaHei','Noto Sans SC','Source Han Sans SC','SimHei','PingFang SC'] if f in installed),None)
    if not font:raise RuntimeError('请安装Microsoft YaHei或Noto Sans SC等中文字体。')
    plt.rcParams.update({'font.family':font,'axes.unicode_minus':False,'font.size':16,
        'axes.labelcolor':P['muted'],'xtick.color':P['muted'],'ytick.color':P['muted'],
        'axes.edgecolor':P['grid'],'figure.facecolor':P['bg'],
        'axes.spines.top':False,'axes.spines.right':False})

def plate(fig,rect,face='white',shadow=True):
    x,y,w,h=rect
    if shadow:fig.add_artist(FancyBboxPatch((x+.002,y-.006),w,h,
        boxstyle='round,pad=.005,rounding_size=.018',transform=fig.transFigure,
        facecolor='#24454F0B',edgecolor='none',zorder=-3))
    fig.add_artist(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.005,rounding_size=.018',
        transform=fig.transFigure,facecolor=face,edgecolor='#E2E9E6',lw=.7,zorder=-2))

def base(title,period='2016—2025',board=True):
    fig=plt.figure(figsize=(16,9),facecolor=P['bg'])
    fig.text(.065,.913,title,size=30,weight='bold',color=P['ink'],va='center')
    plate(fig,(.81,.886,.135,.05),face='#EDF2EF',shadow=False)
    fig.text(.934,.911,period,size=17,color=P['muted'],ha='right',va='center')
    if board:plate(fig,(.045,.075,.91,.755))
    return fig

def axis(fig,rect=(.115,.15,.77,.59),unit=None,years=True):
    ax=fig.add_axes(rect,facecolor='none')
    ax.spines['left'].set_visible(False);ax.spines['bottom'].set_color(P['grid'])
    ax.tick_params(axis='both',length=0,pad=10,labelsize=15)
    ax.grid(axis='y',color=P['grid'],lw=.8,zorder=0);ax.set_axisbelow(True)
    if unit:ax.set_title(unit,loc='left',fontsize=16,color=P['muted'],pad=20)
    if years:
        ax.set_xticks([2016,2018,2020,2022,2024,2025]);ax.set_xlim(2015.7,2025.6)
    return ax

def arr(d,key):return np.array(vals(d,key),float)
def tone(c,light=0):
    rgb=np.array(to_rgb(c));return tuple(rgb+(1-rgb)*light) if light>=0 else tuple(rgb*(1+light))
def label_color(c):
    """浅奶杏填充保留柔和色，白底数值用独立深橙，保证可读。"""
    if c==P['orange']:return P['orange_ink']
    if c=='#92B9C5':return P['blue']
    return c
def on_fill(c):
    """填色内选深墨/白字中对比度更高的一种，不用浅橙承载白字。"""
    def lum(color):
        rgb=np.array(to_rgb(color));linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        return float(linear@np.array([.2126,.7152,.0722]))
    light=lum(c);ink=lum(P['ink'])
    return P['ink'] if (light+.05)/(ink+.05)>=1.05/(light+.05) else 'white'
def endpoint(ax,x,y,label,c,offset=(12,0),size=18):
    ax.annotate(label,(x,y),xytext=offset,textcoords='offset points',color=label_color(c),
        va='center',weight='bold',size=size,annotation_clip=False)
def area(ax,x,lower,upper,c,zorder=1):
    lower=np.broadcast_to(np.asarray(lower,float),len(x));upper=np.asarray(upper,float)
    poly=ax.fill_between(x,lower,upper,color='none')
    im=ax.imshow(np.linspace(0,1,256).reshape(-1,1),origin='lower',aspect='auto',
        extent=[min(x),max(x),float(np.min(lower)),float(np.max(upper))],
        cmap=LinearSegmentedColormap.from_list('area',[tone(c,.94),tone(c,.58)]),zorder=zorder)
    im.set_clip_path(poly.get_paths()[0],transform=ax.transData)
def line(ax,x,y,c,label=None,lw=3,marker=True):
    ax.plot(x,y,lw=lw,color=c,label=label,zorder=4,solid_capstyle='round')
    if marker:ax.scatter(x,y,s=42,facecolor='white',edgecolor=c,lw=1.6,zorder=5)
def badge(fig,x,y,big,small,c):
    fig.text(x,y,big,color=c,size=36,weight='bold')
    fig.text(x,y-.052,small,color=P['muted'],size=16)

def total_population(d):
    fig=base('人口总量与年度变化',board=False)
    plate(fig,(.045,.075,.555,.755));plate(fig,(.62,.075,.335,.755),face='#FBFCFA')
    ax=axis(fig,(.11,.18,.43,.53),'年末总人口 / 亿人')
    y=arr(d,'年末总人口')/10000
    area(ax,YEARS,13.88,y,P['blue']);line(ax,YEARS,y,P['blue'])
    ax.set_ylim(13.88,14.18);ax.set_yticks([13.9,14.0,14.1])
    peak=int(np.argmax(y));ax.scatter([YEARS[peak]],[y[peak]],s=100,c=P['gold'],edgecolor='white',lw=2,zorder=6)
    endpoint(ax,YEARS[peak],y[peak],f'{y[peak]:.4f}',P['gold'],(-20,23))
    endpoint(ax,2025,y[-1],f'{y[-1]:.4f}',P['blue'],(-73,-24))
    ax.set_xticks([2016,2019,2022,2025]);ax.set_xlim(2015.6,2025.4)
    ax2=axis(fig,(.682,.18,.22,.53),'较上年增减 / 万人',False)
    changes=np.diff(arr(d,'年末总人口'));xs=np.arange(9)
    ax2.axhline(0,color=P['muted'],lw=1)
    ax2.bar(xs,changes,width=.58,color=[P['blue_fill'] if v>=0 else P['orange'] for v in changes],zorder=3)
    ax2.set_xticks([0,3,6,8],['2017','2020','2023','2025']);ax2.set_ylim(-500,1000)
    ax2.set_yticks([-400,0,400,800]);ax2.tick_params(labelsize=14)
    for i in [0,4,8]:ax2.text(i,changes[i]+(40 if changes[i]>0 else -40),f'{changes[i]:+.0f}',
        ha='center',va='bottom' if changes[i]>0 else 'top',size=17,weight='bold',color=P['blue'] if changes[i]>0 else P['orange_ink'])
    return fig

def birth_death(d):
    fig=base('出生、死亡与自然增长')
    ax=axis(fig,(.11,.43,.77,.29),'出生率与死亡率 / ‰')
    b,death,natural=[arr(d,n) for n in ['人口出生率','人口死亡率','人口自然增长率']]
    ax.fill_between(YEARS,b,death,where=b>=death,interpolate=True,color='#DCEDEF',alpha=.75)
    ax.fill_between(YEARS,b,death,where=b<death,interpolate=True,color='#FAE9D7',alpha=.8)
    line(ax,YEARS,b,P['blue'],'出生率');line(ax,YEARS,death,P['orange_line'],'死亡率',marker=False)
    ax.lines[-1].set_linestyle((0,(5,2)))
    ax.set_ylim(0,16);ax.set_yticks([0,5,10,15]);ax.tick_params(labelbottom=False)
    ax.legend(loc='upper right',ncol=2,frameon=False,bbox_to_anchor=(1.0,1.3),fontsize=16)
    endpoint(ax,2025,b[-1],f'{b[-1]:.2f}',P['blue'],(15,-4))
    endpoint(ax,2025,death[-1],f'{death[-1]:.2f}',P['orange'],(15,3))
    ax2=axis(fig,(.11,.16,.77,.19),'自然增长率 / ‰')
    ax2.axhline(0,color=P['muted'],lw=1)
    ax2.bar(YEARS,natural,width=.52,color=[P['blue_fill'] if v>=0 else P['orange'] for v in natural],zorder=3)
    ax2.set_ylim(-3.8,8);ax2.set_yticks([-3,0,3,6])
    for i in [0,5,9]:
        ax2.text(YEARS[i],natural[i]+(.3 if natural[i]>=0 else -.35),f'{natural[i]:+.2f}',
            ha='center',va='bottom' if natural[i]>=0 else 'top',size=16,color=P['blue'] if natural[i]>=0 else P['orange_ink'],weight='bold')
    return fig

def urban_cuboids(d):
    fig=base('城乡人口，城镇比重持续提高')
    ax=axis(fig,unit='人口 / 亿人')
    total=arr(d,'年末总人口')/10000;urban=arr(d,'城镇人口')/10000;rural=arr(d,'乡村人口')/10000
    ax.set_ylim(0,17);ax.set_yticks([0,5,10,15]);ax.set_xlim(2015.45,2025.95)
    width=.55;dx=.13;dy=.38;colors=['#65A9B7','#EFC39C']
    def softened(points):
        pts=ax.transData.transform(np.asarray(points,float));before=[];after=[];radius=3.7*fig.dpi/72
        for i,p in enumerate(pts):
            a,b=pts[(i-1)%len(pts)]-p,pts[(i+1)%len(pts)]-p
            before.append(p+a/np.linalg.norm(a)*min(radius,np.linalg.norm(a)*.3))
            after.append(p+b/np.linalg.norm(b)*min(radius,np.linalg.norm(b)*.3))
        vertices=[before[0]];codes=[MplPath.MOVETO]
        for i,p in enumerate(pts):
            vertices.extend([p,after[i],before[(i+1)%len(pts)]])
            codes.extend([MplPath.CURVE3,MplPath.CURVE3,MplPath.LINETO])
        vertices.append(before[0]);codes.append(MplPath.CLOSEPOLY)
        return MplPath(ax.transData.inverted().transform(vertices),codes)
    for i,x in enumerate(YEARS):
        left,right,t=x-width/2,x+width/2,total[i]
        outline=softened([(left,0),(right,0),(right+dx,dy),(right+dx,t+dy),(left+dx,t+dy),(left,t)])
        clip=PathPatch(outline,facecolor='none',edgecolor='none');ax.add_patch(clip)
        bottom=0
        for h,c in zip([urban[i],rural[i]],colors):
            top=bottom+h
            side=Polygon([(right,bottom),(right+dx,bottom+dy),(right+dx,top+dy),(right,top)],
                facecolor=tone(c,-.18),edgecolor='none',zorder=2);side.set_clip_path(clip);ax.add_patch(side)
            im=ax.imshow(np.linspace(0,1,200)[None,:],extent=[left,right,bottom,top],origin='lower',aspect='auto',
                cmap=LinearSegmentedColormap.from_list('front',[tone(c,.15),c,tone(c,-.04)]),zorder=3);im.set_clip_path(clip)
            if bottom>0:
                seam=ax.plot([left,right,right+dx],[bottom,bottom,bottom+dy],color='#FFFFFFCC',lw=1,zorder=4)[0];seam.set_clip_path(clip)
            bottom=top
        cap=Polygon([(left,t),(right,t),(right+dx,t+dy),(left+dx,t+dy)],facecolor=tone(colors[-1],.3),edgecolor='none',zorder=4)
        cap.set_clip_path(clip);ax.add_patch(cap)
        ax.add_patch(PathPatch(outline,facecolor='none',edgecolor='#4C7C8825',lw=.5,zorder=5))
    for i in [0,4,9]:
        ax.text(YEARS[i]+.04,total[i]+.8,f'{urban[i]/total[i]*100:.1f}%',ha='center',size=20,color=P['blue'],weight='bold')
    ax.legend(handles=[Patch(color=c,label=n) for c,n in zip(colors,['城镇','乡村'])],
        loc='upper center',bbox_to_anchor=(.5,1.16),ncol=2,frameon=False,fontsize=16)
    return fig

def annual_age(d):
    fig=base('年龄结构，少儿与老年占比接近')
    ax=axis(fig,(.14,.15,.73,.59),'占年末总人口 / %',False)
    keys=['0-14岁人口','15-64岁人口','65岁及以上人口'];colors=[P['orange'],P['midblue'],P['blue']]
    total=arr(d,'年末总人口');profiles=np.array([arr(d,n)/total*100 for n in keys])
    ax.axhspan(8.5,9.5,color='#F0F6F5',zorder=0)
    for i in range(10):
        track=FancyBboxPatch((0,i-.31),100,.62,boxstyle='round,pad=0,rounding_size=.22',facecolor='none',edgecolor='none')
        ax.add_patch(track);left=0
        for j,c in enumerate(colors):
            w=profiles[j,i];r=Rectangle((left,i-.31),w,.62,facecolor=c,edgecolor='none',zorder=3);r.set_clip_path(track);ax.add_patch(r)
            if j!=1 or i in [0,9]:
                ax.text(left+w/2,i,f'{w:.1f}',color=on_fill(c),ha='center',va='center',size=15,weight='bold',zorder=4)
            left+=w
    ax.set_yticks(range(10),[str(y) for y in YEARS]);ax.set_xticks([0,25,50,75,100])
    ax.set_xlim(0,100);ax.set_ylim(9.7,-.8);ax.grid(False);ax.spines['bottom'].set_visible(False)
    ax.legend(handles=[Patch(color=c,label=n) for c,n in zip(colors,['0—14岁','15—64岁','65岁及以上'])],
        loc='lower center',bbox_to_anchor=(.5,1.09),ncol=3,frameon=False,fontsize=16)
    return fig

def dependency(d):
    fig=base('抚养结构，从少儿侧向老年侧移动',board=False)
    plate(fig,(.045,.075,.55,.755));plate(fig,(.615,.075,.34,.755),face='#F4F8F7')
    ax=axis(fig,(.115,.16,.425,.55),'少儿与老年抚养比 / %',False)
    a,b=arr(d,'少儿抚养比'),arr(d,'老年抚养比')
    for i in range(10):
        ax.plot([a[i],b[i]],[i,i],color='#D6E3E4',lw=5,zorder=2,solid_capstyle='round')
        ax.scatter([a[i],b[i]],[i,i],c=[P['orange'],P['teal']],s=100,edgecolor=[tone(P['orange_ink'],.2),'white'],lw=1.1,zorder=3)
    ax.set_yticks(range(10),YEARS);ax.set_ylim(10.2,-.8);ax.set_xlim(0,32);ax.set_xticks([0,10,20,30])
    ax.grid(False);ax.grid(axis='x',color=P['grid'],lw=.8);ax.spines['bottom'].set_visible(False)
    ax.legend(handles=[plt.Line2D([0],[0],marker='o',color='none',markerfacecolor=c,markeredgecolor='none',markersize=10,label=n)
        for c,n in [(P['orange'],'少儿'),(P['teal'],'老年')]],loc='lower center',bbox_to_anchor=(.55,1.08),ncol=2,frameon=False,fontsize=16)
    # 末年两个点很接近：标签放到该行下方两侧，留出独立空白，不盖住点和连接线。
    for x,c,offset,align in [(a[-1],P['orange'],(-14,-17),'right'),(b[-1],P['teal'],(14,-17),'left')]:
        ax.annotate(f'{x:.1f}',(x,9),xytext=offset,textcoords='offset points',ha=align,va='top',
                    size=17,weight='bold',color=label_color(c),
                    bbox=dict(boxstyle='round,pad=.12',facecolor='white',edgecolor='none'))
    ax2=axis(fig,(.677,.19,.218,.52),'总抚养比 / %')
    t=arr(d,'总抚养比');area(ax2,YEARS,0,t,P['blue']);line(ax2,YEARS,t,P['blue'],marker=False)
    ax2.set_ylim(0,56);ax2.set_xticks([2016,2020,2025]);ax2.set_xlim(2015.6,2025.4);ax2.set_yticks([0,15,30,45])
    endpoint(ax2,2025,t[-1],f'{t[-1]:.1f}',P['blue'],(-52,20),22)
    return fig

def pyramid(d):
    fig=base('年龄金字塔 · 抽样样本','2024')
    ax=axis(fig,(.16,.155,.68,.58),'占总样本 / %',False)
    y=np.arange(20);m=np.array(sample_profile(d,2024,'男性'));f=np.array(sample_profile(d,2024,'女性'))
    ax.barh(y,-m,height=.7,color=P['blue_fill'],zorder=3);ax.barh(y,f,height=.7,color=P['orange'],zorder=3)
    ax.set_yticks(y,[a.replace('-','—') for a in AGES]);ax.tick_params(axis='y',labelsize=13,pad=16)
    ax.set_ylim(-.7,19.8);ax.set_xlim(-5.4,5.4);ax.set_xticks([-5,-2.5,0,2.5,5])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{abs(v):g}'))
    ax.grid(False);ax.grid(axis='x',color=P['grid'],lw=.8);ax.axvline(0,color='white',lw=1,zorder=4)
    ax.legend(handles=[Patch(color=P['blue_fill'],label='男性'),Patch(color=P['orange'],label='女性')],
        loc='lower center',bbox_to_anchor=(.5,1.065),frameon=False,ncol=2,fontsize=17)
    for i in [2,7,11]:
        ax.text(-m[i]-.1,i,f'{m[i]:.2f}',ha='right',va='center',color=P['blue'],size=13)
        ax.text(f[i]+.1,i,f'{f[i]:.2f}',ha='left',va='center',color=P['orange_ink'],size=13)
    return fig

def age_heatmap(d):
    fig=base('年龄分布的年度切片 · 抽样样本','2016—2024')
    ax=fig.add_axes((.15,.16,.68,.59));years=SAMPLE_YEARS
    z=np.array([[val(d,sample_key(a),y)/val(d,sample_key(),y)*100 for y in years] for a in AGES])
    cmap=LinearSegmentedColormap.from_list('soft',['#F4F8F7','#D7E9EB','#A4CCD4','#79AFBD'])
    im=ax.imshow(z,cmap=cmap,vmin=0,vmax=9,aspect='auto',origin='lower')
    ax.set_xticks(range(len(years)),years);ax.set_yticks(range(20),[a.replace('-','—') for a in AGES]);ax.tick_params(length=0,pad=11,labelsize=12)
    ax.set_xticks(np.arange(-.5,len(years),1),minor=True);ax.set_yticks(np.arange(-.5,20,1),minor=True)
    ax.grid(which='minor',color='white',linewidth=2);ax.tick_params(which='minor',length=0)
    for s in ax.spines.values():s.set_visible(False)
    for r in range(20):
        for c in range(len(years)):
            ax.text(c,r,f'{z[r,c]:.1f}',ha='center',va='center',size=12,color=P['ink'])
    cax=fig.add_axes((.87,.25,.013,.40));cb=fig.colorbar(im,cax=cax,ticks=[0,3,6,9]);cb.outline.set_visible(False)
    cb.ax.tick_params(length=0,pad=10,labelsize=14);cax.set_title('%',fontsize=16,color=P['muted'],pad=16)
    fig.text(.15,.791,'占总样本 / %',size=16,color=P['muted'])
    return fig

def sex_ratio(d):
    fig=base('样本性别比的年龄差异','2024')
    ax=axis(fig,(.16,.155,.68,.58),'性别比 / 女＝100',False)
    m=np.array(sample_profile(d,2024,'男性',False));f=np.array(sample_profile(d,2024,'女性',False));r=m/f*100
    ax.axvspan(100,135,color='#F1F7F7',zorder=0);ax.axvline(100,color='#A5BCC1',lw=1.3,ls=(0,(4,4)),zorder=1)
    for i,v in enumerate(r):
        c=P['blue'] if v>=100 else P['orange'];ax.hlines(i,min(v,100),max(v,100),color=tone(c,.65),lw=4,zorder=2)
        ax.scatter([v],[i],s=85,facecolor=c,edgecolor=label_color(c) if c==P['orange'] else 'white',lw=.8,zorder=3)
    ax.set_yticks(range(20),[a.replace('-','—') for a in AGES]);ax.tick_params(axis='y',labelsize=13,pad=16)
    ax.set_ylim(-.7,19.8);ax.set_xlim(0,135);ax.set_xticks([0,25,50,75,100,125])
    ax.grid(False);ax.grid(axis='x',color=P['grid'],lw=.7)
    for i in [0,2,11,19]:endpoint(ax,r[i],i,f'{r[i]:.1f}',P['blue'] if r[i]>=100 else P['orange'],(10,0),15)
    return fig

EDU_NAMES=['大专及以上','高中和中专','初中','小学']
EDU_KEYS=['人口普查每十万人口中受'+x+'教育人口数' for x in EDU_NAMES]
def education(d):
    fig=base('教育程度的人口截面','2020普查',False)
    plate(fig,(.045,.075,.615,.755));plate(fig,(.68,.075,.275,.755),face='#FBF1E6')
    ax=axis(fig,(.19,.22,.405,.43),'每十万人中的人数 / 人',False)
    values=[val(d,k,2020) for k in EDU_KEYS];colors=[P['blue'],'#92B9C5',P['teal'],P['orange']]
    for i,(v,c) in enumerate(zip(values,colors)):
        patch=FancyBboxPatch((0,i-.27),v,.54,boxstyle='round,pad=0,rounding_size=.12',facecolor=c,edgecolor='none',zorder=3);ax.add_patch(patch)
        ax.text(v+700,i,f'{v:,.0f}',ha='left',va='center',size=20,color=label_color(c),weight='bold')
    ax.set_yticks(range(4),EDU_NAMES);ax.set_ylim(3.7,-.7);ax.set_xlim(0,42500)
    ax.set_xticks([0,10000,20000,30000,40000],['0','1万','2万','3万','4万']);ax.tick_params(axis='y',labelsize=18,pad=18)
    ax.grid(False);ax.grid(axis='x',color=P['grid'],lw=.8);ax.spines['bottom'].set_visible(False)
    badge(fig,.725,.58,f'{val(d,"人口普查文盲率",2020):.1f}%', '文盲率',P['teal'])
    fig.text(.725,.36,f'{val(d,"人口普查文盲人口数",2020):,.0f} 万人',color=P['ink'],size=25,weight='bold')
    fig.text(.725,.304,'文盲人口',color=P['muted'],size=16)
    return fig

def longevity(d):
    fig=base('平均预期寿命的点线对照','2020')
    ax=axis(fig,(.115,.22,.77,.51),'平均预期寿命 / 岁',False)
    male,total,female=[val(d,k,2020) for k in ['男性平均预期寿命','平均预期寿命','女性平均预期寿命']]
    ax.set_xlim(72,84);ax.set_ylim(-.9,1.25);ax.set_yticks([])
    ax.set_xticks([72,74,76,78,80,82,84]);ax.grid(False)
    for spine in ax.spines.values():spine.set_visible(False)
    ax.spines['bottom'].set_visible(True);ax.spines['bottom'].set_position(('data',-.60))
    ax.tick_params(axis='x',pad=14,labelsize=15)
    ax.hlines(0,72,84,color='#EFF4F3',lw=7,zorder=1)
    # 连接线只是同一数值轴上的差距，不表示时间变化。
    ax.plot([male,total],[0,0],color=P['blue'],lw=6,solid_capstyle='round',zorder=2)
    ax.plot([total,female],[0,0],color=P['orange'],lw=6,solid_capstyle='round',zorder=2)
    for x,c,name,marker in [(male,P['blue'],'男性','s'),(total,P['teal'],'总体','o'),(female,P['orange'],'女性','D')]:
        ax.vlines(x,-.60,-.53,color=tone(c,.55),lw=1.2,zorder=1)
        ax.scatter([x],[0],s=1050,color=c,alpha=.08,edgecolors='none',zorder=3)
        ax.scatter([x],[0],s=310,color=c,marker=marker,edgecolors='white',lw=2.8,zorder=4)
        ax.text(x,-.19,f'{x:.2f}',ha='center',va='top',size=30,color=label_color(c),weight='bold')
        ax.text(x,-.40,name,ha='center',va='top',size=18,color=P['muted'])
    ax.annotate('',xy=(female,.49),xytext=(male,.49),arrowprops=dict(arrowstyle='<->',color='#90ACB3',lw=1.5))
    ax.vlines([male,female],.25,.61,color='#C7DADC',lw=1)
    middle=(male+female)/2
    ax.text(middle,.88,f'{female-male:.2f} 岁',ha='center',va='center',size=38,color=P['orange_ink'],weight='bold')
    ax.text(middle,.65,'女性与男性之差',ha='center',va='center',size=16,color=P['muted'])
    return fig

FIGURES=[('01_人口总量与年度变化.png',total_population),('02_出生死亡与自然增长.png',birth_death),
    ('03_城乡人口圆角立体柱.png',urban_cuboids),('04_年度年龄结构.png',annual_age),
    ('05_抚养结构变化.png',dependency),('06_样本年龄金字塔.png',pyramid),
    ('07_样本年龄分布热力图.png',age_heatmap),('08_样本年龄性别比.png',sex_ratio),
    ('09_普查教育程度.png',education),('10_平均预期寿命.png',longevity)]

def build(d=None,out=OUT,preview_dir=None):
    d=load_data() if d is None else d;validate(d);configure();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if preview_dir:Path(preview_dir).mkdir(parents=True,exist_ok=True)
    for name,draw in FIGURES:
        fig=draw(d)
        if QA_CALLBACK:QA_CALLBACK(fig,name)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');fig.savefig(out/name,dpi=300)
        missing=[str(w.message) for w in caught if 'Glyph' in str(w.message)]
        if missing:raise RuntimeError(f'{name}缺字: {missing[:3]}')
        if preview_dir:
            from PIL import Image,ImageOps
            fig.savefig(Path(preview_dir)/name,dpi=100)
            ImageOps.grayscale(Image.open(Path(preview_dir)/name)).save(Path(preview_dir)/('gray_'+name))
        plt.close(fig);print('PNG',name)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--data-dir',type=Path);args=parser.parse_args();build(load_data(args.data_dir),args.out)
