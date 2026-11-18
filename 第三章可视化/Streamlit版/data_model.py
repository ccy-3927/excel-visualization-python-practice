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
          'income':{dep:dict(items) for dep,items in groups.items()},'departments':departments,'education':list(cached_pivot),
          'initial':initial,'pivotGradient':stops,'roseLayers':layers}
    # 确认源数据重算与工作簿已保存的透视结果一致。
    for education,expected in cached_pivot.items():
        total=count=0
        for dep in initial['departments']:
            g=groups[dep].get(education,{'sum':0,'count':0});total+=g['sum'];count+=g['count']
        assert count and abs(total/count-expected)<1e-8,(education,total,count,expected)
    return data

