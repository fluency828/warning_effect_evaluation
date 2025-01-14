from dash import Dash, dash_table, html, dcc, Input, Output, State, callback_context
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from page import read_fault_data, read_warning_data, read_dim_data, process_data_for_fault
import pandas as pd
# from datetime import datetime, timedelta

# 创建 Dash 应用
app = Dash(__name__)

# 获取并处理数据
fault_data = read_fault_data().drop_duplicates().reset_index(drop=True)
all_warning_data = read_warning_data().sort_values(
    by=['device_name','start_time'], 
    ascending=False
).reset_index(drop=True)
dim_data = read_dim_data()
processed_data, warnings = process_data_for_fault(fault_data, all_warning_data, dim_data)
processed_data = processed_data[[
    'site_name', 'phase_name', 'device_name',
    'fault_name', 'fault_start_time', 'fault_end_time',
    'earliest_warning_time', 'date_dif', 'warning_count', 
    'warning_days', 'monthly_counts'
]]

processed_data['earliest_warning_time'] = processed_data['earliest_warning_time'].fillna(pd.NaT)
processed_data['date_dif'] = processed_data['date_dif'].fillna(0)
processed_data['warning_count'] = processed_data['warning_count'].fillna(0)
processed_data['warning_days'] = processed_data['warning_days'].fillna(0)
processed_data['monthly_counts'] = processed_data['monthly_counts'].fillna({})
# print(processed_data[processed_data['earliest_warning_time'].isna()])
# 获取所有月份的并集
all_months = set()
for _, row in processed_data.iterrows():
    all_months.update(row['monthly_counts'].keys())
all_months = sorted(list(all_months))

# 获取筛选选项（添加全选选项）
def get_options_with_select_all(values, field_name):
    unique_values = sorted(values.unique())
    return [{'label': f'全选{field_name}', 'value': 'ALL'}] + [
        {'label': str(x), 'value': str(x)} for x in unique_values
    ]

phase_options = get_options_with_select_all(processed_data['phase_name'], '风场')
device_options = get_options_with_select_all(processed_data['device_name'], '设备')
fault_options = get_options_with_select_all(processed_data['fault_name'], '故障')
date_min = processed_data['fault_start_time'].min()
date_max = processed_data['fault_start_time'].max()

# 修改 STYLES 定义
STYLES = {
    'dropdown': {
        'width': '100%',
        'height': '38px',
    },
    'label': {
        'height': '32px',
        'lineHeight': '32px',
        'marginBottom': '5px'
    },
    'date_input': {
        'height': '38px',
        'width': '100%',  # 确保宽度填满容器
    },
    'container': {
        'padding': '20px',
        'backgroundColor': '#f8f9fa',
        'marginBottom': '20px'
    }
}

# 设置布局
app.layout = html.Div([
    # 标题
    html.H1("故障与预警分析系统", style={'textAlign': 'center'}),
    
    # 筛选器区域
    html.Div([
        # 第一行筛选器（相别、设备名称、故障名称、故障开始时间范围）
        html.Div([
            html.Div([
                html.Label('风场:', style=STYLES['label']),
                dcc.Dropdown(
                    id='phase-filter',
                    options=phase_options,
                    multi=True,
                    maxHeight=200,
                    style=STYLES['dropdown'],
                    placeholder='请选择风场...',
                    clearable=True,
                )
            ], style={'width': '20%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label('设备名称:', style=STYLES['label']),
                dcc.Dropdown(
                    id='device-filter',
                    options=device_options,
                    multi=True,
                    maxHeight=200,
                    style=STYLES['dropdown'],
                    placeholder='请选择设备...',
                    clearable=True,
                )
            ], style={'width': '20%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label('故障名称:', style=STYLES['label']),
                dcc.Dropdown(
                    id='fault-filter',
                    options=fault_options,
                    multi=True,
                    maxHeight=200,
                    style=STYLES['dropdown'],
                    placeholder='请选择故障...',
                    clearable=True,
                )
            ], style={'width': '20%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label('故障开始时间范围:', style=STYLES['label']),
                dcc.DatePickerRange(
                    id='date-range-filter',
                    min_date_allowed=date_min.date(),
                    max_date_allowed=date_max.date(),
                    start_date=date_min.date(),
                    end_date=date_max.date(),
                    display_format='YYYY-MM-DD',
                    first_day_of_week=1,
                    calendar_orientation='horizontal',
                    month_format='YYYY年 MM月',
                    clearable=True,
                    style=STYLES['date_input']
                )
            ], style={'width': '20%', 'display': 'inline-block'}),
        ], style={'marginBottom': '10px', 'display': 'flex', 'alignItems': 'flex-start'}),
        
        # 第二行筛选器（预警提前天数和预警天数）
        html.Div([
            html.Div([
                html.Label('预警提前天数:', style=STYLES['label']),
                dcc.RangeSlider(
                    id='date-diff-filter',
                    min=int(processed_data['date_dif'].min()),
                    max=int(processed_data['date_dif'].max()),
                    step=1,
                    marks={i: str(i) for i in range(
                        int(processed_data['date_dif'].min()),
                        int(processed_data['date_dif'].max()) + 1,
                        max(1, int((processed_data['date_dif'].max() - processed_data['date_dif'].min()) / 5))
                    )},
                    value=[int(processed_data['date_dif'].min()), int(processed_data['date_dif'].max())],
                    allowCross=False,
                    tooltip={'placement': 'bottom', 'always_visible': True}
                )
            ], style={'width': '35%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label('预警天数:', style=STYLES['label']),
                dcc.RangeSlider(
                    id='warning-count-filter',
                    min=int(processed_data['warning_days'].min()),
                    max=int(processed_data['warning_days'].max()),
                    step=1,
                    marks={i: str(i) for i in range(
                        int(processed_data['warning_days'].min()),
                        int(processed_data['warning_days'].max()) + 1,
                        max(1, int((processed_data['warning_days'].max() - processed_data['warning_days'].min()) / 5))
                    )},
                    value=[int(processed_data['warning_days'].min()), int(processed_data['warning_days'].max())],
                    allowCross=False,
                    tooltip={'placement': 'bottom', 'always_visible': True}
                )
            ], style={'width': '35%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            # 筛选按钮
            html.Div([
                html.Button('应用筛选', id='apply-filters', n_clicks=0, style={'marginRight': '10px'}),
                html.Button('重置筛选', id='reset-filters', n_clicks=0, style={'marginLeft': '10px'}),
            ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'bottom'}),
        ], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center'}),
    ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'marginBottom': '20px'}),
    
    # 主数据表格
    dash_table.DataTable(
        id='fault-table',
        data=processed_data.drop('monthly_counts', axis=1).to_dict('records'),
        columns=[{"name": i, "id": i} for i in processed_data.columns if i != 'monthly_counts'],
        style_table={
            'overflowX': 'auto',
            'width': '100%'
        },
        style_cell={
            'textAlign': 'left',
            'minWidth': '100px',
            'maxWidth': '180px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
            'cursor': 'pointer'
        },
        page_size=15,
        row_selectable='single',
        selected_rows=[0],
        sort_action='native',
        sort_mode='single',
    ),
    
    # 下方展示区域（水平排列）
    html.Div([
        # 左侧柱状图
        html.Div([
            dcc.Graph(id='monthly-chart')
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        # 右侧预警信息表格
        html.Div([
            html.H3("预警信息", style={'marginTop': '0px'}),
            dash_table.DataTable(
                id='warning-table',
                columns=[
                    {"name": "预警开始时间", "id": "start_time"},
                    {"name": "预警结束时间", "id": "end_time"},
                    {"name": "预警信息", "id": "alarm_info"}
                ],
                style_table={
                    'overflowY': 'auto',
                    'maxHeight': '500px'
                },
                style_cell={
                    'textAlign': 'left',
                    'minWidth': '100px',
                    'maxWidth': '300px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                page_size=10,
            )
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'width': '100%', 'display': 'flex'})
])

# 修改 app.index_string 中的 CSS 样式
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .Select-multi-value-wrapper {
                max-height: 38px;
                overflow-y: auto;
            }
            .Select--multi .Select-value {
                display: inline-block;
                margin: 2px;
            }
            
            /* 日期选择器样式 */
            .DateRangePicker {
                width: 100%;
            }
            .DateRangePickerInput {
                width: 100%;
                height: 38px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            .DateInput {
                width: 45% !important;
                height: 38px;
            }
            .DateInput_input {
                height: 36px;
                line-height: 36px;
                font-size: 14px;
                padding: 0 8px;
                width: 100%;
            }
            .DateRangePickerInput_arrow {
                padding: 0 5px;
                line-height: 38px;
            }
            /* 确保日期选择器下拉框显示在其他元素之上 */
            .DateRangePicker_picker {
                z-index: 999;
            }
            .rc-slider-tooltip {
                z-index: 999;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# 添加全选回调函数
@app.callback(
    [Output('phase-filter', 'value'),
     Output('device-filter', 'value'),
     Output('fault-filter', 'value')],
    [Input('phase-filter', 'value'),
     Input('device-filter', 'value'),
     Input('fault-filter', 'value')]
)
def update_multi_select(phase_selected, device_selected, fault_selected):
    ctx = callback_context
    if not ctx.triggered:
        return [], [], []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    def handle_selection(selected, all_options):
        if not selected:
            return []
        if 'ALL' in selected:
            return [opt['value'] for opt in all_options] if len(selected) == 1 else \
                   [opt['value'] for opt in all_options if opt['value'] != 'ALL']
        return selected if len(selected) < len(all_options) - 1 else \
               [opt['value'] for opt in all_options]
    
    selections = {
        'phase-filter': (phase_selected, phase_options),
        'device-filter': (device_selected, device_options),
        'fault-filter': (fault_selected, fault_options)
    }
    
    result = [selections[trigger_id][0] if trigger_id == key else (val[0] or [])
              for key, val in selections.items()]
    
    if trigger_id in selections:
        result[list(selections.keys()).index(trigger_id)] = \
            handle_selection(*selections[trigger_id])
    
    return result

# 修改筛选回调函数
@app.callback(
    [Output('fault-table', 'data'),
     Output('fault-table', 'selected_rows')],
    [Input('apply-filters', 'n_clicks'),
     Input('reset-filters', 'n_clicks'),
     Input('phase-filter', 'value'),
     Input('device-filter', 'value'),
     Input('fault-filter', 'value'),
     Input('date-diff-filter', 'value'),
     Input('warning-count-filter', 'value'),
     Input('date-range-filter', 'start_date'),
     Input('date-range-filter', 'end_date')],
    [State('fault-table', 'selected_rows'),
     State('fault-table', 'data')]
)
def update_table(apply_clicks, reset_clicks, phases, devices, faults, 
                date_diff_range, warning_days_range, start_date, end_date,
                current_selected_rows, current_data):
    ctx = callback_context
    if not ctx.triggered:
        return processed_data.drop('monthly_counts', axis=1).to_dict('records'), [0]
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 如果是重置按钮，返回原始数据
    if button_id == 'reset-filters':
        return processed_data.drop('monthly_counts', axis=1).to_dict('records'), [0]
    
    # 获取当前选中行的关键信息（如果有）
    current_selected_row = None
    if current_selected_rows and current_data:
        current_selected_row = current_data[current_selected_rows[0]]
    
    filtered_data = processed_data.copy()
    
    # 处理筛选条件
    if phases and 'ALL' not in phases:
        filtered_data = filtered_data[filtered_data['phase_name'].isin(phases)]
    if devices and 'ALL' not in devices:
        filtered_data = filtered_data[filtered_data['device_name'].isin(devices)]
    if faults and 'ALL' not in faults:
        filtered_data = filtered_data[filtered_data['fault_name'].isin(faults)]
    if date_diff_range:
        filtered_data = filtered_data[
            (filtered_data['date_dif'] >= date_diff_range[0]) &
            (filtered_data['date_dif'] <= date_diff_range[1])
        ]
    if warning_days_range:
        filtered_data = filtered_data[
            (filtered_data['warning_days'] >= warning_days_range[0]) &
            (filtered_data['warning_days'] <= warning_days_range[1])
        ]
    if start_date and end_date:
        filtered_data = filtered_data[
            (filtered_data['fault_start_time'].dt.date >= pd.to_datetime(start_date).date()) &
            (filtered_data['fault_start_time'].dt.date <= pd.to_datetime(end_date).date())
        ]
    
    filtered_data = filtered_data.reset_index(drop=True)
    filtered_records = filtered_data.drop('monthly_counts', axis=1).to_dict('records')
    
    # 尝试在筛选后的数据中找到之前选中的行
    selected_index = 0
    if current_selected_row:
        for i, row in enumerate(filtered_records):
            if (row['device_name'] == current_selected_row['device_name'] and
                row['phase_name'] == current_selected_row['phase_name'] and
                row['fault_name'] == current_selected_row['fault_name'] and
                row['fault_start_time'] == current_selected_row['fault_start_time']):
                selected_index = i
                break
    
    return filtered_records, [selected_index]

# 修改图表和预警信息的回调函数
@app.callback(
    [Output('monthly-chart', 'figure'),
     Output('warning-table', 'data')],
    [Input('fault-table', 'selected_rows'),
     Input('fault-table', 'data')]
)
def update_displays(selected_rows, current_table_data):
    if not selected_rows:
        selected_rows = [0]
    
    # 将当前表格数据转换回 DataFrame
    current_df = pd.DataFrame(current_table_data)
    
    # 获取选中行的数据
    selected_row = current_df.iloc[selected_rows[0]]
    
    # 使用多个条件匹配确保找到正确的行
    mask = (processed_data['device_name'] == selected_row['device_name']) & \
           (processed_data['phase_name'] == selected_row['phase_name']) & \
           (processed_data['fault_name'] == selected_row['fault_name']) & \
           (processed_data['fault_start_time'] == pd.to_datetime(selected_row['fault_start_time']))
    
    selected_row_data = processed_data[mask].iloc[0]
    selected_index = processed_data[mask].index[0]
    
    # 获取对应的预警数据
    warning_df = warnings[selected_index]
    
    # 获取所有记录中预警次数的全局最大值
    global_max_warning_count = max(
        df.groupby(df['start_time'].dt.date).size().max()
        for df in warnings
        if not df.empty
    )
    
    # 创建整数刻度的颜色条标签
    colorbar_ticks = list(range(0, global_max_warning_count + 1))
    
    # 准备日历图数据
    warning_counts = warning_df.groupby(warning_df['start_time'].dt.date).size()
    
    # 处理没有预警数据的情况
    if warning_counts.empty:
        # 如果没有预警数据，使用故障时间作为日期范围
        start_date = pd.to_datetime(selected_row_data['fault_start_time']).date()
        end_date = pd.to_datetime(selected_row_data['fault_end_time']).date()
    else:
        # 如果有预警数据，使用预警数据的日期范围
        start_date = warning_counts.index.min()
        end_date = max(warning_counts.index.max(), pd.to_datetime(selected_row_data['fault_end_time']).date())
    
    # 确保包括开始和结束月份
    start_month = pd.to_datetime(start_date).replace(day=1)
    end_month = (pd.to_datetime(end_date) + pd.DateOffset(months=1)).replace(day=1) - pd.DateOffset(days=1)
    
    # 创建月份日历热力图
    months_between = pd.date_range(start_month, end_month, freq='M')
    n_months = len(months_between)
    
    # 确保至少有一行
    n_rows = max((n_months + 2) // 3, 1)
    
    # 创建子图
    fig = make_subplots(
        rows=n_rows, 
        cols=3,
        subplot_titles=[d.strftime('%Y-%m') for d in months_between],
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )
    
    # 获取故障开始时间
    fault_start_time = pd.to_datetime(selected_row_data['fault_start_time']).date()
    
    # 为每个月创建日历热力图
    for i, month_date in enumerate(months_between):
        row = i // 3 + 1
        col = i % 3 + 1
        
        # 获取当月的日历数据
        month_start = month_date.replace(day=1)
        month_end = (month_start + pd.DateOffset(months=1) - pd.DateOffset(days=1)).date()
        month_dates = pd.date_range(month_start, month_end, freq='D')
        
        # 创建日历网格
        weeks = [[] for _ in range(6)]  # 预先创建6周的空间
        week_days = [[] for _ in range(6)]
        hover_texts = [[] for _ in range(6)]
        
        # 计算第一天是星期几（0-6）
        first_day_weekday = month_start.weekday()
        
        # 填充第一周的空白日期
        for week_idx in range(6):
            if week_idx == 0:
                weeks[0].extend([None] * first_day_weekday)
                week_days[0].extend([''] * first_day_weekday)
                hover_texts[0].extend([''] * first_day_weekday)
        
        # 当前处理到第几周
        current_week = 0
        current_week_day = first_day_weekday
        
        # 填充日期和对应的预警次数
        for date in month_dates:
            # 如果当前周已满，移到下一周
            if current_week_day == 7:
                current_week += 1
                current_week_day = 0
            
            warning_count = warning_counts.get(date.date(), 0)
            weeks[current_week].append(warning_count)
            week_days[current_week].append(str(date.day))
            hover_texts[current_week].append(f"{date.strftime('%Y-%m-%d')}: {warning_count} 次预警")
            
            current_week_day += 1
        
        # 填充最后一周的剩余空白
        if current_week_day < 7:
            weeks[current_week].extend([None] * (7 - current_week_day))
            week_days[current_week].extend([''] * (7 - current_week_day))
            hover_texts[current_week].extend([''] * (7 - current_week_day))
        
        # 移除空的周
        weeks = [week for week in weeks if week]
        week_days = [week for week in week_days if week]
        hover_texts = [week for week in hover_texts if week]
        
        # 找到故障日期在当前月份中的位置（如果存在）
        fault_week_idx = None
        fault_day_idx = None
        
        if month_date.year == fault_start_time.year and month_date.month == fault_start_time.month:
            # 计算故障日期在日历中的位置
            first_day_weekday = month_start.weekday()
            fault_day = fault_start_time.day
            total_days = first_day_weekday + fault_day - 1
            fault_week_idx = total_days // 7
            fault_day_idx = total_days % 7
        
        # 添加热力图
        fig.add_trace(
            go.Heatmap(
                z=weeks[::-1],
                text=week_days[::-1],
                texttemplate="%{text}",
                textfont={"size": 10},
                colorscale='YlOrRd',
                showscale=i==0,
                zmin=0,
                zmax=global_max_warning_count,
                colorbar=dict(
                    title='预警次数',
                    titleside='right',
                    x=1.02,
                    y=0.5,
                    tickmode='array',
                    tickvals=colorbar_ticks,
                    ticktext=[str(x) for x in colorbar_ticks]
                ) if i==0 else None,
                hoverinfo='text',
                hovertext=hover_texts[::-1],
            ),
            row=row,
            col=col
        )
        
        # 如果故障日期在当前月份中，添加蓝色边框
        if fault_week_idx is not None and fault_day_idx is not None:
            # 计算单元格的位置（在反转后的坐标系中）
            y_pos = len(weeks) - 1 - fault_week_idx
            x_pos = fault_day_idx
            
            # 添加蓝色边框
            fig.add_shape(
                type="rect",
                xref=f"x{i+1}",
                yref=f"y{i+1}",
                x0=x_pos - 0.5,
                y0=y_pos - 0.5,
                x1=x_pos + 0.5,
                y1=y_pos + 0.5,
                line=dict(
                    color="rgb(0, 150, 255)",
                    width=2,
                ),
                fillcolor="rgba(0, 0, 0, 0)",
                row=row,
                col=col
            )
        
        # 设置坐标轴
        fig.update_xaxes(
            showgrid=False,
            showticklabels=False,
            row=row,
            col=col
        )
        fig.update_yaxes(
            showgrid=False,
            showticklabels=False,
            row=row,
            col=col
        )
    
    # 更新布局
    fig.update_layout(
        title=f"设备 {selected_row_data['device_name']} - 故障开始时间: {fault_start_time}",
        height=100 * n_rows + 150,
        margin=dict(t=50, l=20, r=50, b=20),
        showlegend=False,
    )
    
    # 获取预警信息表格数据
    warning_data = warning_df[['start_time', 'end_time', 'alarm_info']].to_dict('records')
    
    return fig, warning_data

# 运行应用
if __name__ == '__main__':
    app.run_server(debug=True) 