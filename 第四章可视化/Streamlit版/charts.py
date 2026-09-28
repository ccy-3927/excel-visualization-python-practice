"""所有图表使用 Plotly Python API 构建，不拼接 HTML / JavaScript。"""
import plotly.graph_objects as go

CYAN, PINK, BLUE, ORANGE = '#7BBDD5', '#FC6C9D', '#4A5BD1', '#F6A576'
HR_COLORS = ['#00B0F0', '#ED7D31', '#7AD5FE', '#EDA530', '#0070C0']

def style(fig, title, height=295):
    fig.update_layout(
        title={'text': title, 'x': .5, 'font': {'size': 17}}, height=height,
        paper_bgcolor='#2C3560', plot_bgcolor='#2C3560',
        font={'family': 'Microsoft YaHei, Noto Sans CJK SC, sans-serif', 'size': 12, 'color': '#F0F4FF'},
        margin={'l': 28, 'r': 30, 't': 50, 'b': 35},
        legend={'orientation': 'h', 'y': -.06, 'x': .5, 'xanchor': 'center', 'font': {'size': 11}},
        transition={'duration': 350},
    )
    return fig

def donut(title, labels, values, colors, center='', height=295, legend=True):
    fig = go.Figure()
    if sum(values) > 0:
        fig.add_trace(go.Pie(
            labels=labels, values=values, hole=.72, sort=False, direction='clockwise',
            marker={'colors': colors}, textinfo='percent' if legend else 'none',
            textposition='inside', hovertemplate='%{label}<br>数值：%{value:,.2f}<br>占比：%{percent}<extra></extra>',
            showlegend=legend,
        ))
    else:
        center = '暂无数据'
    style(fig, title, height)
    fig.add_annotation(text=str(center), x=.5, y=.5, xref='paper', yref='paper', showarrow=False, font={'size': 24})
    return fig

def bar(title, labels, values, color=CYAN, horizontal=False, height=295):
    if horizontal:
        trace = go.Bar(y=labels, x=values, orientation='h', marker_color=color,
                       text=values, textposition='outside', cliponaxis=False,
                       hovertemplate='%{y}：%{x:,}<extra></extra>')
    else:
        trace = go.Bar(x=labels, y=values, marker_color=color, text=values,
                       textposition='outside', cliponaxis=False, hovertemplate='%{x}：%{y:,}<extra></extra>')
    fig = style(go.Figure(trace), title, height)
    maximum = max(values, default=0)
    if horizontal:
        fig.update_xaxes(range=[0, max(1, maximum * 1.25)], showgrid=False, zeroline=False)
        fig.update_yaxes(autorange='reversed', showgrid=False, automargin=True)
    else:
        fig.update_yaxes(range=[0, max(1, maximum * 1.25)], gridcolor='#424D78', zeroline=False)
        fig.update_xaxes(showgrid=False, automargin=True)
    return fig

def trend(monthly, month):
    labels = [f'{m}月' for m in range(1, 13)]
    values = [monthly[m]['revenue'] for m in range(1, 13)]
    fig = go.Figure(go.Scatter(x=labels, y=values, fill='tozeroy', mode='lines+markers',
                              line={'color': BLUE}, marker={'size': 4}, name='销售额',
                              hovertemplate='%{x}：%{y:.2f} 万<extra></extra>'))
    fig.add_trace(go.Scatter(x=[f'{month}月'], y=[monthly[month]['revenue']], mode='markers',
                            marker={'color': CYAN, 'size': 13}, name='当前月份',
                            hovertemplate='%{x}：%{y:.2f} 万<extra></extra>'))
    style(fig, '各月销售额(万)')
    fig.update_layout(showlegend=False)
    fig.update_yaxes(rangemode='tozero', gridcolor='#424D78', zeroline=False)
    fig.update_xaxes(tickmode='array', tickvals=labels)
    return fig
