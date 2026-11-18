"""运行：python -m streamlit run app.py"""
from io import BytesIO
import matplotlib.pyplot as plt
import streamlit as st
from charts import NAMES, load_data, defaults, draw_chart

st.set_page_config(page_title='第三章 · 动态图表',page_icon='📊',layout='wide')
st.title('第三章 · 动态图表')
st.caption('《Excel数据可视化——从图表到数据大屏》｜原始工作簿数据 · Python / Streamlit 复现')
@st.cache_data
def get_data(): return load_data()
d=get_data(); s=defaults(d)
selected=st.sidebar.radio('选择图表',range(7),format_func=lambda i:f'{i+1:02d}  {NAMES[i]}')
i=selected
st.sidebar.divider()
if i in (0,2,5):
    key={0:'sales',2:'rose',5:'jade'}[i]
    options=[r[0] for r in d[key][1:]]
    s[key]=st.sidebar.selectbox('月份' if i==0 else '统计周期',range(len(options)),index=s[key],format_func=lambda j:options[j])
elif i==1:
    options=d['people'][0][1:]
    s['people']=st.sidebar.selectbox('月份',range(len(options)),index=s['people'],format_func=lambda j:options[j])
elif i==3:
    s['combo']=[st.sidebar.checkbox(label,value=s['combo'][j]) for j,label in enumerate(['销售额','利润','利润率'])]
elif i==4:
    s['departments']=st.sidebar.multiselect('部门（可多选）',d['departments'],default=s['departments'])
elif i==6:
    s['beadMode']=st.sidebar.radio('查看方式',[0,1],index=s['beadMode'],format_func=lambda v:['按月份看区域','按区域看月份'][v])
    options=d['bead'][0][1:] if s['beadMode']==0 else [r[0] for r in d['bead'][1:]]
    s['beadIndex']=st.sidebar.selectbox('月份' if s['beadMode']==0 else '区域',range(len(options)),index=0,format_func=lambda j:options[j],key=f'bead_{s["beadMode"]}')
fig,df=draw_chart(d,i,s)
st.pyplot(fig,use_container_width=True)
if i in (1,5): st.caption('按教材保留圆弧计算方式：跑道图分母为总人数的一半；玉玦图分母为 50%。圆弧角度不直接表示总体占比，请以标注数据为准。')
if i==2: st.caption('保留原工作簿六层嵌套圆环及各层颜色；扇区角度表示来源占比，外径为教材设计。')
if i==3: st.caption('按教材复现双轴：左轴为销售额与利润，右轴为利润率（0–100%）。')
if i==4:
    st.caption('多部门平均收入 = 所选员工收入合计 ÷ 人数；无记录显示为空，不作为零收入参与计算。')
    if not s['departments']: st.info('请选择至少一个部门以查看平均收入。')
with st.expander('查看当前数据',expanded=True): st.dataframe(df,use_container_width=True,hide_index=True)
png=BytesIO(); fig.savefig(png,format='png',dpi=180)
svg=BytesIO(); fig.savefig(svg,format='svg')
st.caption('以下图片下载仅保存当前筛选状态的静态快照；动态交互请使用本页面。')
a,b,c=st.columns(3)
a.download_button('下载 PNG 静态快照',png.getvalue(),f'{NAMES[i]}.png','image/png')
b.download_button('下载 SVG 静态快照',svg.getvalue(),f'{NAMES[i]}.svg','image/svg+xml')
c.download_button('下载当前数据',df.to_csv(index=False).encode('utf-8-sig'),f'{NAMES[i]}.csv','text/csv')
plt.close(fig)
st.sidebar.caption('数据：随项目附带的第三章 动态图表.xlsm。初始筛选对应原工作簿保存状态。')
