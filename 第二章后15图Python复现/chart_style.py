# -*- coding: utf-8 -*-
"""DrawingML 配色、字体、文本框和坐标轴绘制辅助函数。"""
from pathlib import Path
from io import BytesIO
import argparse
import json
import math
import posixpath
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import numpy as np
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, colors
from matplotlib.patches import Rectangle, FancyBboxPatch, Wedge, Circle
from matplotlib.lines import Line2D
from PIL import Image, ImageDraw, ImageFont

BG = '#1A1E43'
BLUE, PINK, WHITE = '#0070C0', '#E74E69', '#F2F2F2'
FILENAME = '第二章 图表(后15).xlsx'
HERE = Path(__file__).resolve().parent


def xml(data):
    """去掉命名空间前缀，保留 XML 内容和关系标识。"""
    root = ET.fromstring(data)
    for e in root.iter():
        e.tag = e.tag.split('}')[-1]
        e.attrib = {k.split('}')[-1]: v for k, v in e.attrib.items()}
    return root


def attr(root, path, default=None, key='val'):
    e = root.find(path) if root is not None else None
    return e.get(key, default) if e is not None else default


def value(root, path, default=0):
    return float(attr(root, path, default))


def fill(root, default=WHITE):
    """读取 RGB、主题色、亮度及透明度。"""
    if root is None:
        return colors.to_rgba(default)
    if root.find('noFill') is not None:
        return (0, 0, 0, 0)
    solid = root.find('solidFill')
    if solid is None:
        return colors.to_rgba(default)
    e = next(iter(solid), None)
    if e is None:
        return colors.to_rgba(default)
    palette = {'bg1': '#FFFFFF', 'lt1': '#FFFFFF', 'tx1': '#000000',
               'dk1': '#000000', 'accent1': '#4472C4', 'accent2': '#ED7D31'}
    c = '#' + e.get('val') if e.tag == 'srgbClr' else palette.get(e.get('val'), default)
    rgb = np.array(colors.to_rgb(c))
    rgb = rgb * value(e, 'lumMod', 100000) / 100000 + value(e, 'lumOff', 0) / 100000
    return (*np.clip(rgb, 0, 1), value(e, 'alpha', 100000) / 100000)


def setup_font():
    for file in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
        if Path(file).exists():
            font_manager.fontManager.addfont(file)
            name = font_manager.FontProperties(fname=file).get_name()
            plt.rcParams['font.family'] = name
            break
    else:
        plt.rcParams['font.family'] = ['Noto Sans CJK SC', 'SimHei', 'DejaVu Sans']
    plt.rcParams.update({'font.size': 9, 'text.color': WHITE,
                         'axes.labelcolor': WHITE, 'xtick.color': WHITE,
                         'ytick.color': WHITE, 'axes.unicode_minus': False,
                         'svg.fonttype': 'path'})


def native_size(shapes):
    """由图内形状的 EMU 尺寸和相对锚点反算 Excel 图表英寸尺寸。"""
    if shapes is not None:
        for a in shapes:
            ext = a.find('./sp/spPr/xfrm/ext')
            if ext is not None and a.find('./from/x') is not None:
                dx = float(a.findtext('./to/x')) - float(a.findtext('./from/x'))
                dy = float(a.findtext('./to/y')) - float(a.findtext('./from/y'))
                if dx > 0 and dy > 0:
                    return int(ext.get('cx')) / dx / 914400, int(ext.get('cy')) / dy / 914400
    return 5.667, 4.25


def text_shape(fig, shape, box):
    """按原文段落、字号、颜色、对齐及行距绘制文本框。"""
    x, y, w, h = box  # y 从顶部起算
    body = shape.find('txBody')
    if body is None:
        return
    paras = body.findall('p')
    bp = body.find('bodyPr')
    pad_x = float(bp.get('lIns', 91440)) / 914400 / fig.get_figwidth() if bp is not None else 0
    pad_y = float(bp.get('tIns', 45720)) / 914400 / fig.get_figheight() if bp is not None else 0
    cursor = 1 - y - pad_y
    renderer = fig.canvas.get_renderer()
    for p in paras:
        runs = p.findall('r') + p.findall('fld')
        text = ''.join(r.findtext('t', '') for r in runs)
        if not text:
            continue
        rp = runs[0].find('rPr')
        fs = float(rp.get('sz', 1100)) / 100 if rp is not None else 11
        bold = rp is not None and rp.get('b') == '1'
        color = fill(rp)
        align = attr(p, 'pPr', 'l', key='algn')
        ha = {'l': 'left', 'ctr': 'center', 'r': 'right'}.get(align, 'left')
        tx = x + pad_x if ha == 'left' else x + (w / 2 if ha == 'center' else w - pad_x)
        # Excel 会在文本框边缘换行；按字体真实宽度逐字进行同样处理。
        prop = font_manager.FontProperties(family=plt.rcParams['font.family'], size=fs,
                                           weight='bold' if bold else 'normal')
        max_pixels = (w - 2 * pad_x) * fig.bbox.width
        # Excel 的短数字文本框使用自动适应；防止年份在窄图例中折行。
        full_width = renderer.get_text_width_height_descent(text, prop, False)[0]
        if len(paras) == 1 and len(text) <= 8 and full_width > max_pixels:
            fs *= max_pixels / full_width * .98
            prop.set_size(fs)
        lines, line = [], ''
        for ch in text:
            test = line + ch
            width = renderer.get_text_width_height_descent(test, prop, False)[0]
            if width > max_pixels and line:
                lines.append(line)
                line = ch
            else:
                line = test
        lines.append(line)
        spacing = value(p, './pPr/lnSpc/spcPts', fs * 120) / 100
        anchor = bp.get('anchor', 't') if bp is not None else 't'
        if anchor == 'ctr' and len(paras) == 1:
            cursor = 1 - y - h / 2
        for line in lines:
            run_colors = [fill(r.find('rPr')) for r in runs]
            va = 'center' if anchor == 'ctr' and len(paras) == 1 else 'top'
            if len(set(run_colors)) > 1 and len(lines) == 1:
                widths = [renderer.get_text_width_height_descent(r.findtext('t',''),prop,False)[0]
                          / fig.bbox.width for r in runs]
                px = tx - (sum(widths)/2 if ha == 'center' else sum(widths) if ha == 'right' else 0)
                for r,rc,rw in zip(runs,run_colors,widths):
                    fig.text(px,cursor,r.findtext('t',''),fontsize=fs,color=rc,ha='left',va=va,
                             weight='bold' if bold else 'normal',zorder=15)
                    px += rw
            else:
                fig.text(tx, cursor, line, fontsize=fs, color=color, ha=ha, va=va,
                         weight='bold' if bold else 'normal', zorder=15)
            cursor -= spacing / 72 / fig.get_figheight()


def draw_shapes(fig, root, skip_empty=False):
    if root is None:
        return
    for a in root:
        shape = a.find('sp')
        if shape is None or a.find('./from/x') is None:
            continue
        x, y = float(a.findtext('./from/x')), float(a.findtext('./from/y'))
        w, h = float(a.findtext('./to/x')) - x, float(a.findtext('./to/y')) - y
        sp = shape.find('spPr')
        fc, ec = fill(sp, '#00000000'), fill(sp.find('ln'), '#00000000')
        geom = attr(sp, 'prstGeom', 'rect', key='prst')
        if not skip_empty and (fc[3] or ec[3]):
            if geom == 'roundRect':
                patch = FancyBboxPatch((x, 1-y-h), w, h, boxstyle='round,pad=0,rounding_size=0.008',
                                       facecolor=fc, edgecolor=ec, linewidth=.75, transform=fig.transFigure, zorder=4)
            elif geom == 'rect':
                patch = Rectangle((x, 1-y-h), w, h, facecolor=fc, edgecolor=ec,
                                  linewidth=.75, transform=fig.transFigure, zorder=4)
            else:
                patch = None
            if patch is not None:
                fig.add_artist(patch)
        text_shape(fig, shape, (x, y, w, h))


def axes_for(fig, root):
    layout = root.find('./chart/plotArea/layout/manualLayout')
    x, y, w, h = [value(layout, k, d) for k, d in zip('xywh', [.12, .28, .8, .56])]
    ax = fig.add_axes([x, 1-y-h, w, h], facecolor=BG)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, pad=5)
    ax.set_axisbelow(True)
    return ax


def vertical_axes(ax, root, labels, maximum, step=None):
    ax.set_xlim(-.5, len(labels)-.5)
    ax.set_ylim(0, maximum)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    va = root.find('./chart/plotArea/valAx')
    if attr(va, 'delete', '0') == '1':
        ax.set_yticks([])
    else:
        if step:
            ax.set_yticks(np.arange(0, maximum + step * .01, step))
        if va.find('majorGridlines') is not None:
            ax.grid(axis='y', color=WHITE, alpha=.2, linestyle=(0, (6, 4)), linewidth=.5)
    ca = root.find('./chart/plotArea/catAx')
    if ca is not None and ca.find('./spPr/ln/solidFill') is not None:
        ax.spines['bottom'].set_visible(True)
        ax.spines['bottom'].set_color(fill(ca.find('./spPr/ln')))
        ax.spines['bottom'].set_linewidth(.5)


def labels_above(ax, x, values, offset=4, fontsize=9, color=WHITE):
    for xx, yy in zip(x, values):
        ax.annotate(f'{yy:g}', (xx, yy), xytext=(0, offset), textcoords='offset points',
                    ha='center', va='bottom', fontsize=fontsize, color=color)


def gradient(ax, extent, top, bottom, clip=None):
    rgba = np.linspace(colors.to_rgba(bottom), colors.to_rgba(top), 256).reshape(256, 1, 4)
    im = ax.imshow(rgba, extent=extent, origin='lower', aspect='auto', interpolation='bicubic', zorder=2)
    if clip is not None:
        im.set_clip_path(clip)


def smooth_curve(y):
    """无 SciPy 依赖的三次 Hermite 插值，通过全部原始点。"""
    y = np.asarray(y, float)
    slopes = np.gradient(y)
    xx, yy = [], []
    for i in range(len(y)-1):
        t = np.linspace(0, 1, 50)
        v = (2*t**3-3*t**2+1)*y[i] + (t**3-2*t**2+t)*slopes[i]
        v += (-2*t**3+3*t**2)*y[i+1] + (t**3-t**2)*slopes[i+1]
        xx.extend(i+t)
        yy.extend(v)
    return xx, yy


