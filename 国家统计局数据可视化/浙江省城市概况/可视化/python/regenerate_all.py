"""浙江城市概况可视化 · 一键复现。

环境：Python 3.10+；pip install numpy matplotlib plotly Pillow openpyxl
用法：python python/regenerate_all.py
      python python/regenerate_all.py --data-dir "原始工作簿目录" --output "输出目录"
输出：10 张 300 dpi PNG、2 个交互式大屏、1 个三维探索页。
直接打开11_城市运行大屏.html、12_城市设施夜景大屏.html或13_三维城市探索.html。
默认使用 data_source.py 内嵌的原始数据快照。不会访问网络或上传 GitHub。
"""
from pathlib import Path
import argparse
from data_source import load_data,validate_data

def main():
    parser=argparse.ArgumentParser(description='生成浙江城市概况全部可视化')
    parser.add_argument('--data-dir',type=Path,help='可选：包含原始9个xlsx的目录')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1],help='输出目录')
    parser.add_argument('--html-only',action='store_true',help='只重建HTML')
    parser.add_argument('--png-only',action='store_true',help='只重建PNG')
    args=parser.parse_args()
    if args.html_only and args.png_only:parser.error('html-only与png-only不能同时使用')
    data=load_data(args.data_dir);validate_data(data)
    if not args.html_only:
        from build_static import build
        build(data,args.output)
    if not args.png_only:
        from build_interactive import build
        build(data,args.output)
    print(f'完成。输出目录：{args.output.resolve()}')

if __name__=='__main__':main()
