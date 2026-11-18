"""一次重建人口可视化：10张PNG、3张HTML（含三维探索）。

安装依赖：pip install numpy matplotlib pillow plotly openpyxl
运行：python regenerate_all.py
可选：python regenerate_all.py --data-dir "原数据目录" --out "可视化目录"
不指定data-dir时使用population_data.py内嵌的用户原始工作簿快照。
建议Python 3.10+、matplotlib 3.8+、plotly 5.24+；需安装中文字体。
HTML无联网依赖，直接双击打开；三个HTML应放在同一目录以便专题切换。
三维探索依赖浏览器WebGL，支持旋转、缩放、年份播放和视角复位。
PNG的完整口径、计算方法见population_static.py，原表注释见population_data.py。
"""
from pathlib import Path
import argparse
from population_data import load_data,validate
from population_static import build as build_png
from population_web import build as build_html
from population_3d import build as build_3d

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--only',choices=['all','png','html'],default='all')
    args=parser.parse_args();data=load_data(args.data_dir);validate(data)
    if args.only in ['all','png']:build_png(data,args.out)
    if args.only in ['all','html']:
        build_html(data,args.out)
        build_3d(data,args.out)
    print('已生成至',args.out.resolve())

if __name__=='__main__':main()
