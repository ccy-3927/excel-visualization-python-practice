"""只读提取第三章原始数据及 Excel 图表样式，不执行 VBA、不改写工作簿。"""
from pathlib import Path
import argparse
import json
import warnings
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
import colorsys
import openpyxl

NS={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    's':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'x':'http://schemas.microsoft.com/office/spreadsheetml/2009/9/main'}

def read_chart_styles(z):
    """解析本工作簿使用的 RGB/主题色、明度、透明度及渐变，避免另配颜色。"""
    theme=ET.fromstring(z.read('xl/theme/theme1.xml'))
    scheme=theme.find('a:themeElements/a:clrScheme',NS)
    palette={e.tag.split('}')[-1]:list(e)[0].get('lastClr',list(e)[0].get('val')) for e in scheme}
    aliases={'bg1':'lt1','tx1':'dk1','bg2':'lt2','tx2':'dk2'}
    def color(node):
        kind=node.tag.split('}')[-1]
        if kind=='srgbClr': value=node.get('val')
        elif kind=='schemeClr': value=palette[aliases.get(node.get('val'),node.get('val'))]
        elif kind=='sysClr': value=node.get('lastClr')
        else: raise ValueError(f'不支持的 Excel 颜色类型：{kind}')
        rgb=[int(value[k:k+2],16)/255 for k in (0,2,4)]; alpha=1.
        for transform in node:
            name=transform.tag.split('}')[-1]; amount=int(transform.get('val'))/100000
            if name in ('lumMod','lumOff'):
                h,l,s=colorsys.rgb_to_hls(*rgb)
                l=l*amount if name=='lumMod' else l+amount
                rgb=list(colorsys.hls_to_rgb(h,min(1,max(0,l)),s))
            elif name=='alpha': alpha=amount
            else: raise ValueError(f'不支持的 Excel 颜色变换：{name}')
        return '#'+''.join(f'{round(v*255):02X}' for v in rgb),alpha
    def fill(parent,path='a:solidFill'):
        element=parent.find(path,NS)
        if element is None: raise ValueError(f'缺少 Excel 填充颜色：{path}')
        return color(list(element)[0])
    roots=[ET.fromstring(z.read(f'xl/charts/chart{i}.xml')) for i in range(1,8)]
    series=[r.findall('.//c:ser',NS) for r in roots]
    def point_fill(s):
        point=next(p for p in s.findall('c:dPt',NS) if p.find('c:idx',NS).get('val')=='0')
        return fill(point,'c:spPr/a:solidFill')[0]
    gradient=series[4][0].find('c:spPr/a:gradFill',NS)
    stops=[{'offset':int(g.get('pos'))/100000,'color':color(list(g)[0])[0]} for g in gradient.findall('a:gsLst/a:gs',NS)]
    layers=[]
    for s in series[2]:
        points=sorted(s.findall('c:dPt',NS),key=lambda p:int(p.find('c:idx',NS).get('val')))
        layers.append([None if p.find('c:spPr/a:noFill',NS) is not None else fill(p,'c:spPr/a:solidFill')[0] for p in points])
    rings={}
    for i in (1,2,5):
        rings[str(i)]={'hole':int(roots[i].find('.//c:holeSize',NS).get('val'))/100,
                       'angle':int(roots[i].find('.//c:firstSliceAng',NS).get('val'))}
    axes=roots[3].findall('.//c:valAx',NS)
    limits=[[float(ax.find('c:scaling/c:min',NS).get('val')),float(ax.find('c:scaling/c:max',NS).get('val'))] for ax in axes]
    track,track_alpha=fill(series[6][1],'c:spPr/a:solidFill')
    return {'backgrounds':[fill(r,'c:spPr/a:solidFill')[0] for r in roots],
            'sales':fill(series[0][0],'c:spPr/a:solidFill')[0],
            'people':[point_fill(s) for s in series[1]],
            'roseLayers':layers,'rings':rings,
            'combo':[fill(s,'c:spPr/a:solidFill')[0] for s in series[3][:2]]+[fill(series[3][2],'c:spPr/a:ln/a:solidFill')[0]],
            'comboLimits':limits,'incomeGradient':stops,
            'incomeGradientAngle':int(gradient.find('a:lin',NS).get('ang'))/60000,
            'jade':[point_fill(s) for s in series[5]],
            'bead':fill(series[6][0],'c:spPr/a:solidFill')[0],
            'beadTrack':track,'beadTrackAlpha':track_alpha,
            'beadMarker':fill(series[6][2],'c:marker/c:spPr/a:solidFill')[0],
            'beadEdge':fill(series[6][2],'c:marker/c:spPr/a:ln/a:solidFill')[0]}

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
        styles=read_chart_styles(z)
        cache=ET.fromstring(z.read('xl/pivotCache/pivotCacheDefinition1.xml'))
        fields=cache.findall('s:cacheFields/s:cacheField',NS)
        dept_items=[n.get('v') for n in fields[2].find('s:sharedItems',NS)]
        slicer=ET.fromstring(z.read('xl/slicerCaches/slicerCache1.xml'))
        items=slicer.findall('.//x:items/x:i',NS)
        departments=[dept_items[int(n.get('x'))] for n in items]
        initial['departments']=[dept_items[int(n.get('x'))] for n in items if n.get('s')=='1']
        if not initial['departments']:initial['departments']=departments[:]
    data={'sales':sales,'people':people,'rose':rose,'combo':combo,'jade':jade,'bead':bead,
          'income':{dep:dict(items) for dep,items in groups.items()},'departments':departments,'education':list(cached_pivot),
          'initial':initial,'styles':styles,'roseLayers':styles['roseLayers']}
    # 确认源数据重算与工作簿已保存的透视结果一致。
    for education,expected in cached_pivot.items():
        total=count=0
        for dep in initial['departments']:
            g=groups[dep].get(education,{'sum':0,'count':0});total+=g['sum'];count+=g['count']
        assert count and abs(total/count-expected)<1e-8,(education,total,count,expected)
    return data

