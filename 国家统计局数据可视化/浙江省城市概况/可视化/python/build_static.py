"""生成10张精致版4800×2700 / 300dpi PNG。依赖numpy、matplotlib、Pillow。

python build_static.py可独立重建。数据源：国家统计局分省年度数据，浙江省城市汇总。
详细口径集中保留在代码，去除图内长说明：
01 累计增幅=(2024年值/2016年值-1)×100%；仅比较相对变化，不评价服务质量。
02 万人次÷10000换算亿人次；仅合计汽电车与轨道，不替代“公共交通客运总量”。
03 阶梯为年度观测值连接，并非精确开通日期；渐变不表示置信区间。
04 其他及未细分=供水总量-生活用水-生产用水，为计算余项，非漏损。
   圆角长方体共用正面/侧面/顶面棱线；只柔化轮廓棱角，正面高度严格对应原值。
05 分母只含天然气与液化石油气服务人口，未计人工煤气；两类人口不保证去重，
   不能据此解释全省居民能源结构。
06 左侧并列展示城市绿地与公园绿地的原始面积，不将二者相加；右侧三项累计增幅
   均为(2024年值/2016年值-1)×100%。公园数量使用个，面积使用万公顷；不设双轴。
07 指数=当年原值/2016年原值×100；原始单位不同，不比较绝对长度。
08 人均指标沿用城区人口与暂住人口之和口径。三面板独立刻度，纵轴从0开始；
   缺失严重的每万人公交车辆指标移出此图，不补值。
09 同比=(当年值/上年值-1)×100%；色阶关于0对称；规模增减不直接评价质量。
10 城市建设表未含2024；2023面积为空，面积只画至2022、人口密度至2023。
   2022完整城市规模分组（市辖区户籍人口）：400万以上1个、200—400万2个、
   100—200万4个、50—100万3个、20—50万1个，合计11个。
   这组独立信息不再塞进面积图；2023、2024分组不全，不推算。
所有缺失保留为空，不插值、不补零、不添加预测或统计显著性。
"""
from pathlib import Path
import warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import FuncFormatter, MaxNLocator
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, Patch
from matplotlib.colors import to_rgb
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from data_source import load_data, value, values, change, YEARS, validate_data

P=dict(bg='#F8F7F3',ink='#1D343B',muted='#68767A',grid='#E2E4E1',teal='#147D7C',
       blue='#3C63A8',gold='#C8944E',violet='#777DA6',mint='#A9C3AD',coral='#B87F5E')
OUT=Path(__file__).resolve().parents[1]
QA_CALLBACK=None

def configure():
    installed={f.name for f in font_manager.fontManager.ttflist}
    font=next((f for f in ['Microsoft YaHei','Noto Sans SC','Source Han Sans SC','SimHei','PingFang SC'] if f in installed),None)
    if not font:raise RuntimeError('请安装Microsoft YaHei / Noto Sans SC等中文字体。')
    plt.rcParams.update({'font.family':font,'axes.unicode_minus':False,'font.size':16,
                         'axes.labelcolor':P['muted'],'xtick.color':P['muted'],'ytick.color':P['muted'],
                         'axes.edgecolor':P['grid'],'figure.facecolor':P['bg'],
                         'axes.spines.top':False,'axes.spines.right':False})

def plate(fig,rect,face='#FFFFFF',shadow=True):
    x,y,w,h=rect
    if shadow:
        fig.add_artist(FancyBboxPatch((x+.003,y-.007),w,h,boxstyle='round,pad=0.005,rounding_size=0.018',
                       transform=fig.transFigure,facecolor='#183B4212',edgecolor='none',zorder=-3))
    fig.add_artist(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.005,rounding_size=0.018',
                   transform=fig.transFigure,facecolor=face,edgecolor='#E7EBE7',lw=.8,zorder=-2))

def base(title,period='2016—2024',board=True):
    fig=plt.figure(figsize=(16,9),facecolor=P['bg'])
    fig.text(.07,.91,title,size=31,weight='bold',color=P['ink'],va='center')
    plate(fig,(.81,.882,.133,.052),face='#EEF1ED',shadow=False)
    fig.text(.932,.91,period,size=17,color=P['muted'],ha='right',va='center')
    if board:plate(fig,(.045,.075,.91,.755))
    return fig

def axis(fig,rect=(.105,.14,.79,.60),unit=None,years=True):
    ax=fig.add_axes(rect,facecolor='none')
    ax.spines['left'].set_visible(False);ax.spines['bottom'].set_color(P['grid'])
    ax.tick_params(axis='both',length=0,pad=13,labelsize=16)
    ax.grid(axis='y',color=P['grid'],lw=.8,zorder=0);ax.set_axisbelow(True)
    if unit:ax.set_title(unit,loc='left',fontsize=16,color=P['muted'],pad=23)
    if years:ax.set_xticks([2016,2018,2020,2022,2024]);ax.set_xlim(2015.65,2024.75)
    return ax

def arr(d,key):
    return np.array([np.nan if v is None else v for v in values(d,key)],dtype=float)

def endlabel(ax,x,y,text,color,offset=(16,0),size=18):
    ax.annotate(text,(x,y),xytext=offset,textcoords='offset points',va='center',color=color,
                size=size,weight='bold',annotation_clip=False)

def tone(color,light=0):
    rgb=np.array(to_rgb(color))
    return tuple(rgb+(1-rgb)*light) if light>=0 else tuple(rgb*(1+light))

def area_gradient(ax,x,lower,upper,color,light=.16,zorder=1):
    """沿高度的装饰渐变；上下边界均使用观测值，不改变面积和坐标。"""
    lower=np.broadcast_to(np.asarray(lower,dtype=float),len(x));upper=np.asarray(upper,dtype=float)
    poly=ax.fill_between(x,lower,upper,color='none')
    cmap=LinearSegmentedColormap.from_list('fill',[tone(color,light),tone(color,-.04)])
    image=ax.imshow(np.linspace(0,1,300).reshape(-1,1),origin='lower',
                    extent=[min(x),max(x),float(np.nanmin(lower)),float(np.nanmax(upper))],
                    cmap=cmap,aspect='auto',zorder=zorder)
    image.set_clip_path(poly.get_paths()[0],transform=ax.transData)
    return poly

def spherical_image(color,size=160):
    """等大的光照球面RGBA图片，左上固定光源，不承载数据量纲。"""
    u=np.linspace(-1,1,size);xx,yy=np.meshgrid(u,-u)
    radius=xx*xx+yy*yy;inside=radius<=1;zz=np.sqrt(np.clip(1-radius,0,1))
    light=np.array([-.45,.55,.7]);light/=np.linalg.norm(light)
    lambert=np.clip(xx*light[0]+yy*light[1]+zz*light[2],0,1)
    base=np.array(to_rgb(color));intensity=.38+.64*lambert
    rgb=np.clip(base[None,None,:]*intensity[:,:,None],0,1)
    spec=np.exp(-((xx+.35)**2+(yy-.42)**2)/.045)*.58
    rgb=rgb*(1-spec[:,:,None])+spec[:,:,None]
    rim=np.clip((1-radius)*32,0,1);alpha=inside*rim
    return np.dstack([rgb,alpha])

def soft_shadow(size=160):
    yy,xx=np.mgrid[-1:1:complex(size),-1:1:complex(size)]
    alpha=np.exp(-((xx/.70)**2+(yy/.24)**2)*3)*.24
    return np.dstack([np.full_like(alpha,.08),np.full_like(alpha,.17),np.full_like(alpha,.18),alpha])

def export(fig,out,name,preview_dir=None):
    if QA_CALLBACK:QA_CALLBACK(fig,name)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');fig.savefig(out/name,dpi=300,facecolor=fig.get_facecolor())
    missing=[str(w.message) for w in caught if 'Glyph' in str(w.message)]
    if missing:raise RuntimeError(f'{name}缺少字形: {missing[:3]}')
    if preview_dir:
        from PIL import Image,ImageOps
        preview_dir=Path(preview_dir);preview_dir.mkdir(parents=True,exist_ok=True)
        fig.savefig(preview_dir/name,dpi=100)
        ImageOps.grayscale(Image.open(preview_dir/name)).save(preview_dir/('gray_'+name))
    plt.close(fig);print('PNG',name)

def growth(d):
    names=['轨道交通运营里程','天然气供气总量','天然气用气人口','天然气管道长度',
           '市容环卫专用车辆设备','供水管道长度','公园个数','道路长度']
    names=sorted(names,key=lambda k:change(d,k));gains=[change(d,k) for k in names]
    labels={'轨道交通运营里程':'轨道运营里程','市容环卫专用车辆设备':'环卫车辆设备'}
    fig=base('城市设施的八年增长');ax=axis(fig,(.265,.14,.615,.62),'累计增幅 / %',years=False)
    for i,(name,gain) in enumerate(zip(names,gains)):
        c=P['gold'] if i==len(names)-1 else P['teal']
        ax.hlines(i,0,gain,lw=13,color=c,alpha=.15)
        ax.scatter([gain],[i],s=470,color=c,alpha=.10,zorder=3,edgecolor='none')
        ax.plot(gain,i,'o',color=c,ms=10,mec='white',mew=1.6,zorder=4)
        ax.text(gain+14,i,f'+{gain:.1f}%',va='center',color=c,weight='bold',size=19,
                bbox=dict(boxstyle='round,pad=.25',facecolor='#FFFFFF',edgecolor='none'))
    ax.set_yticks(range(len(names)),[labels.get(n,n) for n in names]);ax.tick_params(axis='y',labelsize=17,pad=20)
    ax.set_ylim(-.6,7.7);ax.set_xlim(0,550);ax.set_xticks([0,200,400],['0','200','400'])
    ax.grid(False);ax.grid(axis='x',color=P['grid'],lw=.8);ax.spines['bottom'].set_visible(False)
    return fig

def transit(d):
    bus,rail=arr(d,'公共汽电车客运量')/10000,arr(d,'轨道交通客运量')/10000
    fig=base('公共出行，轨道占比持续提升');ax=axis(fig,unit='汽电车与轨道客运量 / 亿人次')
    area_gradient(ax,YEARS,0,bus,P['blue'],light=.20)
    area_gradient(ax,YEARS,bus,bus+rail,P['teal'],light=.12)
    ax.plot(YEARS,bus,color='white',lw=2.4)
    ax.plot(YEARS,bus+rail,color=P['ink'],lw=1.5,alpha=.35)
    ax.set_ylim(0,47);ax.set_yticks([0,15,30,45])
    ax.text(2018.25,15,'公共汽电车',color='white',size=23,weight='bold')
    ax.text(2021.55,26.5,'轨道交通',color='white',size=23,weight='bold')
    endlabel(ax,2024,bus[-1]/2,f'{bus[-1]:.2f}',P['blue'])
    endlabel(ax,2024,bus[-1]+rail[-1]/2,f'{rail[-1]:.2f}',P['teal'])
    return fig

def rail(d):
    y=arr(d,'轨道交通运营里程');fig=base('轨道网络，迈入八百公里时代');ax=axis(fig,unit='运营里程 / 公里')
    poly=ax.fill_between(YEARS,y,step='post',color='none')
    cmap=LinearSegmentedColormap.from_list('jade',[P['bg'],'#8CB5AB',P['teal']])
    im=ax.imshow(np.linspace(0,1,300).reshape(-1,1),origin='lower',extent=[2016,2024,0,950],aspect='auto',cmap=cmap,zorder=1)
    im.set_clip_path(poly.get_paths()[0],transform=ax.transData)
    ax.step(YEARS,y,where='post',lw=3.7,color=P['teal'],zorder=3)
    ax.step(YEARS,y,where='post',lw=10,color=P['teal'],alpha=.08,zorder=2)
    ax.scatter(YEARS,y,color=P['bg'],edgecolor=P['teal'],s=65,lw=2.2,zorder=4)
    for i in [0,4,8]:
        ax.annotate(f'{y[i]:.0f}',(YEARS[i],y[i]),xytext=(0,18),textcoords='offset points',ha='center',
                    size=26 if i==8 else 20,color=P['teal'] if i==8 else P['ink'],weight='bold',
                    bbox=dict(boxstyle='round,pad=.30',facecolor='white',edgecolor='none'))
    ax.scatter([2024],[y[-1]],s=120,color=P['gold'],edgecolor='white',linewidth=2,zorder=5)
    ax.set_ylim(0,1080);ax.set_yticks([0,300,600,900]);return fig

def water(d):
    total=arr(d,'供水总量');life=arr(d,'生活用供水总量');production=arr(d,'生产用供水总量');other=total-life-production
    fig=base('城市供水的三种去向');ax=axis(fig,unit='供水量 / 亿吨')
    from matplotlib.path import Path as MplPath
    from matplotlib.patches import PathPatch
    ax.set_ylim(0,61);ax.set_yticks([0,20,40,60])
    # 每根柱只有一套三面投影：正面、右侧面和顶面共用棱线。
    # 只柔化整体轮廓的棱角，不叠放前后两个圆角矩形。
    width=.54;dx=.13;dy=1.70
    colors=['#46A69B','#799BC4','#E2B78B']
    def softened_outline(vertices,radius_pt=3.8):
        points=ax.transData.transform(np.asarray(vertices,dtype=float))
        incoming=[];outgoing=[]
        radius=radius_pt*fig.dpi/72
        for i,p in enumerate(points):
            previous=points[(i-1)%len(points)]-p
            following=points[(i+1)%len(points)]-p
            before=np.linalg.norm(previous);after=np.linalg.norm(following)
            incoming.append(p+previous/before*min(radius,before*.30))
            outgoing.append(p+following/after*min(radius,after*.30))
        vertices=[incoming[0]];codes=[MplPath.MOVETO]
        for i,p in enumerate(points):
            vertices.extend([p,outgoing[i],incoming[(i+1)%len(points)]])
            codes.extend([MplPath.CURVE3,MplPath.CURVE3,MplPath.LINETO])
        vertices.append(incoming[0]);codes.append(MplPath.CLOSEPOLY)
        return MplPath(ax.transData.inverted().transform(vertices),codes)
    for i,x in enumerate(YEARS):
        left=x-width/2;right=x+width/2;t=total[i]
        # 六边形外轮廓对应真正连贯的长方体投影，圆角大小按印刷点数固定。
        outline=softened_outline([(left,0),(right,0),(right+dx,dy),
                                  (right+dx,t+dy),(left+dx,t+dy),(left,t)])
        silhouette=PathPatch(outline,facecolor='none',edgecolor='none')
        ax.add_patch(silhouette)
        bottom=0.
        for h,c in zip([life[i],production[i],other[i]],colors):
            top=bottom+h
            side=Polygon([(right,bottom),(right+dx,bottom+dy),
                          (right+dx,top+dy),(right,top)],closed=True,
                         facecolor=tone(c,-.19),edgecolor='none',zorder=2)
            side.set_clip_path(silhouette);ax.add_patch(side)
            cmap=LinearSegmentedColormap.from_list('front',[tone(c,.14),c,tone(c,-.04)])
            image=ax.imshow(np.linspace(0,1,200)[None,:],extent=[left,right,bottom,top],
                            origin='lower',aspect='auto',cmap=cmap,zorder=3)
            image.set_clip_path(silhouette)
            if bottom>0:
                seam=ax.plot([left,right,right+dx],[bottom,bottom,bottom+dy],
                             color='#FFFFFFCD',lw=.95,zorder=4,solid_capstyle='round')[0]
                seam.set_clip_path(silhouette)
            bottom=top
        cap=Polygon([(left,t),(right,t),(right+dx,t+dy),(left+dx,t+dy)],
                    closed=True,facecolor=tone(colors[-1],.29),edgecolor='none',zorder=4)
        cap.set_clip_path(silhouette);ax.add_patch(cap)
        # 柔和的L形高光仍明确标出正面与顶面、侧面的连接关系。
        crease=MplPath([(left,t),(right-.036,t),(right,t),(right,t-.46),(right,0)],
                       [MplPath.MOVETO,MplPath.LINETO,MplPath.CURVE3,MplPath.CURVE3,MplPath.LINETO])
        bevel=PathPatch(crease,facecolor='none',edgecolor='#FFFFFFB0',lw=.85,
                        capstyle='round',joinstyle='round',zorder=5)
        bevel.set_clip_path(silhouette);ax.add_patch(bevel)
        ax.add_patch(PathPatch(outline,facecolor='none',edgecolor='#527D831F',lw=.5,zorder=5))
    for i in [0,4,8]:ax.text(YEARS[i]+.045,total[i]+3.3,f'{total[i]:.2f}',ha='center',color=P['ink'],size=20,weight='bold')
    handles=[Patch(facecolor=c,label=label) for c,label in zip(colors,['生活用水','生产用水','其他及未细分'])]
    ax.legend(handles=handles,loc='upper center',bbox_to_anchor=(.52,1.155),ncol=3,
              frameon=False,fontsize=16,handlelength=1.4,columnspacing=2.2)
    return fig

def gas(d):
    natural=arr(d,'天然气用气人口');lpg=arr(d,'液化石油气用气人口');share=natural/(natural+lpg)*100
    fig=base('燃气服务结构，向天然气集中')
    ax=axis(fig,(.14,.165,.73,.555),years=False)
    teal=P['teal'];muted='#E1E7E5'
    # 各年均为100%的同长水平条；横向长度对应计算占比，非人口迁移流量。
    ax.axhspan(7.5,8.5,color='#F0F6F3',zorder=0)
    for i,(year,s) in enumerate(zip(YEARS,share)):
        track=FancyBboxPatch((0,i-.30),100,.60,boxstyle='round,pad=0,rounding_size=.22',
                            facecolor=muted,edgecolor='none',zorder=2)
        ax.add_patch(track)
        front=Rectangle((0,i-.30),s,.60,facecolor=teal,edgecolor='none',zorder=3)
        ax.add_patch(front);front.set_clip_path(track)
        ax.text(s-2.1,i,f'{s:.1f}%',ha='right',va='center',color='white',
                size=18 if year==2024 else 16,weight='bold',zorder=4)
        if year in [2016,2024]:
            ax.text(s+(100-s)/2,i,f'{100-s:.1f}%',ha='center',va='center',
                    color='#718485',size=16,weight='bold',zorder=4)
    ax.set_xlim(0,100);ax.set_ylim(8.7,-.8)
    ax.set_yticks(range(9),YEARS);ax.tick_params(axis='y',pad=23,labelsize=17)
    for label in ax.get_yticklabels():
        if label.get_text()=='2024':label.set_weight('bold');label.set_color(teal)
    ax.set_xticks([0,25,50,75,100],['0','25','50','75','100%'])
    ax.tick_params(axis='x',labelsize=16,pad=16)
    ax.grid(False);ax.grid(axis='x',color='#E8EEEB',lw=.8)
    for spine in ax.spines.values():spine.set_visible(False)
    handles=[Patch(facecolor=teal,label='天然气'),Patch(facecolor=muted,label='液化石油气')]
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.137,.806),ncol=2,frameon=False,
               fontsize=18,handlelength=1.5,columnspacing=2.5)
    fig.text(.87,.77,f'+{share[-1]-share[0]:.1f} 个百分点',ha='right',color=teal,size=22,weight='bold')
    return fig

def green(d):
    city=arr(d,'城市绿地面积');park=arr(d,'公园绿地面积');count=arr(d,'公园个数')
    fig=base('绿色空间，规模与增长并看',board=False)
    plate(fig,(.045,.125,.565,.705));plate(fig,(.63,.125,.325,.705))
    city_color='#419C94';park_color='#83A6CC';count_color='#C8944E'
    ax=axis(fig,(.100,.225,.465,.455),unit='绿地面积 / 万公顷')
    # 两个原始面积指标并列展示，不堆叠相加，也不混入人口或公园数量的量纲。
    width=.32
    ax.bar(np.asarray(YEARS)-.19,city,width=width,color=city_color,
           edgecolor='white',lw=1.0,zorder=3,label='城市绿地')
    ax.bar(np.asarray(YEARS)+.19,park,width=width,color=park_color,
           edgecolor='white',lw=1.0,zorder=3,label='公园绿地')
    ax.set_xlim(2015.4,2024.6);ax.set_ylim(0,22.5);ax.set_yticks([0,5,10,15,20])
    ax.tick_params(axis='both',labelsize=15)
    for xx,yy,color in [(2024-.19,city[-1],city_color),(2024+.19,park[-1],park_color)]:
        ax.annotate(f'{yy:.2f}',(xx,yy),xytext=(0,10),textcoords='offset points',
                    ha='center',color=color,size=18,weight='bold')
    handles=[Patch(facecolor=city_color,label='城市绿地'),Patch(facecolor=park_color,label='公园绿地')]
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.092,.805),ncol=2,
               frameon=False,fontsize=17,handlelength=1.4,columnspacing=2.2)
    fig.text(.664,.765,'八年累计增长',size=23,color=P['ink'],weight='bold')
    ax2=fig.add_axes([.665,.245,.265,.425],facecolor='none')
    series=[('公园数量',count,'个',count_color),('公园绿地',park,'万公顷',park_color),
            ('城市绿地',city,'万公顷',city_color)]
    for row,(name,data,unit,color) in zip([2,1,0],series):
        growth=(data[-1]/data[0]-1)*100
        original=f'{data[-1]:,.0f}' if unit=='个' else f'{data[-1]:.2f}'
        ax2.text(0,row+.31,f'{name}  {original} {unit}',size=17,color=P['ink'],va='bottom')
        ax2.hlines(row,0,100,color='#EFF2EF',lw=13,zorder=1)
        ax2.hlines(row,0,growth,color=color,lw=13,alpha=.78,zorder=2)
        ax2.scatter([growth],[row],s=110,color=color,edgecolor='white',linewidth=1.6,zorder=3)
        ax2.text(growth+4,row,f'+{growth:.1f}%',size=20,color=color,weight='bold',va='center',
                 bbox=dict(facecolor='white',edgecolor='none',pad=2),zorder=4)
    ax2.set_xlim(0,126);ax2.set_ylim(-.45,2.78)
    ax2.set_xticks([0,50,100],['0','50','100%']);ax2.tick_params(axis='x',length=0,pad=13,labelsize=14,colors=P['muted'])
    ax2.set_yticks([])
    for spine in ax2.spines.values():spine.set_visible(False)
    return fig

def networks(d):
    names=['天然气管道长度','供水管道长度','道路长度','城市排水管道长度'];labels=['天然气管道','供水管道','城市道路','排水管道']
    colors=[P['gold'],P['teal'],P['blue'],P['violet']];fig=base('看得见的路，看不见的网')
    ax=axis(fig,(.105,.14,.665,.60),'规模指数 / 2016 = 100')
    for i,(name,label,c) in enumerate(zip(names,labels,colors)):
        data=arr(d,name);index=data/data[0]*100
        ax.plot(YEARS,index,color=c,lw=10,alpha=.075)
        ax.plot(YEARS,index,color=c,lw=3.4,marker=['o','s','^','D'][i],ms=5,ls=['-','--','-.',':'][i])
        endlabel(ax,2024,index[-1],f'{label}  {index[-1]:.0f}',c,offset=(18,[0,0,16,-16][i]),size=17)
    ax.set_ylim(75,255);ax.set_yticks([100,150,200,250]);ax.set_xlim(2015.7,2024.25);return fig

def percapita(d):
    names=['人均城市道路面积','人均公园绿地面积','每万人拥有公共厕所'];titles=['道路面积','公园绿地','公共厕所']
    units=['平方米 / 人','平方米 / 人','座 / 万人'];colors=[P['blue'],P['teal'],P['gold']]
    fig=base('人均设施供给，走向不同',board=False)
    for i,(name,title,unit,c) in enumerate(zip(names,titles,units,colors)):
        plate(fig,(.055+i*.302,.13,.285,.68))
        left=.10+i*.302
        fig.text(left,.745,title,size=23,color=P['ink'],weight='bold')
        fig.text(left,.69,unit,size=16,color=P['muted'])
        data=arr(d,name);fig.text(left,.585,f'{data[-1]:.2f}',size=36,color=c,weight='bold')
        ax=axis(fig,(left,.215,.225,.285),years=False)
        area_gradient(ax,YEARS,0,data,c,light=.86)
        ax.plot(YEARS,data,color=c,lw=9,alpha=.075)
        ax.plot(YEARS,data,color=c,lw=3.4,marker=['o','s','D'][i],ms=5)
        ax.scatter([2024],[data[-1]],s=65,color=c,edgecolor='white',lw=1.5,zorder=4)
        ax.set_xlim(2015.6,2024.7);ax.set_ylim(0,np.nanmax(data)*1.27)
        ax.set_xticks([2016,2024]);ax.yaxis.set_major_locator(MaxNLocator(3))
    return fig

def sanitation(d):
    names=['道路清扫保洁面积','生活垃圾清运量','市容环卫专用车辆设备','公共厕所数量','三类以上公共厕所数量']
    labels=['清扫保洁面积','垃圾清运量','环卫车辆设备','公共厕所','三类以上公厕']
    raw=np.array([arr(d,n) for n in names]);yoy=(raw[:,1:]/raw[:,:-1]-1)*100
    fig=base('环卫服务的年度变化','2017—2024');ax=fig.add_axes([.215,.19,.625,.53])
    lim=np.ceil(np.max(np.abs(yoy))/5)*5
    # 全色阶保持浅色：负值浅蓝、零值近白、正值浅青，不出现深色底格。
    cmap=LinearSegmentedColormap.from_list('balanced',['#ADC7E7','#FDFEFE','#81BEAF'])
    norm=TwoSlopeNorm(vmin=-lim,vcenter=0,vmax=lim)
    im=ax.imshow(yoy,cmap=cmap,norm=norm,aspect='auto')
    for i in range(len(names)):
        for j in range(len(YEARS)-1):
            ax.text(j,i,f'{yoy[i,j]:+.1f}%',ha='center',va='center',size=16,weight='bold',
                    color='#3F6F82')
    ax.set_xticks(range(8),YEARS[1:]);ax.set_yticks(range(5),labels);ax.tick_params(length=0,pad=18,labelsize=17)
    for s in ax.spines.values():s.set_visible(False)
    ax.set_xticks(np.arange(-.5,8,1),minor=True);ax.set_yticks(np.arange(-.5,5,1),minor=True)
    ax.grid(which='minor',color='white',lw=5);ax.tick_params(which='minor',length=0)
    cax=fig.add_axes([.88,.23,.014,.45]);cb=fig.colorbar(im,cax=cax,ticks=[-20,0,20])
    cb.set_label('同比 / %',labelpad=20,size=17);cb.ax.tick_params(labelsize=16,length=0,pad=9);cb.outline.set_visible(False)
    return fig

def construction(d):
    urban=arr(d,'城区面积');built=arr(d,'建成区面积');density=arr(d,'城市人口密度')
    fig=base('城市的边界，与城市的密度','2016—2023');ax=axis(fig,(.09,.18,.405,.52),'面积 / 平方公里',years=False)
    for data,label,c,marker in [(urban,'城区面积',P['blue'],'o'),(built,'建成区面积',P['teal'],'s')]:
        ax.plot(YEARS,data,color=c,lw=10,alpha=.075)
        ax.plot(YEARS,data,color=c,lw=3.7,marker=marker,ms=6,label=label);last=np.where(np.isfinite(data))[0][-1]
        ax.scatter([YEARS[last]],[data[last]],s=75,color=c,edgecolor='white',lw=1.5,zorder=4)
        endlabel(ax,YEARS[last],data[last],f'{data[last]:,.0f}',c,offset=(12,0),size=21)
    ax.set_xlim(2015.6,2023.7);ax.set_xticks([2016,2019,2022]);ax.set_ylim(0,18000);ax.set_yticks([0,6000,12000,18000])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x:,.0f}'))
    ax.legend(loc='upper center',bbox_to_anchor=(.54,1.16),frameon=False,ncol=2,fontsize=16,handlelength=1.5)
    ax2=axis(fig,(.615,.18,.285,.52),'人口密度 / 人 / 平方公里',years=False)
    area_gradient(ax2,YEARS,0,density,P['gold'],light=.87)
    ax2.plot(YEARS,density,color=P['gold'],lw=10,alpha=.075)
    ax2.plot(YEARS,density,color=P['gold'],lw=3.7,marker='D',ms=6)
    ax2.set_xlim(2015.6,2024);ax2.set_xticks([2016,2020,2023]);ax2.set_ylim(0,3000);ax2.set_yticks([0,1500,3000])
    endlabel(ax2,2023,density[7],f'{density[7]:.0f}',P['gold'],offset=(10,0),size=21);return fig

CHARTS=[('01_城市设施增长.png',growth),('02_公共出行结构.png',transit),('03_轨道网络扩容.png',rail),
        ('04_城市供水去向.png',water),('05_燃气服务转型.png',gas),('06_绿色空间轨迹.png',green),
        ('07_道路与地下管网.png',networks),('08_人均设施供给.png',percapita),
        ('09_环卫年度变化.png',sanitation),('10_城市边界与密度.png',construction)]

def build(data=None,out=OUT,preview_dir=None):
    data=load_data() if data is None else data
    validate_data(data);configure();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for filename,fn in CHARTS:export(fn(data),out,filename,preview_dir)

if __name__=='__main__':build()
