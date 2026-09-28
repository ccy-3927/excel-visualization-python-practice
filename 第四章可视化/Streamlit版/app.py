"""运行：python -m streamlit run app.py

独立 Streamlit 应用：Python 读取 Excel，Plotly 绘图，fragment 定时更新。
不调用旧版代码，不读取/生成 HTML 文件，也不嵌入自定义 HTML 或 JavaScript。
"""
from pathlib import Path
import os
import time
import streamlit as st
from data_model import (read_data, summarize_hr, summarize_sales, month_change, next_month,
                        HR_FILE, SALES_FILE, HR_SPECS, DEPARTMENTS, REGIONS, COURIERS, CATEGORIES)
from charts import donut, bar, trend, CYAN, PINK, BLUE, ORANGE, HR_COLORS

st.set_page_config(page_title='第四章 Python 可视化', page_icon='📊', layout='wide')

@st.cache_data(show_spinner='正在读取 Excel 明细…')
def cached_data(directory, fingerprints):
    return read_data(directory)

@st.cache_data(show_spinner=False)
def cached_monthly(sales, costs):
    return summarize_sales(sales, costs)

def chart(fig, key):
    st.plotly_chart(fig, use_container_width=True, theme=None, key=key,
                    config={'displaylogo': False, 'scrollZoom': False})

def jump():
    st.session_state.current_month = st.session_state.start_month
    st.session_state.last_tick = time.monotonic()

def reset():
    st.session_state.start_month = 9
    st.session_state.current_month = 9
    st.session_state.playing = False
    st.session_state.last_tick = time.monotonic()

def playback_changed():
    st.session_state.last_tick = time.monotonic()

def hr_page(rows):
    st.title('公司人员结构看板')
    st.caption('2022年3月 · Python / Streamlit · 部门与性别筛选为新增交互')
    with st.sidebar:
        departments = st.multiselect('部门', DEPARTMENTS, default=DEPARTMENTS)
        genders = st.multiselect('性别', ['男', '女'], default=['男', '女'])
        st.caption('清空任一筛选会显示0人；选择全部可恢复原始分布。')
    result = summarize_hr(rows, departments, genders)
    st.metric('当前人数', f'{result["count"]:,}', help='按所选部门与性别筛选后的明细行数')
    groups = result['groups']
    for start in (0, 3):
        columns = st.columns(3)
        for column, (title, _, labels, kind) in zip(columns, HR_SPECS[start:start + 3]):
            values = [groups[title][x] for x in labels]
            display_labels = ['40岁及以上' if x == '40=<' else x for x in labels]
            with column:
                if kind == 'pie':
                    colors = HR_COLORS if title == '年龄' else ['#EDA530', '#0070C0', '#7AD5FE']
                    fig = donut(title, display_labels, values, colors, f'{sum(values):,}人', height=330)
                else:
                    fig = bar(title, display_labels, values, '#7AD5FE', kind == 'horizontal', height=330)
                chart(fig, 'hr_' + title)
    st.caption('入转调只统计有记录的人员。源表学历 K24/K25 公式引用颠倒；按明细重算，全量专科以下170人、专科282人。')

def sales_page(monthly):
    st.title('公司销售数据可视化看板')
    for key, value in [('current_month', 9), ('start_month', 9), ('playing', False), ('last_tick', time.monotonic())]:
        if key not in st.session_state:
            st.session_state[key] = value
    with st.sidebar:
        st.selectbox('跳转月份 / 播放起点', range(1, 13), format_func=lambda m: f'{m}月', key='start_month', on_change=jump)
        st.toggle('自动播放', key='playing', on_change=playback_changed)
        seconds = st.select_slider('播放间隔（秒）', [1, 2, 3, 5], value=2)
        st.button('恢复9月并暂停', on_click=reset, use_container_width=True)
        st.caption('当前播放月份显示在主看板上方。暂停后保留当前月份；12月后循环至1月。')

    @st.fragment(run_every=seconds if st.session_state.playing else None)
    def dashboard():
        now = time.monotonic()
        if st.session_state.playing and now - st.session_state.last_tick >= seconds * .95:
            st.session_state.current_month = next_month(st.session_state.current_month)
            st.session_state.last_tick = now
        month = st.session_state.current_month
        d = monthly[month]
        st.subheader(f'2021年{month}月' + (' · 播放中' if st.session_state.playing else ''))
        left, middle, right = st.columns(3)
        with left:
            chart(donut('产品类别销量', CATEGORIES, [d['category'].get(x, 0) for x in CATEGORIES],
                        [PINK, BLUE, ORANGE], f'{d["count"]:,}'), 'sales_category')
            st.subheader('成本费用')
            total = sum(d['cost'].values())
            for names in [('推广', '人工'), ('产品', '其他')]:
                cols = st.columns(2)
                for column, name in zip(cols, names):
                    with column:
                        amount = d['cost'].get(name, 0)
                        percentage = amount / total if total else 0
                        chart(donut(name + '费用', [name, '其他成本'], [amount, total - amount],
                                    [CYAN, '#465477'], f'{percentage:.2%}', height=195, legend=False), 'cost_' + name)
                        st.metric(name + '合计', f'{amount:,.2f}')
        with middle:
            rate = month_change(monthly, month)
            st.metric('总销量', f'{d["count"]:,}', None if rate is None else f'{rate:+.2%} 较上月')
            previous = monthly.get(month - 1)
            labels = [f'{month}月', f'{month - 1}月'] if previous else ['1月']
            values = [d['count'], previous['count']] if previous else [d['count']]
            chart(bar('销量环比', labels, values, [CYAN, BLUE], horizontal=True, height=215), 'sales_change')
            if rate is None:
                st.caption('无上年12月数据，1月环比不计算。')
            st.subheader('商品销售额 Top3')
            st.dataframe(d['top'], hide_index=True, use_container_width=True,
                         column_config={'销售额(万)': st.column_config.NumberColumn(format='%.2f')})
            margin = d['margin']
            if margin is not None and 0 <= margin <= 1:
                chart(donut('利润额占比销售额', ['利润', '销售额减利润'],
                            [d['profit'], d['revenue'] - d['profit']], [PINK, '#465477'],
                            f'{margin:.2%}', height=245, legend=False), 'sales_margin')
            else:
                st.metric('利润率', '—' if margin is None else f'{margin:.2%}')
            a, b = st.columns(2)
            a.metric('利润额(万)', f'{d["profit"]:.2f}')
            b.metric('销售额(万)', f'{d["revenue"]:.2f}')
        with right:
            chart(trend(monthly, month), 'sales_trend')
            chart(bar('区域销量', REGIONS, [d['region'].get(x, 0) for x in REGIONS]), 'sales_region')
            chart(bar('快递公司销量', COURIERS, [d['courier'].get(x, 0) for x in COURIERS], PINK), 'sales_courier')
    dashboard()
    st.caption('销量沿用源表明细行数口径；销售额和利润额单位为万，成本单位源表未注明，保留原值。原表“同比”实际为环比，已更正。')

def default_data_directory():
    """兼容原Excel放在课程目录、原文件或data子目录的布局。"""
    configured = os.environ.get('CHAPTER4_DATA_DIR')
    if configured:
        return configured
    here = Path(__file__).resolve().parent
    course = here.parents[1]
    candidates = [course / '原文件', course, here / 'data', course / 'data']
    return str(next((p for p in candidates if all((p / n).is_file() for n in [HR_FILE, SALES_FILE])), candidates[0]))

def main():
    default = default_data_directory()
    with st.sidebar:
        st.header('第四章 · Python 看板')
        page = st.radio('选择看板', ['销售看板', '人力资源看板'])
        with st.expander('数据位置与刷新'):
            source = st.text_input('原Excel所在文件夹', value=default)
            if st.button('重新读取数据'):
                st.cache_data.clear()
    try:
        directory = Path(source)
        fingerprints = tuple((directory / name).stat().st_mtime_ns for name in [HR_FILE, SALES_FILE])
        hr, sales, costs = cached_data(str(directory), fingerprints)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f'无法读取Excel：{exc}')
        st.info('请在左侧“数据位置与刷新”中指定包含两个原始Excel的文件夹。')
        st.stop()
        return
    if page == '人力资源看板':
        # 切换页面时停止销售演示，回来仍停留在之前月份。
        st.session_state.playing = False
        hr_page(hr)
    else:
        sales_page(cached_monthly(sales, costs))

if __name__ == '__main__':
    main()
